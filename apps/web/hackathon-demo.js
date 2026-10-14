// Offline saved demonstration: original board -> damaged copy -> restore.
// Every result shown is a recorded receipt from a saved run. Each board view is
// shown only after its PCB file's SHA-256, computed here in the browser, matches
// the fingerprint its displayed geometry and checks are bound to.
import { BoardView } from "./board-view.js";
import { createSelection, faultReport, goodReport, sha256Hex, validateDemo } from "./hackathon-demo-model.js";
import { escapeHtml as esc } from "./view-model.js";

const BASE = "/hackathon-demo/";
const BOARD_FILES = { good: "saved-run/golden.kicad_pcb", fault: "saved-run/fault/diagnostic-fault.kicad_pcb" };

const $ = (selector) => document.querySelector(selector);

async function fetchOk(path, fetcher) {
    const response = await fetcher(BASE + path, { cache: "no-store" });
    if (!response.ok) throw new Error(`missing ${path}`);
    return response;
}

function renderReport(report, verifiedHash) {
    const rows = report.rows.map((row) => `<tr><th scope="row">${esc(row.check)}</th><td><span class="outcome" data-outcome="${esc(row.outcome)}">${esc(row.outcome.replaceAll("_", " "))}</span></td><td>${esc(row.checker)}</td><td>${esc(row.detail)}</td></tr>`).join("");
    const findings = (report.findings || []).map((item) => `<li><strong>${esc(item.severity)}</strong> · ${esc(item.type)}: ${esc(item.description)}<ul>${item.items.map((part) => `<li>${esc(part)}</li>`).join("")}</ul></li>`).join("");
    const explanation = (report.explanation || []).map((line) => `<p>${esc(line)}</p>`).join("");
    const removed = report.removed ? `<p>Removed track: net <code>${esc(report.removed.net_name)}</code> on ${esc(report.removed.layer)}, from (${esc(report.removed.start_mm.join(", "))}) to (${esc(report.removed.end_mm.join(", "))}) mm.</p>` : "";
    const warnings = (report.warnings || []).map((line) => `<li>${esc(line)}</li>`).join("");
    const limitations = (report.limitations || []).map((line) => `<li>${esc(line)}</li>`).join("");
    $("#report").innerHTML = `
        <h2 id="report-title">${esc(report.title)}</h2>
        <p class="report-outcome"><span class="outcome" data-outcome="${esc(report.outcome)}">${esc(report.outcome.replaceAll("_", " "))}</span> ${esc(report.summary)}</p>
        ${findings ? `<h3>Recorded KiCad findings</h3><ul class="findings">${findings}</ul>` : ""}
        ${explanation ? `<h3>What this means</h3>${explanation}${removed}` : ""}
        <table><thead><tr><th>Check</th><th>Outcome</th><th>Checker</th><th>Detail</th></tr></thead><tbody>${rows}</tbody></table>
        ${warnings ? `<h3>Warnings kept</h3><ul>${warnings}</ul>` : ""}
        ${limitations ? `<h3>Limitations</h3><ul>${limitations}</ul>` : ""}
        <details><summary>Source artifact and recorded status</summary>
            <p>Board file SHA-256 <code>${esc(report.artifact)}</code>, recomputed in this browser: <code>${esc(verifiedHash)}</code>.</p>
            <p>Status: recorded receipt from a saved run. Nothing was generated or checked live.</p>
        </details>`;
    $("#download").hidden = !report.downloadable;
}

export async function initializeHackathonDemo({ fetcher = globalThis.fetch } = {}) {
    const canvas = $("#board");
    const status = (message, tone = "info") => {
        const node = $("#status");
        node.textContent = message;
        node.dataset.tone = tone;
    };
    let demo;
    try {
        demo = validateDemo(await (await fetchOk("demo.json", fetcher)).json());
    } catch {
        status("The saved demonstration could not load. Check that the offline server is running, then reload.", "error");
        return null;
    }
    $("#notice").textContent = demo.notice;
    $("#capture").textContent = `KiCad ${demo.capture.kicad_cli} · harness ${demo.capture.attempts_qualified} attempts qualified · commit ${demo.capture.git_commit.slice(0, 8)} · ${demo.capture.attempt_seconds.toFixed(1)} s recorded run`;
    const download = $("#download");
    download.href = BASE + demo.download.href;
    download.download = demo.download.href;

    const view = new BoardView(canvas, {});
    const selection = createSelection();
    const buttons = { good: $("#show-good"), fault: $("#show-fault") };
    const restore = $("#restore");

    async function select(which) {
        const token = selection.begin();
        Object.values(buttons).forEach((button) => { button.disabled = true; });
        restore.disabled = true;
        status(which === "fault" ? "Loading the damaged copy and verifying its file hash..." : "Loading the original board and verifying its file hash...");
        const entry = which === "fault" ? demo.fault : demo.good;
        const expected = which === "fault" ? demo.fault.snapshot_sha256 : demo.good.board.artifact_fingerprint;
        try {
            const bytes = await (await fetchOk(BOARD_FILES[which], fetcher)).arrayBuffer();
            const actual = await sha256Hex(bytes);
            if (!selection.isCurrent(token)) return;
            if (actual !== expected) throw new Error("hash mismatch");
            if (view.available !== false) {
                view.setBoard(entry.board);
                view.setHighlight(which === "fault" ? { nets: [demo.fault.removed_segment.net_name] } : {});
                view.frame();
                view.render();
            }
            renderReport(which === "fault" ? faultReport(demo) : goodReport(demo), actual);
            document.body.dataset.showing = which;
            buttons.good.setAttribute("aria-pressed", String(which === "good"));
            buttons.fault.setAttribute("aria-pressed", String(which === "fault"));
            status(which === "fault"
                ? "Showing the damaged copy. Its KiCad DRC result belongs to this copy only."
                : "Showing the original board and its recorded checks.");
        } catch {
            if (!selection.isCurrent(token)) return;
            status("That board could not be verified, so it is not shown. Restore the original to try again.", "error");
        } finally {
            if (selection.isCurrent(token)) {
                Object.values(buttons).forEach((button) => { button.disabled = false; });
                restore.disabled = false;
            }
        }
    }

    buttons.good.addEventListener("click", () => select("good"));
    buttons.fault.addEventListener("click", () => select("fault"));
    restore.addEventListener("click", async () => {
        await select("good");
        buttons.good.focus();
    });
    await select("good");
    return { view, select };
}

if (typeof document !== "undefined" && document.querySelector("#board")) initializeHackathonDemo();
