// Camera, perspective projection, depth sorting and hit testing for the board.
//
// The only file allowed to touch a canvas. It draws exactly the scene graph it
// is handed and computes no geometry of its own beyond the view transform.
// Rotation, zoom, pan, flipping to the back, layer visibility, highlighting and
// the exploded view are all view state -- none of them change what the board is.

import { buildScene, highlightMatcher, sceneBounds } from "./board-model.js";

const DEG = Math.PI / 180;
const MIN_PITCH = -88 * DEG;
const MAX_PITCH = 88 * DEG;

export const PALETTE = Object.freeze({
    substrateTop: "#12332a",
    substrateBottom: "#0e2a22",
    substrateEdge: "#0a1f19",
    outline: "#3f7d67",
    part: "#dfe9e3",
    partStroke: "#7f9a8f",
    pad: "#e8c877",
    padThrough: "#cfd8d3",
    trackFront: "#f1bd55",
    trackBack: "#5fa3d6",
    via: "#e8d7a7",
    label: "#0b1a15",
    dim: "rgba(10, 24, 20, 0.72)",
    selected: "#7ef0c0",
    highlight: "#ffe9a8",
});

export function createCamera(overrides = {}) {
    return {
        yaw: -28 * DEG,
        pitch: 58 * DEG,
        zoom: 1,
        panX: 0,
        panY: 0,
        focal: 900,
        distance: 260,
        ...overrides,
    };
}

/**
 * Project one board-space point to screen space.
 *
 * yaw spins about the board normal; pitch is elevation, so pitch = 90 degrees
 * looks straight down at the front of the board and a negative pitch looks up
 * at the back.
 */
export function project(point, camera, viewport) {
    const cy = Math.cos(camera.yaw);
    const sy = Math.sin(camera.yaw);
    const x1 = point.x * cy - point.y * sy;
    const y1 = point.x * sy + point.y * cy;
    const z1 = point.z;

    const cp = Math.cos(camera.pitch);
    const sp = Math.sin(camera.pitch);
    const up = y1 * sp + z1 * cp;
    const toward = -y1 * cp + z1 * sp;

    const depth = Math.max(camera.distance - toward, 1);
    const scale = (camera.focal / depth) * camera.zoom;
    return {
        x: viewport.cx + x1 * scale + camera.panX,
        y: viewport.cy - up * scale + camera.panY,
        depth,
    };
}

function projectAll(points, camera, viewport) {
    return points.map((point) => project(point, camera, viewport));
}

function meanDepth(projected) {
    let total = 0;
    for (const p of projected) total += p.depth;
    return total / projected.length;
}

function polygonContains(polygon, x, y) {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
        const a = polygon[i];
        const b = polygon[j];
        const straddles = a.y > y !== b.y > y;
        if (straddles && x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x) inside = !inside;
    }
    return inside;
}

/**
 * Order primitives far-to-near, in three bands.
 *
 * Depth alone is not enough on a planar board: the substrate is one large
 * polygon whose mean depth sits in the middle of the board, so a component near
 * the far edge sorts behind it and disappears. Everything on the far face is
 * therefore drawn first, then the substrate, then everything on the near face,
 * with depth ordering applied inside each band.
 */
export function depthSort(primitives) {
    return primitives.slice().sort((a, b) => (a.band - b.band) || (b.depth - a.depth));
}

/** Which side of the board a primitive sits on, relative to the camera. */
export function bandOf(z, pitch) {
    const facingFront = pitch >= 0;
    if (z === 0) return 1;
    const near = facingFront ? z > 0 : z < 0;
    return near ? 2 : 0;
}

