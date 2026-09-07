// Display geometry only. Footprints, pads, net membership and copper paths come
// unchanged from board-model. Package silhouettes, heights, finishes and shadows
// below are explicitly illustrative; they are not component or fabrication data.

export const VERTEX_STRIDE = 12;
export const DISPLAY_HEIGHTS = Object.freeze({ module: 2.8, usb: 3.4, header: 5.5,
    sensor: 1.1, capacitor: 0.65, resistor: 0.48, led: 0.8, chip: 1.15 });

const MAT = Object.freeze({
    // RGB, roughness, metal (0/1), finish (plain/brushed/mask/lens/laminate).
    // Finishes are display styles. No physical material specification is known.
    board: [0.045, 0.32, 0.32, 0.55, 0, 2], edge: [0.37, 0.35, 0.23, 0.86, 0, 4],
    reverse: [0.035, 0.25, 0.285, 0.58, 0, 2], gold: [0.91, 0.66, 0.28, 0.26, 1],
    copper: [0.13, 0.40, 0.375, 0.52, 0, 2], backCopper: [0.10, 0.33, 0.37, 0.55, 0, 2],
    silver: [0.61, 0.65, 0.67, 0.42, 1, 1], rim: [0.76, 0.80, 0.82, 0.24, 1],
    solder: [0.64, 0.68, 0.71, 0.29, 1], darkMetal: [0.22, 0.26, 0.29, 0.41, 1, 1],
    charcoal: [0.055, 0.065, 0.07, 0.72], black: [0.012, 0.018, 0.022, 0.88],
    ceramic: [0.52, 0.33, 0.16, 0.48], module: [0.04, 0.13, 0.12, 0.44, 0, 2],
    sensor: [0.56, 0.53, 0.40, 0.31, 1, 1], green: [0.08, 0.35, 0.20, 0.18, 0, 3],
    cyan: [0.34, 0.94, 1, 0.28], white: [0.81, 0.80, 0.69, 0.64],
});

/** Choosing a drawing style from an explicit part identifier changes no facts. */
export function displayPackageKind(part) {
    const id = String(part.partId || "").toUpperCase();
    if (/WROOM|MODULE/.test(id)) return "module";
    if (/USB.*RECEPTACLE|USB.*CONNECTOR/.test(id)) return "usb";
    if (/HEADER/.test(id)) return "header";
    if (/BME280|BMP280/.test(id)) return "sensor";
    if (/CAPACITOR/.test(id)) return "capacitor";
    if (/RESISTOR/.test(id)) return "resistor";
    if (/LED/.test(id)) return "led";
    return "chip";
}

function normal(a, b, c) {
    const u = { x: b.x - a.x, y: b.y - a.y, z: b.z - a.z };
    const v = { x: c.x - a.x, y: c.y - a.y, z: c.z - a.z };
    const x = u.y * v.z - u.z * v.y;
    const y = u.z * v.x - u.x * v.z;
    const z = u.x * v.y - u.y * v.x;
    const d = Math.hypot(x, y, z) || 1;
    return [x / d, y / d, z / d];
}

function vertex(buffer, p, n, m, alpha = 1, emission = 0) {
    // Packing the finish preserves the existing 12-float mesh and fallback ABI.
    const finish = m[3] + (m[4] || 0) * 2 + (m[5] || 0) * 4;
    buffer.push(p.x, p.y, p.z, ...n, m[0], m[1], m[2], finish, emission, alpha);
}

function face(buffer, points, material, { alpha = 1, emission = 0, flip = false } = {}) {
    const ordered = flip ? points.slice().reverse() : points;
    const n = normal(ordered[0], ordered[1], ordered[2]);
    for (let i = 1; i < ordered.length - 1; i += 1) {
        for (const p of [ordered[0], ordered[i], ordered[i + 1]]) vertex(buffer, p, n, material, alpha, emission);
    }
}

/** Local fractional coordinates preserve the authoritative rotated footprint. */
export function pointOnFootprint(part, u, v, height = 0) {
    const [a, b, , d] = part.points;
    return { x: a.x + (b.x - a.x) * u + (d.x - a.x) * v,
        y: a.y + (b.y - a.y) * u + (d.y - a.y) * v,
        z: a.z + (part.side === "B.Cu" ? -height : height) };
}

