#!/usr/bin/env node
/** Exercise the real Ohmni form through a running Chromium CDP endpoint. */

import process from "node:process";

const API_VERSION = 2;
const FIXTURE_ID = "esp32-bme280-environmental-logger";
const JOB_ID_PATTERN = /^[0-9a-f]{12}$/;
const INSTANCE_ID_PATTERN = /^[0-9a-f]{16}$/;
const UI_VERSION_PATTERN = /^[0-9a-f]{64}$/;

function usage() {
  return [
    "Usage: node scripts/demo_browser_smoke.mjs [options]",
    "  --debug-host HOST          CDP host (default: 127.0.0.1)",
    "  --debug-port PORT          CDP port (default: 9222)",
    "  --page-url URL             Ohmni page URL (default: http://127.0.0.1:8765/)",
    "  --timeout-ms MILLISECONDS  Completion timeout (default: 300000)",
    "  --stop-after-progress      Succeed once the real UI advances beyond 0%",
    "  --no-reload                Do not reload the target before clicking",
  ].join("\n");
}

function positiveInteger(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }
  return parsed;
}

function parseArgs(argv) {
  const options = {
    debugHost: process.env.OHMNI_CDP_HOST || "127.0.0.1",
    debugPort: positiveInteger(process.env.OHMNI_CDP_PORT || "9222", "debug port"),
    pageUrl: process.env.OHMNI_PAGE_URL || "http://127.0.0.1:8765/",
    timeoutMs: positiveInteger(process.env.OHMNI_SMOKE_TIMEOUT_MS || "300000", "timeout"),
    stopAfterProgress: false,
    reload: true,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help" || argument === "-h") {
      console.log(usage());
      process.exit(0);
    } else if (argument === "--stop-after-progress") {
      options.stopAfterProgress = true;
    } else if (argument === "--no-reload") {
      options.reload = false;
    } else if (["--debug-host", "--debug-port", "--page-url", "--timeout-ms"].includes(argument)) {
      const value = argv[index + 1];
      if (value === undefined) throw new Error(`${argument} requires a value`);
      index += 1;
      if (argument === "--debug-host") options.debugHost = value;
      if (argument === "--debug-port") options.debugPort = positiveInteger(value, "debug port");
      if (argument === "--page-url") options.pageUrl = value;
      if (argument === "--timeout-ms") options.timeoutMs = positiveInteger(value, "timeout");
    } else {
      throw new Error(`unknown argument: ${argument}`);
    }
  }
  const page = new URL(options.pageUrl);
  if (!(["http:", "https:"].includes(page.protocol))) throw new Error("page URL must use HTTP(S)");
  options.pageUrl = page.href;
  return options;
}

function sleep(milliseconds) {
  return new Promise(resolve => setTimeout(resolve, milliseconds));
}

function normalizeHeaders(headers = {}) {
  return Object.fromEntries(Object.entries(headers).map(([key, value]) => [key.toLowerCase(), String(value)]));
}

function samePage(actual, expected) {
  try {
    const left = new URL(actual);
    const right = new URL(expected);
    return left.origin === right.origin && left.pathname === right.pathname;
  } catch {
    return false;
  }
}

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

async function connectCdp(webSocketUrl, onEvent) {
  const socket = new WebSocket(webSocketUrl);
  const pending = new Map();
  let sequence = 0;
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const entry = pending.get(message.id);
      pending.delete(message.id);
      clearTimeout(entry.timer);
      if (message.error) entry.reject(new Error(`${entry.method}: ${JSON.stringify(message.error)}`));
      else entry.resolve(message.result);
      return;
    }
    if (message.method) onEvent(message.method, message.params || {});
  });
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, {once: true});
    socket.addEventListener("error", () => reject(new Error("could not connect to the CDP target")), {once: true});
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`${method} timed out`));
    }, 10000);
    pending.set(id, {method, resolve, reject, timer});
    socket.send(JSON.stringify({id, method, params}));
  });
  const close = () => {
    for (const entry of pending.values()) {
      clearTimeout(entry.timer);
      entry.reject(new Error("CDP connection closed"));
    }
    pending.clear();
    socket.close();
  };
  return {call, close};
}

