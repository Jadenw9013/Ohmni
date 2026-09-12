// Transport validation for saved projects. No engineering verdicts are computed here.
import { fail, sameIdentity, pollHeaders, fetchHealth, API_BASE } from "./client-contract.js";

const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const text = (value) => typeof value === "string" && value.length > 0;
const id = (value) => typeof value === "string" && /^[0-9a-f]{16}$/.test(value);
export const briefAddress = (brief) => brief.sensors[0]?.address ?? 118; // Legacy single-sensor callers.
export const FAMILY_IDS = ["a1_usb_i2c_sensor", "a2_usb_gpio_controller", "a3_usb_spi_peripheral"];
const integer = (value) => Number.isInteger(value) && value >= 0;
const finite = (value) => typeof value === "number" && Number.isFinite(value);

export const defaultProjectBrief = (options, familyId = FAMILY_IDS[0]) => options
    ? structuredClone(options.families.find((family) => family.id === familyId)?.defaults
        || options.families[0].defaults) : ({
    schema_version: 1, project_name: "My room climate monitor",
    description: "USB-C powered ESP32 room temperature and humidity monitor.",
    archetype: "a1_usb_i2c_sensor", input_power: "usb_c_5v", input_voltage_v: 5,
    logic_voltage_v: 3.3, mcu_part_id: "ESP32-WROOM-32E",
    sensors: [{ part_id: "BME280", address: 118 }], status_led_count: 1,
    include_programming_header: true, max_board_layers: 2,
    hand_solderable_preferred: true, budget_usd: 20, safety_domains: [],
});

export function supportedBrief(brief) {
    // This validates the editable transport, not whether a circuit is safe or
    // satisfiable. Capability ranges and defaults come from project-options;
    // actual address conflicts and engineering refusals belong to the server.
    return object(brief) && text(brief.project_name) && brief.project_name.trim().length > 0
        && brief.project_name.length <= 120 && brief.schema_version === 1
        && text(brief.description) && brief.description.length <= 1000
        && FAMILY_IDS.includes(brief.archetype) && brief.input_power === "usb_c_5v"
        && finite(brief.input_voltage_v) && brief.input_voltage_v >= 4.75 && brief.input_voltage_v <= 5.25
        && finite(brief.logic_voltage_v) && Math.abs(brief.logic_voltage_v - 3.3) <= 1e-9
        && brief.mcu_part_id === "ESP32-WROOM-32E" && brief.max_board_layers === 2
        && integer(brief.status_led_count) && integer(brief.button_count ?? 0)
        && typeof brief.include_programming_header === "boolean"
        && typeof brief.hand_solderable_preferred === "boolean"
        && (brief.budget_usd === null || finite(brief.budget_usd) && brief.budget_usd >= 0)
        && Array.isArray(brief.safety_domains) && brief.safety_domains.every(text)
        && Array.isArray(brief.sensors) && brief.sensors.every((sensor) => object(sensor) && text(sensor.part_id)
            && (sensor.address == null || integer(sensor.address) && sensor.address <= 127))
        && (brief.spi_devices === undefined || Array.isArray(brief.spi_devices)
            && brief.spi_devices.every((device) => object(device) && text(device.part_id)));
}

export function parseProjectOptions(payload, identity) {
    checkIdentity(payload, identity);
    const options = payload.options;
    const range = (value) => object(value) && integer(value.min) && integer(value.max)
        && value.max >= value.min && value.max <= 16;
    if (!object(options) || options.schema_version !== 1 || !Array.isArray(options.families)
        || options.families.length !== FAMILY_IDS.length
        || new Set(options.families.map((family) => family?.id)).size !== FAMILY_IDS.length
        || !options.families.every((family) => object(family) && FAMILY_IDS.includes(family.id)
            && text(family.title) && text(family.description)
            && ["sensor_count", "status_led_count", "button_count", "spi_count"].every((field) => range(family[field]))
            && Array.isArray(family.sensor_slot_defaults) && family.sensor_slot_defaults.length === family.sensor_count.max
            && family.sensor_slot_defaults.every((sensor) => object(sensor) && text(sensor.part_id) && sensor.address === null)
            && supportedBrief(family.defaults) && family.defaults.archetype === family.id)
        || !Array.isArray(options.sensors) || !options.sensors.length
        || !options.sensors.every((sensor) => object(sensor) && text(sensor.part_id) && text(sensor.label)
            && text(sensor.description) && Array.isArray(sensor.addresses) && sensor.addresses.length > 0
            && sensor.addresses.every((address) => integer(address) && address <= 127)
            && new Set(sensor.addresses).size === sensor.addresses.length)
        || new Set(options.sensors.map((sensor) => sensor.part_id)).size !== options.sensors.length
        || !Array.isArray(options.spi_devices) || !options.spi_devices.length
        || !options.spi_devices.every((device) => object(device) && text(device.part_id) && text(device.label) && text(device.description))
        || new Set(options.spi_devices.map((device) => device.part_id)).size !== options.spi_devices.length
        || !object(options.fixed) || !Array.isArray(options.limitations) || !options.limitations.every(text)) fail("api_ui_mismatch");
    if (!options.families.every((family) => briefFitsOptions(family.defaults, options)
        && family.sensor_slot_defaults.every((slot) => options.sensors.some((sensor) => sensor.part_id === slot.part_id)))) fail("api_ui_mismatch");
    return options;
}