function rectangle(part, x0, y0, x1, y1, height) {
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map(([u, v]) => pointOnFootprint(part, u, v, height));
}

function prism(buffer, bottom, top, material, { topMaterial = material, alpha = 1, emission = 0 } = {}) {
    const back = top[0].z < bottom[0].z;
    face(buffer, top, topMaterial, { flip: back, alpha, emission });
    face(buffer, bottom, material, { flip: !back, alpha, emission });
    for (let i = 0; i < bottom.length; i += 1) {
        const j = (i + 1) % bottom.length;
        face(buffer, [bottom[i], bottom[j], top[j], top[i]], material, { flip: back, alpha, emission });
    }
}

function footprintSize(part) {
    return { width: Math.hypot(part.points[1].x - part.points[0].x, part.points[1].y - part.points[0].y),
        height: Math.hypot(part.points[3].x - part.points[0].x, part.points[3].y - part.points[0].y) };
}

/** Rounded bevel rings stay inside the projected footprint bounds. */
function bevelRing(part, bounds, z, inset, corner) {
    const size = footprintSize(part);
    const [x0, y0, x1, y1] = bounds;
    const xInset = inset / size.width, yInset = inset / size.height;
    const left = x0 + xInset, right = x1 - xInset;
    const lower = y0 + yInset, upper = y1 - yInset;
    const cx = Math.min(corner / size.width, (right - left) * 0.23);
    const cy = Math.min(corner / size.height, (upper - lower) * 0.23);
    return [[left + cx, lower], [right - cx, lower], [right, lower + cy], [right, upper - cy],
        [right - cx, upper], [left + cx, upper], [left, upper - cy], [left, lower + cy]]
        .map(([u, v]) => pointOnFootprint(part, u, v, z));
}

function ringWalls(buffer, a, b, material, flip) {
    for (let index = 0; index < a.length; index += 1) {
        const next = (index + 1) % a.length;
        face(buffer, [a[index], a[next], b[next], b[index]], material, { flip });
    }
}

function beveledBox(buffer, part, bounds, from, to, material,
    { bevel = 0.11, corner = 0.07, topMaterial = material } = {}) {
    const size = footprintSize(part);
    const span = Math.min((bounds[2] - bounds[0]) * size.width, (bounds[3] - bounds[1]) * size.height);
    const edge = Math.min(bevel, (to - from) * 0.28, span * 0.15);
    const rings = [bevelRing(part, bounds, from, edge * 0.4, corner),
        bevelRing(part, bounds, from + edge, 0, corner),
        bevelRing(part, bounds, to - edge, 0, corner),
        bevelRing(part, bounds, to, edge, corner)];
    const back = part.side === "B.Cu";
    face(buffer, rings[0], material, { flip: !back });
    for (let index = 1; index < rings.length; index += 1) ringWalls(buffer, rings[index - 1], rings[index], material, back);
    face(buffer, rings[3], topMaterial, { flip: back });
}

/** A raised solder finish is an illustration confined to each real pad. */
function solderFillet(buffer, pad, material) {
    const sign = pad.points[0].z < 0 ? -1 : 1;
    const part = { points: pad.points, side: sign < 0 ? "B.Cu" : "F.Cu" };
    const size = footprintSize(part);
    const small = Math.min(size.width, size.height);
    const height = Math.min(0.21, small * 0.27);
    const rings = [bevelRing(part, [0.04, 0.04, 0.96, 0.96], 0.135, 0, small * 0.16),
        bevelRing(part, [0.04, 0.04, 0.96, 0.96], 0.135 + height * 0.7, small * 0.11, small * 0.19),
        bevelRing(part, [0.04, 0.04, 0.96, 0.96], 0.135 + height, small * 0.22, small * 0.16)];
    for (let index = 1; index < rings.length; index += 1) ringWalls(buffer, rings[index - 1], rings[index], material, sign < 0);
    face(buffer, rings[2], material, { flip: sign < 0 });
}

function tint(material, item, matcher, selected) {
    if (item.ref && item.ref === selected) return [
        material[0] * 0.9 + 0.025, material[1] * 0.9 + 0.055, material[2] * 0.9 + 0.06, ...material.slice(3)];
    if (!matcher?.active || matcher.matches(item)) return material;
    return [material[0] * 0.35 + 0.012, material[1] * 0.35 + 0.018,
        material[2] * 0.35 + 0.025, Math.min(0.95, material[3] + 0.22), ...material.slice(4)];
}

