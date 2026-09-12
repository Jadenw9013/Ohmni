// Time-domain plot of a SPICE transient. Inline SVG, no dependencies.
//
// This module draws; it does not decide. Every coordinate comes from the series
// the backend projected, and nothing is smoothed, resampled, extrapolated or
// zero-filled: a curve that has been "tidied" is a picture of the tidying. The
// only transformation is the linear map from a value to a pixel, and the axis
// labels state the range that map used, so a reader can check it.

const WIDTH = 620;
const HEIGHT = 260;
const PAD = { left: 56, right: 16, top: 16, bottom: 34 };
// Enough to read a settling curve; beyond this an SVG path stops being legible
// and starts being a large string. The backend already bounds what it sends.
const MAX_PLOTTED_POINTS = 600;
// Distinguishable at a glance and in both themes; last resort is a repeat.
const TRACE_COLOURS = ["#2159e8", "#e07b39", "#0f9d58", "#b3261e", "#8a4fff", "#00838f"];

const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[character]));

const finite = (value) => typeof value === "number" && Number.isFinite(value);

/** Engineering notation, so a millisecond axis does not read as 0.001. */
export function readable(value, unit) {
    if (!finite(value)) return "";
    const magnitude = Math.abs(value);
    if (magnitude === 0) return `0 ${unit}`;
    const steps = [
        [1e9, "G"], [1e6, "M"], [1e3, "k"], [1, ""],
        [1e-3, "m"], [1e-6, "µ"], [1e-9, "n"], [1e-12, "p"],
    ];
    const [scale, prefix] = steps.find(([factor]) => magnitude >= factor) || [1e-12, "p"];
    const scaled = value / scale;
    const digits = Math.abs(scaled) >= 100 ? 0 : Math.abs(scaled) >= 10 ? 1 : 2;
    return `${scaled.toFixed(digits)} ${prefix}${unit}`;
}

/** Keep at most `limit` points, always including the first and the last. */
function thin(values, limit) {
    if (values.length <= limit) return values.map((value, index) => index);
    const step = Math.ceil(values.length / limit);
    const kept = [];
    for (let index = 0; index < values.length; index += step) kept.push(index);
    if (kept[kept.length - 1] !== values.length - 1) kept.push(values.length - 1);
    return kept;
}

/**
 * Build the SVG for one transient result, or return null when there is nothing
 * honest to draw. A caller that gets null must say why itself -- an empty plot
 * frame implies a circuit that did nothing, which is a different claim.
 */
