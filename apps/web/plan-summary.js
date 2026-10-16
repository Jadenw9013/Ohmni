import { escapeHtml as e } from "./view-model.js";

export function planSummaryHtml(brief, { requested = null, saved = false } = {}) {
    const rows = [];
    const add = (field, text) => rows.push(`<li>${e(text)}${requested && !requested.includes(field) ? ' <small>Suggested</small>' : ''}</li>`);
    if (brief.sensors?.length) add("sensors", `Sensing: ${brief.sensors.map(s => ({BME280:"temperature, humidity and pressure", TMP102AIDRLR:"temperature"})[s.part_id] || s.part_id).join("; ")}`);
    if (brief.button_count) add("button_count", `${brief.button_count} push button${brief.button_count === 1 ? "" : "s"}`);
    if (brief.status_led_count) add("status_led_count", `${brief.status_led_count} indicator light${brief.status_led_count === 1 ? "" : "s"}`);
    if (brief.spi_devices?.length) add("spi_devices", `${brief.spi_devices.length} memory chip${brief.spi_devices.length === 1 ? "" : "s"} for storing data`);
    add("input_power", brief.input_power === "usb_c_5v" ? "Powered through USB-C" : `Power: ${brief.input_power}`);
    return `<div class="compact-plan"><h2>${e(brief.project_name)}</h2><p>${saved ? "Your saved setup" : requested ? "Check this interpretation of your idea" : "Suggested setup — change anything below"}</p><ul>${rows.join("")}</ul><p class="plan-power-note">USB-C supplies power. Programming needs a separate adapter${brief.include_programming_header ? "; a programming connector is included" : "; you will need to provide programming access"}.</p><p class="plan-delivery-note">You’re creating board design files. Assembly, firmware (the program that runs on the board), and physical testing are separate steps.</p></div>`;
}