function disc(buffer, centre, radius, material, { inner = 0, alpha = 1, segments = 16, sign = 1 } = {}) {
    for (let i = 0; i < segments; i += 1) {
        const a = (i / segments) * Math.PI * 2;
        const b = ((i + 1) / segments) * Math.PI * 2;
        const at = (angle, r) => ({ x: centre.x + Math.cos(angle) * r,
            y: centre.y + Math.sin(angle) * r, z: centre.z });
        if (inner > 0) face(buffer, [at(a, inner), at(a, radius), at(b, radius), at(b, inner)], material, { alpha, flip: sign < 0 });
        else face(buffer, [centre, at(a, radius), at(b, radius)], material, { alpha, flip: sign < 0 });
    }
}

/** Ribbon width and end points exactly retain the projected copper segment. */
export function trackRibbon(track, displayLift = 0.045) {
    const dx = track.b.x - track.a.x;
    const dy = track.b.y - track.a.y;
    const length = Math.hypot(dx, dy);
    if (length < 1e-10 || !Number.isFinite(length)) return [];
    const ox = (-dy / length) * track.width / 2;
    const oy = (dx / length) * track.width / 2;
    const z = track.a.z + (track.layer === "F.Cu" ? displayLift : -displayLift);
    return [{ x: track.a.x - ox, y: track.a.y - oy, z },
        { x: track.b.x - ox, y: track.b.y - oy, z },
        { x: track.b.x + ox, y: track.b.y + oy, z },
        { x: track.a.x + ox, y: track.a.y + oy, z }];
}

function contactShadow(buffer, part, height) {
    // A soft, neutral display shadow. It never changes a pad, net or copper path.
    for (let step = 6; step > 0; step -= 1) {
        const spread = step * 0.028;
        const points = rectangle(part, -spread, -spread, 1 + spread, 1 + spread, 0.015);
        face(buffer, points, MAT.black, { alpha: 0.042 + height * 0.012, flip: part.side === "B.Cu" });
    }
}

// Compact strokes are actual reference designators, rendered as illustrative
// ink. No logos, electrical symbols, part values or fabricated IDs are added.
const STROKE = Object.freeze({
    a: [0, 1, 0.55, 1], b: [0.55, 1, 0.55, 0.5], c: [0.55, 0.5, 0.55, 0],
    d: [0, 0, 0.55, 0], e: [0, 0, 0, 0.5], f: [0, 0.5, 0, 1], g: [0, 0.5, 0.55, 0.5],
    h: [0, 1, 0.55, 0], i: [0.275, 1, 0.275, 0], j: [0, 0.5, 0.55, 0],
    k: [0, 1, 0.55, 0.5], l: [0.55, 0.5, 0, 0],
});
const GLYPHS = Object.freeze({ 0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc",
    5: "afgcd", 6: "afgecd", 7: "abc", 8: "abcdefg", 9: "abfgcd", A: "abcefg",
    B: "fegcd", C: "afed", D: "bcdeg", E: "afged", F: "afge", G: "afedcg", H: "fbgec",
    I: "adi", J: "bcde", K: "fekl", L: "fed", N: "fehbc", O: "abcdef", P: "abfge",
    R: "abfgej", S: "afgcd", T: "ai", U: "febcd", X: "hlk", Y: "ki", Z: "ald", "-": "g" });

function referenceInk(buffer, part, material) {
    const size = footprintSize(part);
    const text = String(part.ref).toUpperCase();
    const height = 0.85;
    const spacing = height * 0.77;
    const width = text.length * spacing - height * 0.22;
    const left = (size.width - width) / 2;
    const baseline = -1.13;
    const thickness = 0.065;
    for (let index = 0; index < text.length; index += 1) {
        for (const key of GLYPHS[text[index]] || "") {
            const [x0, y0, x1, y1] = STROKE[key];
            const ax = left + index * spacing + x0 * height, ay = baseline + y0 * height;
            const bx = left + index * spacing + x1 * height, by = baseline + y1 * height;
            const length = Math.hypot(bx - ax, by - ay);
            const dx = -(by - ay) / length * thickness / 2, dy = (bx - ax) / length * thickness / 2;
            const points = [[ax - dx, ay - dy], [bx - dx, by - dy], [bx + dx, by + dy], [ax + dx, ay + dy]]
                .map(([x, y]) => pointOnFootprint(part, x / size.width, y / size.height, 0.033));
            face(buffer, points, material, { flip: part.side === "B.Cu" });
        }
    }
}