export class BoardView {
    constructor(canvas, { onSelect = () => {}, onHover = () => {} } = {}) {
        this.canvas = canvas;
        this.context = canvas.getContext("2d");
        this.camera = createCamera();
        this.scene = null;
        this.board = null;
        this.options = { explode: 0, showCopper: true, showComponents: true, showBack: false };
        this.highlight = { refs: [], nets: [], systems: [] };
        this.matcher = highlightMatcher(this.highlight);
        this.selected = null;
        this.hitRegions = [];
        this.onSelect = onSelect;
        this.onHover = onHover;
        this.dragging = null;
        this.attach();
    }

    attach() {
        const canvas = this.canvas;
        canvas.addEventListener("pointerdown", (event) => {
            canvas.setPointerCapture?.(event.pointerId);
            this.dragging = {
                x: event.clientX, y: event.clientY, moved: false,
                pan: event.shiftKey || event.button === 1,
            };
        });
        canvas.addEventListener("pointermove", (event) => {
            if (!this.dragging) {
                const hit = this.pick(event);
                this.onHover(hit ? hit.ref : null);
                canvas.style.cursor = hit ? "pointer" : "grab";
                return;
            }
            const dx = event.clientX - this.dragging.x;
            const dy = event.clientY - this.dragging.y;
            if (Math.abs(dx) + Math.abs(dy) > 3) this.dragging.moved = true;
            if (this.dragging.pan) {
                this.camera.panX += dx;
                this.camera.panY += dy;
            } else {
                this.camera.yaw += dx * 0.008;
                this.camera.pitch = Math.min(MAX_PITCH,
                    Math.max(MIN_PITCH, this.camera.pitch + dy * 0.008));
            }
            this.dragging.x = event.clientX;
            this.dragging.y = event.clientY;
            this.render();
        });
        const release = (event) => {
            if (this.dragging && !this.dragging.moved) {
                const hit = this.pick(event);
                this.select(hit ? hit.ref : null);
            }
            this.dragging = null;
            canvas.style.cursor = "grab";
        };
        canvas.addEventListener("pointerup", release);
        canvas.addEventListener("pointercancel", () => { this.dragging = null; });
        canvas.addEventListener("wheel", (event) => {
            event.preventDefault();
            const factor = Math.exp(-event.deltaY * 0.0012);
            this.camera.zoom = Math.min(6, Math.max(0.35, this.camera.zoom * factor));
            this.render();
        }, { passive: false });
        canvas.addEventListener("keydown", (event) => {
            const step = event.shiftKey ? 12 : 4;
            const moves = {
                ArrowLeft: () => { this.camera.yaw -= step * DEG; },
                ArrowRight: () => { this.camera.yaw += step * DEG; },
                ArrowUp: () => { this.camera.pitch = Math.min(MAX_PITCH, this.camera.pitch + step * DEG); },
                ArrowDown: () => { this.camera.pitch = Math.max(MIN_PITCH, this.camera.pitch - step * DEG); },
                "+": () => { this.camera.zoom = Math.min(6, this.camera.zoom * 1.15); },
                "-": () => { this.camera.zoom = Math.max(0.35, this.camera.zoom / 1.15); },
            };
            if (moves[event.key]) {
                event.preventDefault();
                moves[event.key]();
                this.render();
            }
        });
    }

    setBoard(board) {
        this.board = board;
        this.rebuild();
        this.frame();
    }

    rebuild() {
        if (!this.board) return;
        this.scene = buildScene(this.board, this.options);
    }

    setOptions(options) {
        Object.assign(this.options, options);
        if ("showBack" in options) {
            this.camera.pitch = options.showBack
                ? -Math.abs(this.camera.pitch || 58 * DEG)
                : Math.abs(this.camera.pitch || 58 * DEG);
        }
        this.rebuild();
        this.render();
    }

    setHighlight(highlight) {
        this.highlight = { refs: [], nets: [], systems: [], ...highlight };
        this.matcher = highlightMatcher(this.highlight);
        this.render();
    }

    select(ref) {
        this.selected = ref;
        this.onSelect(ref);
        this.render();
    }

