// Builds a renderer-agnostic scene graph from the projected board geometry.
//
// Pure: no DOM, no canvas, no engineering decisions. Every coordinate here is
// a copy of a millimetre value the Python projection derived from a compiled
// KiCad artifact. Nothing is inferred, and nothing is invented -- in
// particular component height is not modelled, because Ohmni has no data for
// it. The renderer adds explicitly illustrative package bodies separately.
//
// A second renderer (WebGL, Three.js) would consume this same output. See
// docs/product/VISUALIZATION_ARCHITECTURE.md.

// Directions parts move in when the board is exploded, one per functional
// system. Presentation only: the grouping itself comes from the projection.
export const SYSTEM_DIRECTIONS = Object.freeze({
    power: { x: -1, y: 0.35 },
    compute: { x: 0, y: -1 },
    sense: { x: 1, y: 0.35 },
    io: { x: -0.2, y: 1 },
});

export const SYSTEM_ORDER = Object.freeze(["power", "compute", "sense", "io"]);

const FRONT = "F.Cu";

function rotate(dx, dy, degrees) {
    const radians = (degrees * Math.PI) / 180;
    const c = Math.cos(radians);
    const s = Math.sin(radians);
    return { x: dx * c - dy * s, y: dx * s + dy * c };
}

function quad(cx, cy, z, width, height, rotationDeg) {
    const hw = width / 2;
    const hh = height / 2;
    return [
        [-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh],
    ].map(([dx, dy]) => {
        const r = rotate(dx, dy, rotationDeg);
        return { x: cx + r.x, y: cy + r.y, z };
    });
}

/** Board millimetre space, recentred on the board so rotation feels natural. */
export function centreOf(board) {
    return { x: board.width_mm / 2, y: board.height_mm / 2 };
}

function layerZ(layer, thickness) {
    return layer === FRONT ? thickness / 2 : -thickness / 2;
}

/**
 * Build the scene.
 *
 * @param board  the `board` object from the product projection
 * @param options.explode  0..1, how far systems are separated
 * @param options.showCopper  render tracks and vias
 * @param options.showComponents  render component bodies and pads
 */
export function buildScene(board, options = {}) {
    const { explode = 0, showCopper = true, showComponents = true } = options;
    const t = board.display_thickness_mm;
    const centre = centreOf(board);
    const spread = explode * Math.max(board.width_mm, board.height_mm) * 0.45;
    const lift = explode * t * 6;

    const offsets = {};
    for (const system of SYSTEM_ORDER) {
        const dir = SYSTEM_DIRECTIONS[system] || { x: 0, y: 0 };
        offsets[system] = { x: dir.x * spread, y: dir.y * spread, z: lift };
    }

    const substrate = [];
    const hw = board.width_mm / 2;
    const hh = board.height_mm / 2;
    const top = [{ x: -hw, y: -hh, z: t / 2 }, { x: hw, y: -hh, z: t / 2 },
                 { x: hw, y: hh, z: t / 2 }, { x: -hw, y: hh, z: t / 2 }];
    const bottom = top.map((p) => ({ ...p, z: -t / 2 }));
    substrate.push({ kind: "substrate", face: "top", points: top });
    substrate.push({ kind: "substrate", face: "bottom", points: bottom });
    for (let i = 0; i < 4; i += 1) {
        const j = (i + 1) % 4;
        substrate.push({
            kind: "substrate", face: "edge",
            points: [top[i], top[j], bottom[j], bottom[i]],
        });
    }

    const parts = [];
    const pads = [];
    if (showComponents) {
        for (const component of board.components) {
            const offset = offsets[component.system] || { x: 0, y: 0, z: 0 };
            const cx = component.x_mm - centre.x + offset.x;
            const cy = component.y_mm - centre.y + offset.y;
            const z = layerZ(component.side, t) + (component.side === FRONT ? offset.z : -offset.z);
            parts.push({
                kind: "part",
                ref: component.ref,
                partId: component.part_id,
                package: component.package,
                footprintId: component.footprint_id,
                system: component.system,
                side: component.side,
                nets: component.net_names,
                points: quad(cx, cy, z, component.width_mm, component.height_mm,
                             component.rotation_deg),
                label: component.ref,
                centre: { x: cx, y: cy, z },
            });
            for (const pad of component.pads) {
                const r = rotate(pad.x_mm, pad.y_mm, component.rotation_deg);
                pads.push({
                    kind: "pad",
                    ref: component.ref,
                    number: pad.number,
                    shape: pad.shape,
                    net: pad.net_name,
                    system: component.system,
                    through: pad.kind !== "smd",
                    nonPlated: pad.kind === "np_thru_hole",
                    drill: pad.drill ? { ...pad.drill } : null,
                    points: quad(cx + r.x, cy + r.y, z, pad.width_mm, pad.height_mm,
                                 component.rotation_deg),
                });
            }
        }
    }

    const tracks = [];
    const vias = [];
    if (showCopper) {
        for (const track of board.tracks) {
            const z = layerZ(track.layer, t);
            tracks.push({
                kind: "track",
                net: track.net_name,
                layer: track.layer,
                width: track.width_mm,
                a: { x: track.start_x_mm - centre.x, y: track.start_y_mm - centre.y, z },
                b: { x: track.end_x_mm - centre.x, y: track.end_y_mm - centre.y, z },
            });
        }
        for (const via of board.vias) {
            vias.push({
                kind: "via",
                net: via.net_name,
                diameter: via.diameter_mm,
                drill: via.drill_mm,
                centre: { x: via.x_mm - centre.x, y: via.y_mm - centre.y, z: 0 },
                thickness: t,
            });
        }
    }

    return {
        width: board.width_mm,
        height: board.height_mm,
        thickness: t,
        thicknessIsDisplayOnly: board.thickness_is_display_only,
        substrate, parts, pads, tracks, vias,
        offsets,
    };
}

/** Which primitives a highlight applies to. Membership only; never inference. */
export function highlightMatcher({ refs = [], nets = [], systems = [] } = {}) {
    const refSet = new Set(refs);
    const netSet = new Set(nets);
    const systemSet = new Set(systems);
    const active = refSet.size > 0 || netSet.size > 0 || systemSet.size > 0;
    return {
        active,
        matches(item) {
            if (!active) return true;
            if (item.ref && refSet.has(item.ref)) return true;
            if (item.net && netSet.has(item.net)) return true;
            if (item.system && systemSet.has(item.system)) return true;
            if (Array.isArray(item.nets) && item.nets.some((name) => netSet.has(name))) return true;
            return false;
        },
    };
}

/** Board-space bounds of the scene, used to frame the camera. */
export function sceneBounds(scene) {
    let maxX = scene.width / 2;
    let maxY = scene.height / 2;
    for (const part of scene.parts) {
        for (const point of part.points) {
            maxX = Math.max(maxX, Math.abs(point.x));
            maxY = Math.max(maxY, Math.abs(point.y));
        }
    }
    return { maxX, maxY, radius: Math.hypot(maxX, maxY) };
}