function packageGeometry(buffer, part, pads, materialFor) {
    const kind = displayPackageKind(part);
    const h = DISPLAY_HEIGHTS[kind];
    const m = (name) => materialFor(MAT[name]);
    const b = (bounds, from, to, material, options) => beveledBox(buffer, part, bounds,
        from + 0.10, to + 0.10, m(material), options);
    if (kind === "module") {
        b([0, 0, 1, 1], 0, 0.45, "module", { bevel: 0.07 });
        b([0.038, 0.033, 0.962, 0.767], 0.45, 0.63, "darkMetal", { bevel: 0.045 });
        b([0.045, 0.04, 0.955, 0.76], 0.6, h - 0.10, "silver", { bevel: 0.2, corner: 0.2 });
        b([0.057, 0.052, 0.943, 0.748], h - 0.15, h, "rim", { bevel: 0.04, corner: 0.12, topMaterial: m("silver") });
        b([0.075, 0.795, 0.925, 0.96], 0.45, 0.52, "module", { bevel: 0.015 });
    } else if (kind === "usb") {
        // Open shell, an inset dark cavity and a tongue make the connector read
        // spatially. These are display abstractions, not a STEP model.
        b([0.02, 0.03, 0.98, 0.97], 0, 0.26, "silver", { bevel: 0.065 });
        b([0.02, 0.03, 0.075, 0.97], 0.26, h, "silver");
        b([0.925, 0.03, 0.98, 0.97], 0.26, h, "silver");
        b([0.075, 0.03, 0.925, 0.11], 0.26, h, "black");
        b([0.075, 0.08, 0.925, 0.97], h - 0.27, h, "rim", { bevel: 0.075, corner: 0.16, topMaterial: m("silver") });
        b([0.14, 0.11, 0.86, 0.89], h * 0.40, h * 0.56, "charcoal", { bevel: 0.09 });
        // Rolled front rim and recessed shell seams are cosmetic housing detail.
        b([0.065, 0.932, 0.935, 0.968], 0.26, 0.41, "rim", { bevel: 0.035 });
        b([0.11, 0.17, 0.13, 0.82], h - 0.004, h + 0.002, "darkMetal", { bevel: 0.001 });
        b([0.87, 0.17, 0.89, 0.82], h - 0.004, h + 0.002, "darkMetal", { bevel: 0.001 });
    } else if (kind === "header") {
        b([0, 0, 1, 1], 0, 1.65, "charcoal");
        for (const pad of pads) {
            const centre = pad.points.reduce((c, p) => ({ x: c.x + p.x / 4, y: c.y + p.y / 4, z: c.z + p.z / 4 }), { x: 0, y: 0, z: 0 });
            const pin = { ...part, points: pad.points.map((p) => ({ x: centre.x + (p.x - centre.x) * 0.31,
                y: centre.y + (p.y - centre.y) * 0.31, z: p.z })), centre };
            beveledBox(buffer, pin, [0, 0, 1, 1], 1.7, h, m("gold"), { bevel: 0.065, corner: 0.04 });
        }
    } else if (kind === "sensor") {
        b([0, 0, 1, 1], 0, h * 0.3, "charcoal");
        b([0.06, 0.06, 0.94, 0.94], h * 0.3, h, "sensor", { bevel: 0.09, corner: 0.09 });
        b([0.18, 0.18, 0.82, 0.82], h - 0.035, h + 0.005, "silver", { bevel: 0.01 });
    } else if (kind === "capacitor" || kind === "resistor" || kind === "led") {
        b([0.03, 0.06, 0.97, 0.94], 0, h * 0.82, kind === "capacitor" ? "ceramic" : kind === "led" ? "white" : "charcoal", { bevel: 0.10 });
        b([0, 0, 0.19, 1], 0, h * 0.9, "solder", { bevel: 0.06 });
        b([0.81, 0, 1, 1], 0, h * 0.9, "solder", { bevel: 0.06 });
        if (kind === "led") b([0.25, 0.22, 0.75, 0.78], h * 0.68, h, "green", { bevel: 0.095, corner: 0.09 });
    } else {
        b([0.08, 0.12, 0.92, 0.88], 0, h, "charcoal", { bevel: 0.13, corner: 0.07 });
    }
    const bottom = part.points.map((p) => ({ ...p, z: p.z + (part.side === "B.Cu" ? -0.1 : 0.1) }));
    const top = part.points.map((p) => ({ ...p, z: p.z + (part.side === "B.Cu" ? -h - 0.13 : h + 0.13) }));
    const faces = [top, bottom, ...bottom.map((p, i) => [p, bottom[(i + 1) % 4], top[(i + 1) % 4], top[i]])];
    return { ...part, displayKind: kind, displayHeight: h, geometryIsDisplayOnly: true,
        bottom, top, faces, labelPoint: pointOnFootprint(part, 0.5, kind === "module" ? 0.4 : 0.5, h + 0.25) };
}