    /**
     * Fit the board to the viewport.
     *
     * Two passes, because perspective foreshortening means the projected extent
     * of a tilted board is not something the millimetre bounds predict. The
     * first pass sets a plausible focal length; the second measures what the
     * corners actually project to and corrects the zoom.
     */
    frame() {
        if (!this.scene) return;
        const bounds = sceneBounds(this.scene);
        const viewport = this.viewport();
        const span = Math.max(bounds.maxX * 2, bounds.maxY * 2, 1);
        this.camera.zoom = 1;
        this.camera.panX = 0;
        this.camera.panY = 0;
        this.camera.focal = (Math.min(viewport.width, viewport.height) / span) * this.camera.distance;

        const corners = [];
        for (const face of this.scene.substrate) corners.push(...face.points);
        for (const part of this.scene.parts) corners.push(...part.points);
        let minX = Infinity;
        let maxX = -Infinity;
        let minY = Infinity;
        let maxY = -Infinity;
        for (const corner of corners) {
            const p = project(corner, this.camera, viewport);
            minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
            minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
        }
        const width = Math.max(maxX - minX, 1);
        const height = Math.max(maxY - minY, 1);
        const fit = Math.min((viewport.width * 0.92) / width, (viewport.height * 0.92) / height);
        this.camera.zoom = Math.min(6, Math.max(0.35, fit));
        // Recentre on what is actually drawn, not on the origin.
        this.camera.panX = viewport.cx - ((minX + maxX) / 2 - viewport.cx) * (this.camera.zoom - 1) - (minX + maxX) / 2;
        this.camera.panY = viewport.cy - ((minY + maxY) / 2 - viewport.cy) * (this.camera.zoom - 1) - (minY + maxY) / 2;
        this.render();
    }

    viewport() {
        const ratio = globalThis.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        const width = Math.max(rect.width, 1);
        const height = Math.max(rect.height, 1);
        if (this.canvas.width !== Math.round(width * ratio)
            || this.canvas.height !== Math.round(height * ratio)) {
            this.canvas.width = Math.round(width * ratio);
            this.canvas.height = Math.round(height * ratio);
        }
        return { width, height, cx: width / 2, cy: height / 2, ratio };
    }

    pick(event) {
        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        for (const region of this.hitRegions) {
            if (polygonContains(region.polygon, x, y)) return region;
        }
        return null;
    }

    /** One tested implementation of membership, shared with the scene model. */
    isHighlighted(item) {
        return (this.matcher || highlightMatcher(this.highlight)).matches(item);
    }

    isDimming() {
        return (this.matcher || highlightMatcher(this.highlight)).active;
    }

    render() {
        if (!this.scene) return;
        const viewport = this.viewport();
        const ctx = this.context;
        const camera = this.camera;
        ctx.save();
        ctx.scale(viewport.ratio, viewport.ratio);
        ctx.clearRect(0, 0, viewport.width, viewport.height);

        const dimming = this.isDimming();
        const primitives = [];
        this.hitRegions = [];

        for (const face of this.scene.substrate) {
            const points = projectAll(face.points, camera, viewport);
            primitives.push({ type: "substrate", face: face.face, points, band: 1, depth: meanDepth(points) });
        }
        for (const track of this.scene.tracks) {
            const a = project(track.a, camera, viewport);
            const b = project(track.b, camera, viewport);
            primitives.push({
                type: "track", a, b, layer: track.layer, net: track.net,
                width: Math.max(1.1, (track.width * camera.focal * camera.zoom) / a.depth),
                lit: this.isHighlighted(track), band: bandOf(track.a.z, camera.pitch),
                depth: (a.depth + b.depth) / 2,
            });
        }
        for (const via of this.scene.vias) {
            const centre = project(via.centre, camera, viewport);
            primitives.push({
                type: "via", centre, net: via.net,
                radius: Math.max(1, (via.diameter * camera.focal * camera.zoom) / (2 * centre.depth)),
                lit: this.isHighlighted(via), band: 2, depth: centre.depth,
            });
        }
        for (const pad of this.scene.pads) {
            const points = projectAll(pad.points, camera, viewport);
            primitives.push({
                type: "pad", points, through: pad.through, net: pad.net,
                lit: this.isHighlighted(pad), band: bandOf(pad.points[0].z, camera.pitch),
                depth: meanDepth(points) - 0.01,
            });
        }
        for (const part of this.scene.parts) {
            const points = projectAll(part.points, camera, viewport);
            const centre = project(part.centre, camera, viewport);
            primitives.push({
                type: "part", points, centre, ref: part.ref, label: part.label,
                system: part.system, lit: this.isHighlighted(part),
                selected: part.ref === this.selected,
                band: bandOf(part.centre.z, camera.pitch), depth: meanDepth(points) - 0.02,
            });
        }

        for (const primitive of depthSort(primitives)) {
            this.draw(ctx, primitive, dimming);
        }
        ctx.restore();
    }

