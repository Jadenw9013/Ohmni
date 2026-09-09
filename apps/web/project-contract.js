// Transport validation for saved projects. No engineering verdicts are computed here.
import { fail, sameIdentity, pollHeaders, fetchHealth } from "./client-contract.js";

const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const text = (value) => typeof value === "string" && value.length > 0;
const id = (value) => typeof value === "string" && /^[0-9a-f]{16}$/.test(value);
export const briefAddress = (brief) => brief.sensors[0].address ?? 118;

export const defaultProjectBrief = () => ({
    schema_version: 1, project_name: "My room climate monitor",
    description: "USB-C powered ESP32 room temperature and humidity monitor.",
    archetype: "a1_usb_i2c_sensor", input_power: "usb_c_5v", input_voltage_v: 5,
    logic_voltage_v: 3.3, mcu_part_id: "ESP32-WROOM-32E",
    sensors: [{ part_id: "BME280", address: 118 }], status_led_count: 1,
    include_programming_header: true, max_board_layers: 2,
    hand_solderable_preferred: true, budget_usd: 20, safety_domains: [],
});

export function supportedBrief(brief) {
    return object(brief) && text(brief.project_name) && brief.project_name.trim().length > 0
        && brief.project_name.length <= 120 && brief.schema_version === 1
        && brief.archetype === "a1_usb_i2c_sensor" && brief.input_power === "usb_c_5v"
        && brief.input_voltage_v === 5 && brief.logic_voltage_v === 3.3
        && brief.mcu_part_id === "ESP32-WROOM-32E" && brief.max_board_layers === 2
        && [0, 1].includes(brief.status_led_count) && typeof brief.include_programming_header === "boolean"
        && Array.isArray(brief.sensors) && brief.sensors.length === 1
        && brief.sensors[0]?.part_id === "BME280" && [null, 118, 119].includes(brief.sensors[0]?.address);
}

export function parseProjectEnvelope(payload, identity) {
    checkIdentity(payload, identity);
    const project = payload.project;
    if (!object(project) || !id(project.project_id) || !text(project.created_at)
        || !text(project.updated_at) || !Array.isArray(project.revisions) || !project.revisions.length) fail("api_ui_mismatch");
    const seen = new Set();
    project.revisions.forEach((revision, i) => {
        if (!object(revision) || !id(revision.revision_id) || seen.has(revision.revision_id)
            || revision.number !== i + 1 || !text(revision.created_at) || !supportedBrief(revision.brief)
            || !/^[0-9a-f]{64}$/.test(revision.brief_fingerprint) || !object(revision.preview)
            || !["asked_for", "assumed", "needs_clarification"].every((field) => Array.isArray(revision.preview[field])
                && revision.preview[field].every((line) => object(line) && text(line.label) && typeof line.value === "string"))
            || !(revision.job_id === null || /^[0-9a-f]{12}$/.test(revision.job_id))) fail("api_ui_mismatch");
        seen.add(revision.revision_id);
    });
    return project;
}

export function parseProjectList(payload, identity) {
    checkIdentity(payload, identity);
    if (!Array.isArray(payload.projects) || !payload.projects.every((project) => object(project)
        && id(project.project_id) && text(project.name) && id(project.latest_revision_id)
        && Number.isInteger(project.revision_count) && project.revision_count > 0)) fail("api_ui_mismatch");
    return payload.projects;
}

export function checkIdentity(payload, identity) {
    if (!object(payload) || payload.api_version !== identity.api_version) fail("api_ui_mismatch");
    if (!sameIdentity(payload, identity)) fail("generation_mismatch");
}

export function sameBrief(a, b) {
    return Boolean(a && b) && a.project_name === b.project_name
        && a.status_led_count === b.status_led_count
        && a.include_programming_header === b.include_programming_header
        && briefAddress(a) === briefAddress(b);
}

export function briefChanges(previous, current) {
    if (!previous) return ["First saved configuration"];
    const changes = [];
    if (previous.project_name !== current.project_name) changes.push(`Renamed to ${current.project_name}`);
    if (previous.status_led_count !== current.status_led_count) changes.push(current.status_led_count ? "Added the status LED and its resistor" : "Omitted the status LED and its resistor");
    if (previous.include_programming_header !== current.include_programming_header) changes.push(current.include_programming_header ? "Added the programming header" : "Omitted the programming header");
    if (briefAddress(previous) !== briefAddress(current)) changes.push(`Changed the sensor address to ${briefAddress(current) === 118 ? "0x76" : "0x77"}`);
    return changes.length ? changes : ["The visible choices match the previous revision"];
}

export function parseProjectStart(payload, identity) {
    checkIdentity(payload, identity);
    if (!/^[0-9a-f]{12}$/.test(payload.job_id)
        || !["queued", "running", "complete", "failed"].includes(payload.status)) fail("api_ui_mismatch");
    return payload.job_id;
}

export class ProjectRequestError extends Error {
    constructor(message) { super(message); this.name = "ProjectRequestError"; }
}

export async function projectRequest(path, { fetcher = globalThis.fetch, identity, method = "GET", data } = {}) {
    const current = identity || await fetchHealth(fetcher);
    let response;
    try {
        response = await fetcher(path, { method, cache: "no-store", headers: {
            ...pollHeaders(current), ...(method === "GET" ? {} : { "content-type": "application/json" }),
        }, ...(method === "GET" ? {} : { body: JSON.stringify({ ...current, ...data }) }) });
    } catch { throw new ProjectRequestError("The server is unreachable. Check the local Ohmni server, then try again. Your edits are still here."); }
    let payload;
    try { payload = await response.json(); } catch { fail("api_ui_mismatch"); }
    if (!response.ok) {
        if (["server_instance_mismatch", "ui_version_mismatch"].includes(payload?.error)) fail("generation_mismatch");
        const refusal = payload?.refusal?.message;
        const messages = {
            project_not_found: "This saved project is unavailable. Refresh the project list and try again.",
            revision_not_found: "This revision is unavailable. Reopen the saved project.",
            invalid_project_request: "These choices are not supported. Check the project settings before saving.",
            invalid_exercise_choice: "Choose one of the available repairs, then try again.",
            job_start_unavailable: "The server cannot start another run right now. Wait for an active run to finish, then try again.",
        };
        throw new ProjectRequestError(typeof refusal === "string" ? refusal : messages[payload?.error]
            || "The server could not complete this action. Your edits are still here. Try again.");
    }
    checkIdentity(payload, current);
    return { payload, identity: current };
}