/** No browser globals, mutations, electrical inference or external assets. */
export function buildRenderGeometry(scene, { matcher, selected = null, xray = false } = {}) {
    const substrate = [];
    const objects = [];
    const shadows = [];
    const parts = [];
    for (const s of scene.substrate) {
        const alpha = xray ? 0.18 : 1;
        if (s.face !== "edge") {
            face(substrate, s.points, s.face === "top" ? MAT.board : MAT.reverse, { flip: s.face === "bottom", alpha });
            continue;
        }
        // Display mask/core/mask edge finish, not a claimed copper stack-up.
        // The outline and overall display thickness remain exactly the source's.
        const lerp = (a, b, t) => ({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t });
        for (const [from, to, material] of [[0, 0.055, MAT.board], [0.055, 0.945, MAT.edge], [0.945, 1, MAT.reverse]]) {
            const points = [lerp(s.points[0], s.points[3], from), lerp(s.points[1], s.points[2], from),
                lerp(s.points[1], s.points[2], to), lerp(s.points[0], s.points[3], to)];
            face(substrate, points, material, { flip: true, alpha });
        }
    }
    for (const track of scene.tracks) {
        const points = trackRibbon(track);
        if (!points.length) continue;
        const lit = matcher?.active && matcher.matches(track);
        const material = tint(lit ? MAT.gold : track.layer === "F.Cu" ? MAT.copper : MAT.backCopper, track, matcher, selected);
        face(objects, points, material, { flip: track.layer !== "F.Cu", emission: lit ? 0.35 : 0 });
    }
    for (const pad of scene.pads) {
        const sign = pad.points[0].z < 0 ? -1 : 1;
        const bottom = pad.points.map((p) => ({ ...p, z: p.z + sign * 0.055 }));
        const top = pad.points.map((p) => ({ ...p, z: p.z + sign * 0.13 }));
        prism(objects, bottom, top, tint(MAT.gold, pad, matcher, selected));
        solderFillet(objects, pad, tint(MAT.solder, pad, matcher, selected));
    }
    for (const via of scene.vias) {
        const material = tint(MAT.gold, via, matcher, selected);
        for (const sign of [-1, 1]) {
            const centre = { ...via.centre, z: sign * (scene.thickness / 2 + 0.08) };
            disc(objects, centre, via.diameter / 2, material, { inner: via.drill / 2, sign });
            disc(objects, { ...centre, z: centre.z - sign * 0.01 }, via.drill / 2, MAT.black, { sign, segments: 12 });
        }
    }
    const padsByRef = new Map();
    for (const pad of scene.pads) {
        if (!padsByRef.has(pad.ref)) padsByRef.set(pad.ref, []);
        padsByRef.get(pad.ref).push(pad);
    }
    for (const part of scene.parts) {
        if (Math.abs(part.centre.z) <= scene.thickness / 2 + 0.001) {
            contactShadow(shadows, part, DISPLAY_HEIGHTS[displayPackageKind(part)]);
        }
        referenceInk(objects, part, tint(MAT.white, part, matcher, selected));
        parts.push(packageGeometry(objects, part, padsByRef.get(part.ref) || [],
            (material) => tint(material, part, matcher, selected)));
    }
    return { substrate: new Float32Array(substrate), objects: new Float32Array(objects),
        shadows: new Float32Array(shadows), parts, geometryIsDisplayOnly: true,
        vertexCount: (substrate.length + objects.length + shadows.length) / VERTEX_STRIDE };
}