    draw(ctx, primitive, dimming) {
        const fade = dimming && !primitive.lit ? 0.16 : 1;
        ctx.globalAlpha = 1;
        if (primitive.type === "substrate") {
            ctx.beginPath();
            primitive.points.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
            ctx.closePath();
            ctx.fillStyle = primitive.face === "top" ? PALETTE.substrateTop
                : primitive.face === "bottom" ? PALETTE.substrateBottom : PALETTE.substrateEdge;
            ctx.fill();
            ctx.strokeStyle = PALETTE.outline;
            ctx.lineWidth = 1;
            ctx.stroke();
            return;
        }
        if (primitive.type === "track") {
            ctx.globalAlpha = fade;
            ctx.beginPath();
            ctx.moveTo(primitive.a.x, primitive.a.y);
            ctx.lineTo(primitive.b.x, primitive.b.y);
            ctx.strokeStyle = primitive.lit && dimming ? PALETTE.highlight
                : primitive.layer === "F.Cu" ? PALETTE.trackFront : PALETTE.trackBack;
            ctx.lineWidth = primitive.width;
            ctx.lineCap = "round";
            ctx.stroke();
            ctx.globalAlpha = 1;
            return;
        }
        if (primitive.type === "via") {
            ctx.globalAlpha = fade;
            ctx.beginPath();
            ctx.arc(primitive.centre.x, primitive.centre.y, primitive.radius, 0, Math.PI * 2);
            ctx.fillStyle = PALETTE.via;
            ctx.fill();
            ctx.globalAlpha = 1;
            return;
        }
        if (primitive.type === "pad") {
            ctx.globalAlpha = fade;
            ctx.beginPath();
            primitive.points.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
            ctx.closePath();
            ctx.fillStyle = primitive.through ? PALETTE.padThrough : PALETTE.pad;
            ctx.fill();
            ctx.globalAlpha = 1;
            return;
        }
        ctx.globalAlpha = fade;
        ctx.beginPath();
        primitive.points.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
        ctx.closePath();
        ctx.fillStyle = PALETTE.part;
        ctx.fill();
        ctx.strokeStyle = primitive.selected ? PALETTE.selected : PALETTE.partStroke;
        ctx.lineWidth = primitive.selected ? 2.5 : 1;
        ctx.stroke();
        this.hitRegions.unshift({ ref: primitive.ref, polygon: primitive.points });
        const span = Math.hypot(
            primitive.points[1].x - primitive.points[0].x,
            primitive.points[1].y - primitive.points[0].y,
        );
        if (span > 16 && fade === 1) {
            ctx.fillStyle = PALETTE.label;
            ctx.font = `${Math.min(13, Math.max(8, span / 3.2))}px ui-monospace, monospace`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(primitive.label, primitive.centre.x, primitive.centre.y);
        }
        ctx.globalAlpha = 1;
    }
}
