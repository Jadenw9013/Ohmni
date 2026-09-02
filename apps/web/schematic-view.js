// Schematic rendering, and the schematic-to-board transition.
//
// Pure geometry in, SVG markup out. Both layouts are real: the schematic
// positions come from the compiled KiCad sheet, the board positions from the
// compiled PCB. The transition tweens between those two real layouts and
// cross-fades the symbols for the footprints. It is deliberately not a
// geometric morph, because a symbol and a footprint have no shape relationship
// and pretending otherwise would teach something false.

import { escapeHtml } from "./view-model.js";

const PAD = 26;

const unit = (value) => Math.min(1, Math.max(0, value));

function bounds(items, sizeFor) {
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const item of items) {
        const { w, h } = sizeFor(item);
        minX = Math.min(minX, item.x_mm - w / 2);
        maxX = Math.max(maxX, item.x_mm + w / 2);
        minY = Math.min(minY, item.y_mm - h / 2);
        maxY = Math.max(maxY, item.y_mm + h / 2);
    }
    if (!Number.isFinite(minX)) return { minX: 0, minY: 0, maxX: 1, maxY: 1 };
    return { minX, minY, maxX, maxY };
}

/**
 * Normalised 0..1 positions for one ref in each layout.
 *
 * app.js tweens between them. Returned per ref so a component that exists in
 * only one layout is simply absent rather than invented.
 */
export function transitionTracks(schematic, board) {
    const symbolBounds = bounds(schematic.symbols, (s) => ({ w: s.width_mm, h: s.height_mm }));
    const partBounds = bounds(board.components, (c) => ({ w: c.width_mm, h: c.height_mm }));
    const normalise = (value, min, max) => (max - min < 1e-6 ? 0.5 : (value - min) / (max - min));
    const boardByRef = new Map(board.components.map((c) => [c.ref, c]));
    const tracks = [];
    for (const symbol of schematic.symbols) {
        const part = boardByRef.get(symbol.ref);
        if (!part) continue;
        tracks.push({
            ref: symbol.ref,
            system: symbol.system,
            from: {
                x: normalise(symbol.x_mm, symbolBounds.minX, symbolBounds.maxX),
                y: normalise(symbol.y_mm, symbolBounds.minY, symbolBounds.maxY),
                w: symbol.width_mm, h: symbol.height_mm,
            },
            to: {
                x: normalise(part.x_mm, partBounds.minX, partBounds.maxX),
                y: normalise(part.y_mm, partBounds.minY, partBounds.maxY),
                w: part.width_mm, h: part.height_mm,
            },
        });
    }
    return tracks.sort((a, b) => (a.ref < b.ref ? -1 : 1));
}

/** Interpolate one transition frame. `t` runs 0 (schematic) to 1 (board). */
export function transitionFrame(tracks, t) {
    const clamped = Math.min(1, Math.max(0, t));
    const ease = clamped < 0.5
        ? 2 * clamped * clamped
        : 1 - ((-2 * clamped + 2) ** 2) / 2;
    return tracks.map((track) => ({
        ref: track.ref,
        system: track.system,
        x: track.from.x + (track.to.x - track.from.x) * ease,
        y: track.from.y + (track.to.y - track.from.y) * ease,
        w: track.from.w + (track.to.w - track.from.w) * ease,
        h: track.from.h + (track.to.h - track.from.h) * ease,
        // Endpoints are pinned rather than computed, so a finished transition
        // is exactly the board and a fresh one is exactly the schematic.
        symbolOpacity: ease >= 1 ? 0 : ease <= 0 ? 1 : unit(1 - ease * 1.9),
        footprintOpacity: ease >= 1 ? 1 : ease <= 0 ? 0 : unit(ease * 1.9 - 0.9),
    }));
}

/** Render the compiled schematic sheet as interactive SVG. */
export function schematicSvg(schematic, { highlight = {}, selected = null } = {}) {
    const scale = 4.4;
    const box = bounds(schematic.symbols, (s) => ({ w: s.width_mm, h: s.height_mm }));
    const width = (box.maxX - box.minX) * scale + PAD * 2;
    const height = (box.maxY - box.minY) * scale + PAD * 2;
    const refs = new Set(highlight.refs || []);
    const nets = new Set(highlight.nets || []);
    const dimming = refs.size > 0 || nets.size > 0;
    const x = (mm) => PAD + (mm - box.minX) * scale;
    const y = (mm) => PAD + (mm - box.minY) * scale;

    const parts = [];
    for (const symbol of schematic.symbols) {
        const lit = !dimming || refs.has(symbol.ref)
            || symbol.pins.some((pin) => pin.net_name && nets.has(pin.net_name));
        const left = x(symbol.x_mm - symbol.width_mm / 2);
        const top = y(symbol.y_mm - symbol.height_mm / 2);
        parts.push(
            `<g class="sym${lit ? "" : " dim"}${symbol.ref === selected ? " sel" : ""}" `
            + `data-ref="${escapeHtml(symbol.ref)}" data-system="${escapeHtml(symbol.system)}" `
            + `tabindex="0" role="button" aria-label="${escapeHtml(symbol.ref)} ${escapeHtml(symbol.part_id)}">`
            + `<rect x="${left.toFixed(1)}" y="${top.toFixed(1)}" `
            + `width="${(symbol.width_mm * scale).toFixed(1)}" `
            + `height="${(symbol.height_mm * scale).toFixed(1)}" rx="3"/>`
            + `<text x="${(left + 6).toFixed(1)}" y="${(top + 14).toFixed(1)}">`
            + `${escapeHtml(symbol.ref)}</text>`
            + `<text class="sym-part" x="${(left + 6).toFixed(1)}" y="${(top + 26).toFixed(1)}">`
            + `${escapeHtml(symbol.part_id)}</text>`
            + symbol.pins.map((pin) => {
                const px = x(pin.x_mm);
                const py = y(pin.y_mm);
                const netLit = !dimming || (pin.net_name && nets.has(pin.net_name)) || refs.has(symbol.ref);
                return `<g class="pin${netLit ? "" : " dim"}" data-net="${escapeHtml(pin.net_name || "")}">`
                    + `<circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="2.4"/>`
                    + `<text x="${(px + 4).toFixed(1)}" y="${(py + 3).toFixed(1)}">`
                    + `${escapeHtml(pin.net_name || "not connected")}</text></g>`;
            }).join("")
            + "</g>",
        );
    }
    return `<svg class="schematic" viewBox="0 0 ${width.toFixed(0)} ${height.toFixed(0)}" `
        + `role="img" aria-label="Compiled schematic sheet" `
        + `data-fingerprint="${escapeHtml(schematic.artifact_fingerprint)}">${parts.join("")}</svg>`;
}