export function briefFitsOptions(brief, options) {
    if (!supportedBrief(brief)) return false;
    const family = options.families.find((item) => item.id === brief.archetype);
    if (!family) return false;
    const inRange = (count, field) => count >= family[field].min && count <= family[field].max;
    return inRange(brief.sensors.length, "sensor_count") && inRange(brief.status_led_count, "status_led_count")
        && inRange(brief.button_count ?? 0, "button_count") && inRange(brief.spi_devices?.length ?? 0, "spi_count")
        && brief.sensors.every((sensor) => options.sensors.some((item) => item.part_id === sensor.part_id
            && (sensor.address == null || item.addresses.includes(sensor.address))))
        && (brief.spi_devices || []).every((device) => options.spi_devices.some((item) => item.part_id === device.part_id));
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
    const ordered = (value) => Array.isArray(value) ? value.map(ordered)
        : object(value) ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, ordered(value[key])])) : value;
    const normalized = (brief) => ({ ...brief, button_count: brief.button_count ?? 0,
        spi_devices: brief.spi_devices ?? [], sensors: brief.sensors.map((sensor) => ({ ...sensor, address: sensor.address ?? null })) });
    return Boolean(a && b) && JSON.stringify(ordered(normalized(a))) === JSON.stringify(ordered(normalized(b)));
}

export function briefChanges(previous, current) {
    if (!previous) return ["First saved configuration"];
    const changes = [];
    if (previous.project_name !== current.project_name) changes.push(`Renamed to ${current.project_name}`);
    if (previous.archetype !== current.archetype) changes.push("Changed the kind of board");
    if (previous.status_led_count !== current.status_led_count) changes.push(`Status lights: ${previous.status_led_count} → ${current.status_led_count}`);
    if ((previous.button_count ?? 0) !== (current.button_count ?? 0)) changes.push(`Buttons: ${previous.button_count ?? 0} → ${current.button_count ?? 0}`);
    if (previous.include_programming_header !== current.include_programming_header) changes.push(current.include_programming_header ? "Added the programming header" : "Omitted the programming header");
    const sensors = (brief) => brief.sensors.map((sensor) => `${sensor.part_id} (${sensor.address == null ? "automatic address" : `0x${sensor.address.toString(16).toUpperCase()}`})`).join(", ") || "none";
    if (sensors(previous) !== sensors(current)) changes.push(`Sensors: ${sensors(current)}`);
    const memories = (brief) => (brief.spi_devices || []).map((device) => device.part_id).join(", ") || "none";
    if (memories(previous) !== memories(current)) changes.push(`Memory devices: ${memories(current)}`);
    const visible = ["project_name", "archetype", "status_led_count", "button_count", "include_programming_header", "sensors", "spi_devices"];
    const remaining = { ...previous };
    for (const field of visible) remaining[field] = current[field];
    if (!sameBrief(remaining, current)) changes.push("Updated additional saved requirements");
    return changes.length ? changes : ["The complete configuration matches the previous revision"];
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
        response = await fetcher(API_BASE + path, { method, cache: "no-store", headers: {
            ...pollHeaders(current), ...(method === "GET" ? {} : { "content-type": "application/json" }),
        // Identity fields are named, never spread. The parsed health object also
        // carries capabilities, and the server checks request bodies for an exact
        // key set -- so spreading it would turn a new capability into a rejected
        // request for every project write.
        }, ...(method === "GET" ? {} : { body: JSON.stringify({
            api_version: current.api_version,
            server_instance_id: current.server_instance_id,
            ui_version: current.ui_version,
            ...data,
        }) }) });
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