function apiPath(url, origin) {
  try {
    const parsed = new URL(url);
    return parsed.origin === origin && parsed.pathname.startsWith("/api/")
      ? `${parsed.pathname}${parsed.search}`
      : null;
  } catch {
    return null;
  }
}

async function evaluate(call, expression) {
  const reply = await call("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (reply.exceptionDetails) throw new Error(`browser evaluation failed: ${JSON.stringify(reply.exceptionDetails)}`);
  return reply.result.value;
}

async function waitForPage(call, deadline) {
  let lastError;
  while (Date.now() < deadline) {
    try {
      const state = await evaluate(call, `(() => ({
        ready: document.readyState,
        href: location.href,
        hasForm: Boolean(document.querySelector("#request-form")),
        hasButton: Boolean(document.querySelector("#run-button"))
      }))()`);
      if (state.ready === "complete" && state.hasForm && state.hasButton) return state;
    } catch (error) {
      lastError = error;
    }
    await sleep(100);
  }
  throw new Error(`Ohmni page did not become ready${lastError ? `: ${lastError.message}` : ""}`);
}

async function responseBodies(call, exchanges) {
  for (const exchange of exchanges.values()) {
    if (!exchange.response || exchange.body !== undefined) continue;
    try {
      const result = await call("Network.getResponseBody", {requestId: exchange.requestId});
      exchange.body = result.base64Encoded
        ? Buffer.from(result.body, "base64").toString("utf8")
        : result.body;
    } catch (error) {
      exchange.bodyError = error.message;
    }
  }
}

function parseBody(exchange, label) {
  requireValue(typeof exchange.body === "string", `${label} response body was not captured`);
  try {
    return JSON.parse(exchange.body);
  } catch {
    throw new Error(`${label} response was not JSON`);
  }
}

function validateIdentity(value, label) {
  requireValue(value?.api_version === API_VERSION, `${label} API version was not ${API_VERSION}`);
  requireValue(INSTANCE_ID_PATTERN.test(value?.server_instance_id || ""), `${label} server instance ID was invalid`);
  requireValue(UI_VERSION_PATTERN.test(value?.ui_version || ""), `${label} UI version was invalid`);
}

function validateApi(exchanges, pageOrigin, stopAfterProgress) {
  const records = [...exchanges.values()];
  const start = records.find(item => item.method === "POST" && apiPath(item.url, pageOrigin) === "/api/demo");
  requireValue(start, "the form did not POST /api/demo");
  requireValue(start.response?.status === 202, `POST /api/demo returned ${start.response?.status ?? "no response"}`);
  let requestBody;
  try {
    requestBody = JSON.parse(start.postData || "");
  } catch {
    throw new Error("POST /api/demo did not carry a JSON body");
  }
  requireValue(
    JSON.stringify(Object.keys(requestBody).sort()) === JSON.stringify([
      "api_version", "fixture_id", "server_instance_id", "ui_version",
    ]),
    "POST /api/demo did not use the exact current fixture contract",
  );
  requireValue(requestBody.fixture_id === FIXTURE_ID, "POST /api/demo used the wrong fixture");
  validateIdentity(requestBody, "start request");
  const accepted = parseBody(start, "start");
  validateIdentity(accepted, "start response");
  requireValue(accepted.server_instance_id === requestBody.server_instance_id, "start response changed server identity");
  requireValue(accepted.ui_version === requestBody.ui_version, "start response changed UI identity");
  requireValue(accepted.status === "queued", "start response did not queue a job");
  requireValue(JOB_ID_PATTERN.test(accepted.job_id || ""), "start response job ID was invalid");

  const jobRecords = records.filter(item => item.method === "GET"
    && apiPath(item.url, pageOrigin)?.startsWith(`/api/jobs/${accepted.job_id}`));
  requireValue(jobRecords.length > 0, "the UI did not poll the accepted job");
  const successful = jobRecords.filter(item => item.response?.status === 200 && typeof item.body === "string");
  requireValue(successful.length > 0, "the UI received no successful job response");
  for (const item of successful) {
    const headers = normalizeHeaders(item.headers);
    requireValue(headers["x-ohmni-api-version"] === String(API_VERSION), "job poll omitted the API-version header");
    requireValue(headers["x-ohmni-server-instance"] === accepted.server_instance_id, "job poll used the wrong server identity");
    requireValue(headers["x-ohmni-ui-version"] === accepted.ui_version, "job poll used the wrong UI identity");
  }
  const latest = parseBody(successful.at(-1), "job");
  validateIdentity(latest, "job response");
  requireValue(latest.server_instance_id === accepted.server_instance_id, "job response changed server identity");
  requireValue(latest.ui_version === accepted.ui_version, "job response changed UI identity");
  requireValue(latest.job_id === accepted.job_id, "job response changed job ID");
  if (stopAfterProgress) {
    requireValue(["running", "complete"].includes(latest.status), "job did not advance beyond queued");
    requireValue(latest.progress?.some(item => Number(item.percent) > 0), "job response had no positive progress");
  } else {
    requireValue(latest.status === "complete", "terminal job response was not complete");
    requireValue(latest.progress?.at(-1)?.percent === 100, "terminal job response did not reach 100%");
    const report = latest.report;
    requireValue(report?.failure_and_repair?.rule === "PB-PWR-001", "BME280 5 V failure was absent");
    requireValue(report?.failure_and_repair?.status === "REPAIRED", "bounded repair was absent");
    requireValue(
      report?.failure_and_repair?.result?.includes("passed after deterministic re-verification"),
      "bounded repair was not deterministically re-verified",
    );
    const ladder = Array.isArray(report?.verification_ladder) ? report.verification_ladder : [];
    const semantic = ladder.filter(row => typeof row?.subsystem === "string");
    requireValue(semantic.length > 0, "semantic verification roll-ups were absent");
    requireValue(
      semantic.every(row => !/(FAIL|ERROR|BLOCK|UNKNOWN)/.test(String(row.status))),
      "semantic verification retained a blocking or unknown status",
    );
    for (const stage of [
      "KiCad ERC", "Ohmni physical verification", "Ohmni routing verification", "KiCad DRC",
    ]) {
      const row = ladder.find(item => item?.stage === stage);
      requireValue(row && ["PASS", "PASS_WITH_WARNINGS"].includes(row.status), `${stage} did not pass`);
    }
    requireValue(report?.schematic?.current === true, "schematic was not current");
    requireValue(
      ["PASS", "PASS_WITH_WARNINGS"].includes(report?.schematic?.erc_status),
      "schematic ERC did not pass",
    );
    requireValue(report?.pcb?.current === true, "PCB was not current");
    requireValue(report?.pcb?.violations === 0 && report?.pcb?.unrouted === 0, "DRC/routing did not close at zero");
    requireValue(report?.release?.current === true, "release was not current");
    requireValue(
      report?.release?.status === "READY_FOR_MANUFACTURING_REVIEW",
      "release was not ready for manufacturing review",
    );
    requireValue(
      UI_VERSION_PATTERN.test(report?.release?.manifest?.sha256 || ""),
      "release integrity manifest digest was absent",
    );
  }
  return {accepted, latest, records};
}

function validateGoldenUi(state) {
  const required = [
    "BME280 VDD and VDDIO connected to 5 V VBUS",
    "BOUNDED REPAIR",
    "Both sensor supply pins moved to 3V3",
    "Ohmni semantic verification",
    "KiCad ERC",
    "Ohmni physical verification",
    "Ohmni routing verification",
    "KiCad DRC",
    "0 violations / 0 unrouted",
    "Ready for manufacturing review",
  ];
  const missing = required.filter(text => !state.bodyText.includes(text));
  requireValue(missing.length === 0, `completed UI omitted: ${missing.join(", ")}`);
  requireValue(state.releaseText.includes("CURRENT"), "release UI did not present current artifacts");
  requireValue(!state.releaseText.includes("STALE"), "release UI presented a stale release");
  return required;
}

function safeExchange(exchange, pageOrigin) {
  return {
    method: exchange.method,
    path: apiPath(exchange.url, pageOrigin),
    status: exchange.response?.status ?? null,
  };
}

async function run(options) {
  const listUrl = `http://${options.debugHost}:${options.debugPort}/json/list`;
  const response = await fetch(listUrl);
  requireValue(response.ok, `CDP target list returned HTTP ${response.status}`);
  const targets = await response.json();
  const target = targets.find(item => item.type === "page" && samePage(item.url, options.pageUrl));
  requireValue(target?.webSocketDebuggerUrl, `no CDP page target matched ${options.pageUrl}`);

  const pageOrigin = new URL(options.pageUrl).origin;
  const exchanges = new Map();
  const onEvent = (method, params) => {
    if (method === "Network.requestWillBeSent") {
      const path = apiPath(params.request?.url, pageOrigin);
      if (!path) return;
      exchanges.set(params.requestId, {
        requestId: params.requestId,
        method: params.request.method,
        url: params.request.url,
        headers: params.request.headers || {},
        postData: params.request.postData,
      });
    } else if (method === "Network.responseReceived" && exchanges.has(params.requestId)) {
      exchanges.get(params.requestId).response = {
        status: params.response.status,
        headers: params.response.headers || {},
      };
    }
  };
  const {call, close} = await connectCdp(target.webSocketDebuggerUrl, onEvent);
  const deadline = Date.now() + options.timeoutMs;
  try {
    await Promise.all([
      call("Network.enable"),
      call("Page.enable"),
      call("Runtime.enable"),
    ]);
    if (options.reload) await call("Page.reload", {ignoreCache: true});
    const ready = await waitForPage(call, deadline);
    requireValue(samePage(ready.href, options.pageUrl), `browser loaded unexpected page ${ready.href}`);
    const clicked = await evaluate(call, `(() => {
      const element = document.querySelector("#run-button");
      if (!element || element.disabled) return false;
      element.scrollIntoView({block: "center", inline: "center"});
      element.click();
      return true;
    })()`);
    requireValue(clicked, "Run button was not clickable");

    let state;
    while (Date.now() < deadline) {
      state = await evaluate(call, `(() => {
        const progressText = document.querySelector("#progress-percent")?.textContent || "";
        return {
          progressText,
          progress: Number.parseInt(progressText, 10) || 0,
          progressList: document.querySelector("#progress-list")?.innerText || "",
          workspaceHidden: document.querySelector("#workspace")?.hidden !== false,
          releaseText: document.querySelector("#release")?.innerText || "",
          bodyText: document.body?.innerText || ""
        };
      })()`);
      if (state.progressList.includes("Pipeline stopped")) {
        throw new Error(`UI reported Pipeline stopped: ${state.progressList.replace(/\s+/g, " ").trim()}`);
      }
      if (options.stopAfterProgress && state.progress > 0) break;
      if (!options.stopAfterProgress && state.progress === 100 && !state.workspaceHidden) break;
      await sleep(200);
    }
    requireValue(state, "browser returned no workflow state");
    if (options.stopAfterProgress) requireValue(state.progress > 0, "UI did not advance beyond 0%");
    else {
      requireValue(state.progress === 100, `UI stopped at ${state.progress}%`);
      requireValue(!state.workspaceHidden, "completed workspace stayed hidden");
    }
    await sleep(100);
    await responseBodies(call, exchanges);
    const api = validateApi(exchanges, pageOrigin, options.stopAfterProgress);
    const requiredResults = options.stopAfterProgress ? [] : validateGoldenUi(state);
    return {
      mode: options.stopAfterProgress ? "progress" : "complete",
      page_url: options.pageUrl,
      progress: state.progress,
      job_id: api.accepted.job_id,
      server_instance_id: api.accepted.server_instance_id,
      ui_version: api.accepted.ui_version,
      api: api.records.map(item => safeExchange(item, pageOrigin)),
      required_results: requiredResults,
    };
  } finally {
    close();
  }
}

try {
  const result = await run(parseArgs(process.argv.slice(2)));
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  console.error(`Ohmni browser smoke failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
