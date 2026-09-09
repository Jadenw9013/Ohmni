export function tone(status){const value=(status||"UNKNOWN").toUpperCase();if(value==="PASS"||value==="VERIFIED")return"pass";if(value==="NOT_VERIFIED"||value.includes("FAIL")||value.includes("ERROR")||value.includes("BLOCK"))return"fail";if(value.includes("NOT_YET")||value.includes("UNSUPPORTED"))return"notyet";return"warn"}
export function badge(status){const safe=String(status||"UNKNOWN").replaceAll("_"," ");return `<span class="badge ${tone(status)}">${escapeHtml(safe)}</span>`}
export function money(value,knowledge="KNOWN"){return knowledge==="UNKNOWN"||value==null?"UNKNOWN":`$${Number(value).toFixed(2)}`}
export function artifactCurrent(item){return item?.current===true?"CURRENT":"STALE"}
export function releaseReadiness(release){const current=release?.current===true,status=current?String(release?.status||"UNKNOWN"):"STALE";return{status,label:current&&status==="READY_FOR_MANUFACTURING_REVIEW"?"Ready for manufacturing review":"Release is stale or not ready"}}
export function escapeHtml(value){return String(value??"").replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]))}

export function requirementResultsHtml(rows) {
    const tones = { MET: "pass", VIOLATED: "fail", UNKNOWN: "warn" };
    if (!Array.isArray(rows) || !rows.length || !rows.every((row) => row && typeof row.field === "string"
        && typeof row.value === "string" && (row.display_value === undefined || typeof row.display_value === "string")
        && typeof row.status === "string" && Object.hasOwn(tones, row.status) && typeof row.detail === "string"
        && Array.isArray(row.rule_ids) && row.rule_ids.every((rule) => typeof rule === "string"))) return null;
    const labels = { project_name: "Project name", description: "Project purpose", archetype: "Board family",
        input_power: "Power connection", input_voltage_v: "Input supply", logic_voltage_v: "Logic supply",
        mcu_part_id: "Processor", sensor_count: "Sensors", status_led_count: "Status lights", button_count: "Buttons",
        spi_count: "Memory devices", include_programming_header: "Programming header", max_board_layers: "Board layers",
        hand_solderable_preferred: "Hand soldering preference", budget_usd: "Budget preference", safety_domains: "Requested safety scope",
        assumption: "A design assumption" };
    const label = (field) => {
        const sensor = /^sensors\.(\d+)\.(part_id|address)$/.exec(field);
        if (sensor) return `Sensor ${Number(sensor[1]) + 1} ${sensor[2] === "address" ? "address" : "part"}`;
        const memory = /^spi_devices\.(\d+)\.part_id$/.exec(field);
        return memory ? `Memory ${Number(memory[1]) + 1}` : labels[field] || field.replaceAll("_", " ");
    };
    const renderRow = (row) => `<div class="requirement-result"><h3>${escapeHtml(row.label || label(row.field))}: ${escapeHtml(row.display_value ?? row.value)}</h3><span class="badge ${tones[row.status]}">${escapeHtml(row.status[0] + row.status.slice(1).toLowerCase())}</span><p>${escapeHtml(row.detail)}</p>${row.rule_ids.length ? `<small>Recorded checks: ${row.rule_ids.map(escapeHtml).join(", ")}</small>` : ""}</div>`;
    const choices = rows.filter((row) => row.origin !== "assumption");
    const assumptions = rows.filter((row) => row.origin === "assumption");
    return choices.map(renderRow).join("") + (assumptions.length
        ? `<details class="requirement-assumptions"><summary>Assumptions and limits (${assumptions.length})</summary>${assumptions.map(renderRow).join("")}</details>` : "");
}