export function scopeSvg(transient) {
    if (!transient || !Array.isArray(transient.time_s) || !Array.isArray(transient.series)) return null;
    const times = transient.time_s.filter(finite);
    if (times.length < 2) return null;
    const usable = transient.series
        .filter((item) => item && Array.isArray(item.values) && item.values.length === transient.time_s.length)
        .map((item, index) => ({
            name: String(item.name ?? `signal ${index + 1}`),
            unit: item.unit === "A" ? "A" : "V",
            values: item.values,
            colour: TRACE_COLOURS[index % TRACE_COLOURS.length],
        }));
    // One axis carries one quantity. Drawing amperes against a volt scale would
    // put two different measurements on the same gridline and label both wrong,
    // so a mixed result plots the first unit and `omitted` reports the rest.
    const unit = usable.length ? usable[0].unit : "V";
    const series = usable.filter((item) => item.unit === unit);
    if (!series.length) return null;

    const sampled = thin(times, MAX_PLOTTED_POINTS);
    const readings = series.flatMap((item) => item.values.filter(finite));
    if (!readings.length) return null;
    const timeMin = Math.min(...times);
    const timeMax = Math.max(...times);
    let low = Math.min(...readings, 0);
    let high = Math.max(...readings, 0);
    if (high === low) high = low + 1;               // a flat trace still needs a scale
    const headroom = (high - low) * 0.08;
    // Headroom only where the trace could use it. A gridline at -400 mV under a
    // rail that never goes negative invites the reader to see a dip that the
    // simulation did not produce.
    const lowest = Math.min(...readings);
    const highest = Math.max(...readings);
    low = lowest < 0 ? low - headroom : Math.min(low, 0);
    high = highest > 0 ? high + headroom : Math.max(high, 0);
    if (timeMax === timeMin) return null;

    const plotWidth = WIDTH - PAD.left - PAD.right;
    const plotHeight = HEIGHT - PAD.top - PAD.bottom;
    const x = (time) => PAD.left + ((time - timeMin) / (timeMax - timeMin)) * plotWidth;
    const y = (value) => PAD.top + (1 - (value - low) / (high - low)) * plotHeight;

    const gridLines = [];
    for (let step = 0; step <= 4; step += 1) {
        const value = low + ((high - low) * step) / 4;
        const position = y(value).toFixed(1);
        gridLines.push(
            `<line class="scope-grid" x1="${PAD.left}" y1="${position}" x2="${WIDTH - PAD.right}" y2="${position}"/>`
            + `<text class="scope-tick" x="${PAD.left - 8}" y="${position}" text-anchor="end" dominant-baseline="middle">`
            + `${escapeHtml(readable(value, unit))}</text>`,
        );
    }
    for (let step = 0; step <= 4; step += 1) {
        const time = timeMin + ((timeMax - timeMin) * step) / 4;
        const position = x(time).toFixed(1);
        gridLines.push(
            `<line class="scope-grid" x1="${position}" y1="${PAD.top}" x2="${position}" y2="${HEIGHT - PAD.bottom}"/>`
            + `<text class="scope-tick" x="${position}" y="${HEIGHT - PAD.bottom + 16}" text-anchor="middle">`
            + `${escapeHtml(readable(time, "s"))}</text>`,
        );
    }

    const traces = series.map((item) => {
        const points = sampled
            .filter((index) => finite(item.values[index]))
            .map((index) => `${x(times[index]).toFixed(1)},${y(item.values[index]).toFixed(1)}`);
        return points.length < 2 ? "" : `<polyline class="scope-trace" fill="none" stroke="${item.colour}"`
            + ` data-signal="${escapeHtml(item.name)}" points="${points.join(" ")}"/>`;
    }).join("");

    const legend = series.map((item) => `<span class="scope-key">`
        + `<i style="background:${item.colour}" aria-hidden="true"></i>${escapeHtml(item.name)}</span>`).join("");

    const omitted = usable.length - series.length;
    const note = omitted > 0
        ? `<p class="fineprint">${omitted} signal(s) in a different unit are not plotted here.</p>`
        : "";
    return `<div class="scope">
        <svg viewBox="0 0 ${WIDTH} ${HEIGHT}" class="scope-svg" role="img"
             aria-label="${escapeHtml(`Simulated ${series.map((item) => item.name).join(", ")} `
                 + `from ${readable(timeMin, "s")} to ${readable(timeMax, "s")}`)}">
            <rect class="scope-face" x="${PAD.left}" y="${PAD.top}" width="${plotWidth}" height="${plotHeight}"/>
            ${gridLines.join("")}${traces}
        </svg>
        <div class="scope-legend">${legend}</div>${note}
    </div>`;
}

/**
 * Render the simulation section of a completed report.
 *
 * A run that produced no curve is reported as what it was -- unavailable,
 * failed, or never attempted -- rather than as an empty graph.
 */
export function scopeHtml(simulation) {
    if (!simulation || typeof simulation !== "object") {
        return `<h3>Power-on behaviour</h3><p class="panel-note">No simulation was attempted for this design.</p>`;
    }
    const plot = scopeSvg(simulation.transient);
    const limitation = simulation.limitation
        ? `<p class="fineprint">${escapeHtml(simulation.limitation)}</p>` : "";
    if (!plot) {
        const status = String(simulation.status || "UNKNOWN");
        const because = simulation.detail ? ` ${escapeHtml(simulation.detail)}` : "";
        return `<h3>Power-on behaviour</h3>
            <p class="panel-note">No curve was produced: the simulator reported
            <strong>${escapeHtml(status)}</strong>.${because}</p>
            <p class="fineprint">A missing simulation is not a passed one. Nothing on this
            page depends on it; the electrical checks stand on their own.</p>`;
    }
    const transient = simulation.transient;
    const thinned = transient.decimated_from
        ? ` Thinned from ${transient.decimated_from} simulator steps.` : "";
    return `<h3>Power-on behaviour</h3>
        <p class="panel-note">What the voltages do in the first moments after power is applied,
        from <code>${escapeHtml(transient.analysis || "a transient analysis")}</code> over
        ${transient.sample_count} samples.${escapeHtml(thinned)}</p>
        ${plot}${limitation}`;
}
