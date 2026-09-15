// Interactive, depth-buffered 3D view of authoritative board-model geometry.
// Package shapes/heights, lighting and animation are illustrative display state.
// They never supply electrical, simulation, clearance or fabrication facts.
import { buildScene, highlightMatcher, sceneBounds } from "./board-model.js";
import { buildRenderGeometry, VERTEX_STRIDE } from "./board-renderer-geometry.js";
import { VisualRenderer } from "./visual-renderer.js";
import { actualSceneManifest } from "./visual-board-scene.js";

const DEG = Math.PI / 180;
const MIN_PITCH = -88 * DEG;
const MAX_PITCH = 88 * DEG;
const clamp = (value, lo, hi) => Math.min(hi, Math.max(lo, value));
const now = () => globalThis.performance?.now?.() || Date.now();

export const PALETTE = Object.freeze({ substrateTop: "#08494f", substrateBottom: "#06383e",
    substrateEdge: "#70694f", outline: "#85aca5", part: "#151c25", partStroke: "#90a4b6",
    pad: "#e8be68", padThrough: "#d6c496", trackFront: "#d19745", trackBack: "#59a2be",
    via: "#e8c677", label: "#e7eeff", dim: "#242b43", selected: "#98f3ff", highlight: "#ffdc87" });

export function createCamera(overrides = {}) {
    return { yaw: -28 * DEG, pitch: 53 * DEG, zoom: 1, panX: 0, panY: 0,
        focal: 900, distance: 260, ...overrides };
}

/** Positive elevation sees the front; negative elevation sees the back. */
export function project(point, camera, viewport) {
    const cy = Math.cos(camera.yaw), sy = Math.sin(camera.yaw);
    const x1 = point.x * cy - point.y * sy;
    const y1 = point.x * sy + point.y * cy;
    const cp = Math.cos(camera.pitch), sp = Math.sin(camera.pitch);
    const up = y1 * sp + point.z * cp;
    const toward = -y1 * cp + point.z * sp;
    const depth = Math.max(camera.distance - toward, 1);
    const scale = (camera.focal / depth) * camera.zoom;
    return { x: viewport.cx + x1 * scale + camera.panX,
        y: viewport.cy - up * scale + camera.panY, depth };
}

export function depthSort(primitives) {
    return primitives.slice().sort((a, b) => (a.band - b.band) || (b.depth - a.depth));
}

export function bandOf(z, pitch) {
    if (z === 0) return 1;
    return (pitch >= 0 ? z > 0 : z < 0) ? 2 : 0;
}

function polygonContains(polygon, x, y) {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
        const a = polygon[i], b = polygon[j];
        if ((a.y > y) !== (b.y > y)
            && x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x) inside = !inside;
    }
    return inside;
}

function hull(points) {
    const sorted = points.slice().sort((a, b) => a.x - b.x || a.y - b.y);
    const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
    const half = (arr) => {
        const result = [];
        for (const p of arr) {
            while (result.length >= 2 && cross(result[result.length - 2], result[result.length - 1], p) <= 0) result.pop();
            result.push(p);
        }
        return result.slice(0, -1);
    };
    return [...half(sorted), ...half(sorted.slice().reverse())];
}

function screenBounds(points) {
    const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    return { minX, maxX, minY, maxY, width: Math.max(1, maxX - minX),
        height: Math.max(1, maxY - minY), cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
}

function path(ctx, points) {
    ctx.beginPath();
    points.forEach((p, index) => index ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
    ctx.closePath();
}

export class BoardView {
    constructor(canvas, { onSelect = () => {}, onHover = () => {}, rendererFactory = node => new VisualRenderer(node) } = {}) {
        this.canvas = canvas;
        this.camera = createCamera();
        this.options = { explode: 0, showCopper: true, showComponents: true, showBack: false,
            autoRotate: false, animateFlow: false, xray: false, showLabels: true, showMask: true };
        this.highlight = { refs: [], nets: [], systems: [] };
        this.matcher = highlightMatcher(this.highlight);
        this.selected = null;
        this.hovered = null;
        this.scene = null;
        this.board = null;
        this.geometry = null;
        this.onSelect = onSelect;
        this.onHover = onHover;
        this.hitRegions = [];
        this.dragging = null;
        this.pointers = new Map();
        this.cleanups = [];
        this.lastInteraction = 0;
        this.inViewport = true;
        this.disposed = false;
        this.contextLost = false;
        this.raf = null;
        this.targetCamera = null;
        this.assemblyAnimation = null;
        this.lastFrameTime = null;
        this.time = 0;
        this.motionQuery = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)");
        this.reducedMotion = Boolean(this.motionQuery?.matches);
        try {
            this.rendererFactory = rendererFactory;
            this.renderer = rendererFactory(canvas);
            this.rendererKind = "three";
        } catch {
            try { this.context = canvas.getContext("2d"); } catch { this.context = null; }
            if (!this.context) this.createFallbackCanvas();
            this.rendererKind = "canvas";
        }
        this.available = Boolean(this.renderer || this.context);
        if (!this.available) return;
        canvas.dataset.renderer = this.rendererKind;
        canvas.style.touchAction = "none";
        // Keep crisp labels on a transparent sibling without intercepting the
        // interactive canvas. Its offset follows the canvas inside its parent.
        if (this.renderer && canvas.ownerDocument?.createElement && canvas.parentElement) {
            this.overlay = canvas.ownerDocument.createElement("canvas");
            this.overlay.className = "board-label-overlay";
            this.overlay.setAttribute("aria-hidden", "true");
            Object.assign(this.overlay.style, { position: "absolute", pointerEvents: "none", zIndex: "2" });
            canvas.parentElement.appendChild(this.overlay);
            this.overlayContext = this.overlay.getContext("2d");
        }
        this.attach();
    }

    listen(target, name, callback, options) {
        target?.addEventListener?.(name, callback, options);
        this.cleanups.push(() => target?.removeEventListener?.(name, callback, options));
    }

    createFallbackCanvas() {
        if (!this.canvas.ownerDocument?.createElement || !this.canvas.parentElement) return;
        this.fallbackCanvas = this.canvas.ownerDocument.createElement('canvas');
        this.fallbackCanvas.setAttribute('aria-hidden', 'true');
        Object.assign(this.fallbackCanvas.style, { position: 'absolute', pointerEvents: 'none', zIndex: '1' });
        this.canvas.parentElement.appendChild(this.fallbackCanvas);
        this.context = this.fallbackCanvas.getContext('2d');
        this.canvas.style.opacity = '0';
    }

    interacted() {
        this.lastInteraction = now(); this.targetCamera = null;
        if (this.assemblyAnimation) { this.assemblyAnimation = null; this.notifyViewChange(); }
    }

    notifyViewChange() {
        if (typeof globalThis.CustomEvent !== "function") return;
        this.canvas.dispatchEvent?.(new CustomEvent("ohmni:viewchange", {
            detail: { options: { ...this.options }, selected: this.selected, rendererKind: this.rendererKind },
        }));
    }

    attach() {
        const canvas = this.canvas;
        this.listen(canvas, "pointerdown", (event) => {
            if (event.button !== 0 && event.button !== 1) return;
            this.interacted();
            canvas.setPointerCapture?.(event.pointerId);
            this.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
            if (this.pointers.size === 1) this.dragging = {
                x: event.clientX, y: event.clientY, originX: event.clientX, originY: event.clientY,
                moved: false, pan: event.shiftKey || event.button === 1,
            };
            if (this.pointers.size === 2 && this.dragging) this.dragging.moved = true;
            canvas.style.cursor = "grabbing";
        });
        this.listen(canvas, "pointermove", (event) => {
            if (!this.dragging || !this.pointers.has(event.pointerId)) {
                const hit = this.pick(event);
                const ref = hit?.ref || null;
                if (ref !== this.hovered) {
                    this.hovered = ref;
                    this.onHover(ref);
                    this.render();
                }
                canvas.style.cursor = hit ? "pointer" : "grab";
                return;
            }
            this.interacted();
            const previous = Array.from(this.pointers.values());
            this.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
            const current = Array.from(this.pointers.values());
            if (current.length >= 2) {
                const distance = (points) => Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y);
                const oldDistance = distance(previous);
                if (oldDistance > 1) this.camera.zoom = clamp(this.camera.zoom * distance(current) / oldDistance, 0.35, 6);
                this.camera.panX += (current[0].x + current[1].x - previous[0].x - previous[1].x) / 2;
                this.camera.panY += (current[0].y + current[1].y - previous[0].y - previous[1].y) / 2;
                this.dragging.moved = true;
            } else {
                const dx = event.clientX - this.dragging.x, dy = event.clientY - this.dragging.y;
                if (Math.hypot(event.clientX - this.dragging.originX, event.clientY - this.dragging.originY) > 4) this.dragging.moved = true;
                if (this.dragging.pan) { this.camera.panX += dx; this.camera.panY += dy; }
                else {
                    this.camera.yaw += dx * 0.007;
                    this.camera.pitch = clamp(this.camera.pitch + dy * 0.007, MIN_PITCH, MAX_PITCH);
                }
            }
            this.dragging.x = event.clientX;
            this.dragging.y = event.clientY;
            this.render();
        });
        const release = (event, cancelled = false) => {
            this.pointers.delete(event.pointerId);
            if (!cancelled && this.dragging && !this.dragging.moved) this.select(this.pick(event)?.ref || null);
            if (this.pointers.size === 0) this.dragging = null;
            else if (this.dragging) {
                const remaining = this.pointers.values().next().value;
                this.dragging.x = remaining.x;
                this.dragging.y = remaining.y;
                this.dragging.moved = true;
            }
            canvas.releasePointerCapture?.(event.pointerId);
            canvas.style.cursor = "grab";
            this.ensureAnimation();
        };
        this.listen(canvas, "pointerup", (event) => release(event));
        this.listen(canvas, "pointercancel", (event) => release(event, true));
        this.listen(canvas, "pointerleave", () => {
            if (!this.dragging && this.hovered) { this.hovered = null; this.onHover(null); this.render(); }
        });
        this.listen(canvas, "wheel", (event) => {
            event.preventDefault();
            this.interacted();
            const rect = canvas.getBoundingClientRect();
            const x = event.clientX - rect.left - rect.width / 2;
            const y = event.clientY - rect.top - rect.height / 2;
            const previous = this.camera.zoom;
            const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? rect.height : 1);
            this.camera.zoom = clamp(previous * Math.exp(-delta * 0.0012), 0.35, 6);
            const factor = this.camera.zoom / previous;
            this.camera.panX = x + (this.camera.panX - x) * factor;
            this.camera.panY = y + (this.camera.panY - y) * factor;
            this.render();
        }, { passive: false });
        this.listen(canvas, "keydown", (event) => {
            // Escape clears a selected part first; the next Escape retains the
            // native dialog's close behavior instead of trapping keyboard users.
            if (event.key === "Escape" && !this.selected) return;
            const step = (event.shiftKey ? 12 : 4) * DEG;
            const moves = {
                ArrowLeft: () => { this.camera.yaw -= step; },
                ArrowRight: () => { this.camera.yaw += step; },
                ArrowUp: () => { this.camera.pitch = clamp(this.camera.pitch + step, MIN_PITCH, MAX_PITCH); },
                ArrowDown: () => { this.camera.pitch = clamp(this.camera.pitch - step, MIN_PITCH, MAX_PITCH); },
                "+": () => { this.camera.zoom = Math.min(6, this.camera.zoom * 1.15); },
                "=": () => { this.camera.zoom = Math.min(6, this.camera.zoom * 1.15); },
                "-": () => { this.camera.zoom = Math.max(0.35, this.camera.zoom / 1.15); },
                Home: () => this.frame(), Escape: () => this.select(null),
                "[": () => this.selectNext(-1), "]": () => this.selectNext(1),
                Enter: () => { if (!this.selected) this.selectNext(1); else this.focus(this.selected); },
            };
            if (moves[event.key]) { event.preventDefault(); this.interacted(); moves[event.key](); this.render(); }
        });
        this.listen(globalThis.document, "visibilitychange", () => {
            if (globalThis.document?.hidden) this.stopAnimation();
            else { this.lastFrameTime = null; this.render(); }
        });
        this.listen(this.motionQuery, "change", (event) => {
            this.reducedMotion = event.matches;
            this.targetCamera = null;
            if (this.assemblyAnimation) {
                this.assemblyAnimation = null;
                this.options.explode = 0;
                this.rebuild(); this.frame();
            }
            this.stopAnimation();
            this.render();
            this.notifyViewChange();
        });
        this.listen(canvas, "webglcontextlost", (event) => {
            event.preventDefault(); this.contextLost = true; this.stopAnimation();
            this.lostRenderer = this.renderer; this.renderer = null; this.rendererKind = 'canvas';
            this.createFallbackCanvas(); this.available = Boolean(this.context);
            this.contextLost = false; canvas.dataset.renderer = 'canvas';
            this.rebuild(); this.render(); this.notifyViewChange();
        });
        this.listen(canvas, "webglcontextrestored", () => {
            if (this.disposed) return;
            try {
                this.renderer?.dispose();
                this.lostRenderer?.dispose(); this.lostRenderer = null;
                this.renderer = this.rendererFactory(canvas);
                this.rendererKind = 'three'; canvas.dataset.renderer = 'three';
                this.fallbackCanvas?.remove(); this.fallbackCanvas = null; this.context = null;
                canvas.style.opacity = '1'; this.available = true;
                this.contextLost = false;
                this.rebuild(); this.render();
            } catch { this.available = false; }
        });
        if (typeof globalThis.IntersectionObserver === "function") {
            this.visibilityObserver = new IntersectionObserver((entries) => {
                this.inViewport = entries[0]?.isIntersecting !== false;
                if (!this.inViewport) this.stopAnimation(); else this.render();
            });
            this.visibilityObserver.observe(canvas);
        }
        if (typeof globalThis.ResizeObserver === "function") {
            this.resizeObserver = new ResizeObserver(() => {
                const rect = canvas.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) return;
                const previous = this.lastViewportSize;
                this.lastViewportSize = [rect.width, rect.height];
                if (previous && (Math.abs(previous[0] - rect.width) > 1 || Math.abs(previous[1] - rect.height) > 1)) this.frame();
                else this.render();
            });
            this.resizeObserver.observe(canvas);
        }
    }

    setBoard(board) {
        if (this.disposed) return;
        this.interacted();
        this.board = board; this.selected = null; this.hovered = null;
        this.rebuild(); this.frame();
    }

    rebuild() {
        if (!this.board || this.disposed) return;
        this.scene = buildScene(this.board, this.options);
        this.rebuildGeometry();
    }

    rebuildGeometry() {
        if (!this.scene) return;
        this.geometry = buildRenderGeometry(this.scene, { matcher: this.matcher,
            selected: this.selected, xray: this.options.xray });
        if (!this.contextLost) {
            this.renderer?.setGeometry?.(this.geometry);
            if (this.renderer?.setScene) this.renderer.setScene(this.board.visual_manifest ?? actualSceneManifest(this.board));
            if (this.renderer?.boundingParts) this.geometry.parts = this.renderer.boundingParts(this.scene, this.options);
        }
    }

    setOptions(options) {
        if (this.disposed) return;
        if ("explode" in options) this.assemblyAnimation = null;
        Object.assign(this.options, options);
        if ("explode" in options) this.options.explode = clamp(Number(options.explode) || 0, 0, 1);
        if ("showBack" in options) {
            this.camera.pitch = (options.showBack ? -1 : 1) * Math.abs(this.camera.pitch || 53 * DEG);
            this.targetCamera = null;
        }
        if (["explode", "showCopper", "showComponents"].some((key) => key in options)) this.rebuild();
        else if ("xray" in options) this.rebuildGeometry();
        this.render();
        this.notifyViewChange();
    }

    setHighlight(highlight) {
        if (this.disposed) return;
        this.highlight = { refs: [], nets: [], systems: [], ...highlight };
        this.matcher = highlightMatcher(this.highlight);
        this.rebuildGeometry(); this.render();
        this.notifyViewChange();
    }

    select(ref) {
        if (this.disposed) return;
        this.interacted();
        this.selected = ref;
        this.rebuildGeometry(); this.onSelect(ref); this.render();
        this.notifyViewChange();
    }

    selectNext(direction) {
        const parts = this.geometry?.parts || [];
        if (!parts.length) return;
        const index = parts.findIndex((part) => part.ref === this.selected);
        const next = index < 0 ? (direction < 0 ? parts.length - 1 : 0)
            : (index + direction + parts.length) % parts.length;
        this.select(parts[next].ref);
    }

    /** User-triggered display assembly; the engineering model is unchanged. */
    animateAssembly() {
        if (!this.available || this.disposed || !this.scene) return;
        this.interacted();
        this.setOptions({ autoRotate: false, showBack: false, showComponents: true,
            explode: this.reducedMotion || !globalThis.requestAnimationFrame ? 0 : 1 });
        this.camera = createCamera(); this.frame();
        if (!this.reducedMotion && globalThis.requestAnimationFrame) {
            this.assemblyAnimation = { elapsed: 0, duration: 2400, sinceGeometry: 0 };
            this.render();
        }
        this.notifyViewChange();
    }

    stopAssembly() {
        this.assemblyAnimation = null;
        this.targetCamera = null;
        this.notifyViewChange(); this.render();
    }

    /** Fit/preset transitions share the same interruption and motion policy. */
    moveCameraTo(target) {
        if (this.reducedMotion || !globalThis.requestAnimationFrame) Object.assign(this.camera, target);
        else {
            this.targetCamera = { ...target };
            if ("yaw" in target) {
                const delta = Math.atan2(Math.sin(target.yaw - this.camera.yaw), Math.cos(target.yaw - this.camera.yaw));
                this.targetCamera.yaw = this.camera.yaw + delta;
            }
        }
        this.lastInteraction = now(); this.render();
    }

    fitAnimated() {
        if (!this.scene || !this.available || this.disposed) return;
        const previous = { ...this.camera };
        this.frame();
        const target = { ...this.camera };
        this.camera = previous; this.moveCameraTo(target);
    }

    setCameraPreset(preset) {
        if (!this.scene || !this.available || this.disposed) return;
        this.interacted();
        const previous = { ...this.camera };
        this.setOptions({ autoRotate: false, showBack: preset === "back" });
        this.camera = createCamera(preset === "top" ? { yaw: 0, pitch: 88 * DEG }
            : preset === "back" ? { pitch: -53 * DEG } : {});
        this.frame();
        const target = { ...this.camera };
        this.camera = previous; this.moveCameraTo(target);
    }

    frame() {
        if (!this.scene || this.disposed || !this.available) return;
        if (this.assemblyAnimation) { this.assemblyAnimation = null; this.notifyViewChange(); }
        this.targetCamera = null;
        const bounds = sceneBounds(this.scene);
        const viewport = this.viewport();
        const span = Math.max(bounds.maxX * 2, bounds.maxY * 2, 1);
        this.camera.zoom = 1; this.camera.panX = 0; this.camera.panY = 0;
        this.camera.focal = Math.min(viewport.width, viewport.height) / span * this.camera.distance;
        const points = this.scene.substrate.flatMap((face) => face.points)
            .concat((this.geometry?.parts || []).flatMap((part) => [...part.top, ...part.bottom]));
        const projected = screenBounds(points.map((point) => project(point, this.camera, viewport)));
        this.camera.zoom = clamp(Math.min(viewport.width * 0.84 / projected.width,
            viewport.height * (this.options.frameHeightFraction ?? 0.82) / projected.height), 0.35, 6);
        this.camera.panX = (viewport.cx - projected.cx) * this.camera.zoom;
        this.camera.panY = (viewport.cy - projected.cy) * this.camera.zoom;
        this.render();
    }

    /** Focus changes the camera, never a placement. */
    focus(refOrRefs) {
        if (this.disposed || !this.available) return;
        const refs = new Set(Array.isArray(refOrRefs) ? refOrRefs : [refOrRefs]);
        const parts = (this.geometry?.parts || []).filter((part) => refs.has(part.ref));
        if (!parts.length) return;
        this.focusPoints(parts.flatMap((part) => [...part.top, ...part.bottom]), Math.sign(parts[0].centre.z) || 1);
    }

    /** Focus display geometry without assigning it a component identity. */
    focusPoints(points, side = 1) {
        if (this.disposed || !this.available || !points.length) return;
        this.interacted();
        const pitch = this.options.xray ? this.camera.pitch
            : side * Math.max(Math.abs(this.camera.pitch), 35 * DEG);
        const focusCamera = { ...this.camera, pitch };
        const viewport = this.viewport();
        const bounds = screenBounds(points.map((point) => project(point, focusCamera, viewport)));
        const zoom = clamp(this.camera.zoom * Math.min(viewport.width * 0.6 / bounds.width,
            viewport.height * 0.56 / bounds.height), 0.35, 6);
        const ratio = zoom / this.camera.zoom;
        const target = { pitch, zoom, panX: (this.camera.panX + viewport.cx - bounds.cx) * ratio,
            panY: (this.camera.panY + viewport.cy - bounds.cy) * ratio };
        this.options.showBack = pitch < 0;
        this.moveCameraTo(target); this.notifyViewChange();
    }

    viewport() {
        const ratio = Math.min(globalThis.devicePixelRatio || 1, 2);
        const rect = this.canvas.getBoundingClientRect();
        const width = Math.max(rect.width, 1), height = Math.max(rect.height, 1);
        const pixelWidth = Math.round(width * ratio), pixelHeight = Math.round(height * ratio);
        if (this.canvas.width !== pixelWidth || this.canvas.height !== pixelHeight) {
            this.canvas.width = pixelWidth; this.canvas.height = pixelHeight;
        }
        if (this.overlay) {
            if (this.overlay.width !== pixelWidth || this.overlay.height !== pixelHeight) {
                this.overlay.width = pixelWidth; this.overlay.height = pixelHeight;
            }
            Object.assign(this.overlay.style, { left: `${this.canvas.offsetLeft}px`, top: `${this.canvas.offsetTop}px`,
                width: `${width}px`, height: `${height}px`, display: this.canvas.hidden ? "none" : "block" });
        }
        if (this.fallbackCanvas) {
            this.fallbackCanvas.width = pixelWidth; this.fallbackCanvas.height = pixelHeight;
            Object.assign(this.fallbackCanvas.style, { left: `${this.canvas.offsetLeft}px`, top: `${this.canvas.offsetTop}px`, width: `${width}px`, height: `${height}px` });
        }
        return { width, height, cx: width / 2, cy: height / 2, ratio };
    }

    pick(event) {
        if (this.renderer?.pick) {
            const exact = this.renderer.pick(event);
            if (exact) return exact;
        }
        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left, y = event.clientY - rect.top;
        for (const region of this.hitRegions) if (this.renderer?.owners?.get(region.ref)?.visible !== false && polygonContains(region.polygon, x, y)) return region;
        // Small passives get modest screen-space targets; exact silhouettes win.
        for (const region of this.hitRegions) {
            if (this.renderer?.owners?.get(region.ref)?.visible === false) continue;
            if (Math.hypot(x - region.centre.x, y - region.centre.y) < 7) return region;
        }
        return null;
    }

    isHighlighted(item) { return this.matcher.matches(item); }
    isDimming() { return this.matcher.active; }

    updateHitRegions(viewport) {
        this.hitRegions = (this.geometry?.parts || []).filter((part) =>
            this.options.xray || bandOf(part.centre.z, this.camera.pitch) === 2
        ).map((part) => {
            const points = [...part.top, ...part.bottom].map((point) => project(point, this.camera, viewport));
            return { ref: part.ref, part, polygon: hull(points), centre: project(part.labelPoint, this.camera, viewport),
                depth: Math.min(...points.map((p) => p.depth)), bounds: screenBounds(points) };
        }).sort((a, b) => a.depth - b.depth);
    }

    render() {
        if (!this.scene || !this.available || this.disposed || this.contextLost) return;
        this.canvas.dataset.motion = this.reducedMotion ? 'reduced' : 'standard';
        const viewport = this.viewport();
        this.updateHitRegions(viewport);
        if (this.renderer) this.renderer.render(this.camera, viewport, { ...this.options, highlight: this.highlight });
        else this.renderFallback(viewport);
        this.renderOverlay(viewport);
        this.ensureAnimation();
    }

    renderOverlay(viewport) {
        const ctx = this.overlayContext || this.context;
        if (!ctx) return;
        ctx.save();
        ctx.setTransform(viewport.ratio, 0, 0, viewport.ratio, 0, 0);
        if (this.overlayContext) ctx.clearRect(0, 0, viewport.width, viewport.height);
        this.drawFlow(ctx, viewport);
        const occupied = [];
        const regions = this.hitRegions.slice().sort((a, b) =>
            Number(b.ref === this.selected) - Number(a.ref === this.selected)
            || Number(b.ref === this.hovered) - Number(a.ref === this.hovered)
            || Number(this.matcher.active && this.matcher.matches(b.part)) - Number(this.matcher.active && this.matcher.matches(a.part))
            || b.bounds.width - a.bounds.width);
        for (const region of regions) {
            const selected = region.ref === this.selected, hovered = region.ref === this.hovered;
            const lit = this.matcher.active && this.matcher.matches(region.part);
            if (selected || hovered || lit) {
                ctx.save(); path(ctx, region.polygon);
                ctx.strokeStyle = selected || hovered ? "#9af2ff" : "#ffe2a2";
                ctx.lineWidth = selected ? 2 : 1.1;
                ctx.shadowColor = selected || hovered ? "#30d5f4" : "#ffc36b";
                ctx.shadowBlur = this.rendererKind === 'three' ? 0 : selected ? 17 : 7;
                ctx.globalAlpha = selected || hovered ? 1 : 0.7;
                ctx.stroke(); ctx.restore();
            }
            if (!this.options.showLabels || (this.matcher.active && !lit && !selected && !hovered)) continue;
            const large = region.bounds.width > 92 && region.part.displayKind === "module";
            const label = large ? `${region.ref} · ${region.part.partId}` : region.ref;
            ctx.font = `${selected || hovered ? "600" : "500"} ${large ? 11 : 10}px ui-monospace, SFMono-Regular, Consolas, monospace`;
            const width = ctx.measureText(label).width + 12, height = 20;
            const x = clamp(region.centre.x - width / 2, 5, Math.max(5, viewport.width - width - 5));
            const y = clamp(large ? region.centre.y - 10 : region.bounds.minY - 23, 5, viewport.height - 25);
            const overlap = occupied.some((r) => x < r.x + r.width + 3 && x + width + 3 > r.x && y < r.y + r.height + 3 && y + height + 3 > r.y);
            if (overlap && !selected && !hovered) continue;
            if (!selected && this.hitRegions.some((r) => r.ref !== region.ref
                && r.depth + 0.5 < region.depth && polygonContains(r.polygon, region.centre.x, region.centre.y))) continue;
            occupied.push({ x, y, width, height });
            if (!large) {
                ctx.beginPath(); ctx.moveTo(region.centre.x, region.bounds.minY - 1);
                ctx.lineTo(x + width / 2, y + height);
                ctx.strokeStyle = selected || hovered ? "#96eaff" : "rgba(153, 179, 212, 0.5)";
                ctx.lineWidth = 1; ctx.stroke();
            }
            ctx.beginPath();
            if (ctx.roundRect) ctx.roundRect(x, y, width, height, 5); else ctx.rect(x, y, width, height);
            ctx.fillStyle = selected || hovered ? "rgba(18, 58, 77, 0.94)" : "rgba(11, 19, 38, 0.79)";
            ctx.fill();
            ctx.strokeStyle = selected || hovered ? "rgba(122, 229, 248, 0.8)" : "rgba(172, 191, 221, 0.2)";
            ctx.lineWidth = 1; ctx.stroke();
            ctx.textAlign = "center"; ctx.textBaseline = "middle";
            ctx.fillStyle = selected || hovered ? "#c8faff" : "#d6e3f4";
            ctx.fillText(label, x + width / 2, y + height / 2 + 0.5);
        }
        ctx.restore();
    }

    drawFlow(ctx, viewport) {
        if (!this.options.animateFlow || this.reducedMotion) return;
        const tracks = this.drawableFlowTracks();
        const stride = Math.max(1, Math.ceil(tracks.length / 48));
        for (let i = 0; i < tracks.length; i += stride) {
            const track = tracks[i];
            if (Math.hypot(track.a.x - track.b.x, track.a.y - track.b.y) < 0.8) continue;
            // Back-and-forth light encodes no current direction, signal timing,
            // electron speed or electrical result. Only named copper is used.
            const fraction = 0.5 + 0.42 * Math.sin(this.time * 0.0013 + i * 1.71);
            const p = project({ x: track.a.x + (track.b.x - track.a.x) * fraction,
                y: track.a.y + (track.b.y - track.a.y) * fraction,
                z: track.a.z + (track.a.z < 0 ? -0.15 : 0.15) }, this.camera, viewport);
            if (!this.options.xray && this.hitRegions.some((r) => r.depth < p.depth && polygonContains(r.polygon, p.x, p.y))) continue;
            const radius = clamp(this.camera.focal * this.camera.zoom / p.depth * 0.28, 1.2, 3.1);
            ctx.save(); ctx.beginPath(); ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
            ctx.shadowColor = "#76e8ff"; ctx.shadowBlur = 12; ctx.fillStyle = "#d0fbff";
            ctx.globalAlpha = 0.75 + 0.2 * Math.sin(this.time * 0.003 + i);
            ctx.fill(); ctx.restore();
        }
    }

    renderFallback(viewport) {
        const ctx = this.context;
        ctx.setTransform(viewport.ratio, 0, 0, viewport.ratio, 0, 0);
        ctx.clearRect(0, 0, viewport.width, viewport.height);
        const triangles = [];
        for (const group of ["substrate", "shadows", "objects"]) {
            if (group === "shadows" && this.options.xray) continue;
            const buffer = this.geometry[group];
            for (let i = 0; i < buffer.length; i += VERTEX_STRIDE * 3) {
                const world = [0, 1, 2].map((v) => ({ x: buffer[i + v * VERTEX_STRIDE],
                    y: buffer[i + v * VERTEX_STRIDE + 1], z: buffer[i + v * VERTEX_STRIDE + 2] }));
                const points = world.map((p) => project(p, this.camera, viewport));
                const normal = [buffer[i + 3], buffer[i + 4], buffer[i + 5]];
                const light = 0.56 + 0.58 * Math.max(0, -normal[0] * 0.45 + normal[1] * 0.4 + normal[2] * 0.82) + buffer[i + 10];
                const rgb = [6, 7, 8].map((k) => Math.round(clamp(buffer[i + k] * light * 255, 0, 255)));
                const z = world.reduce((sum, p) => sum + p.z / 3, 0);
                triangles.push({ points, depth: points.reduce((sum, p) => sum + p.depth / 3, 0),
                    band: this.options.xray ? (group === "substrate" ? -1 : 1) : group === "substrate" ? 1 : bandOf(z, this.camera.pitch),
                    color: `rgba(${rgb.join(",")},${buffer[i + 11]})` });
            }
        }
        for (const triangle of depthSort(triangles)) { path(ctx, triangle.points); ctx.fillStyle = triangle.color; ctx.fill(); }
    }

    canAnimate() {
        if (this.disposed || this.contextLost || this.reducedMotion || !this.inViewport
            || globalThis.document?.hidden || !this.scene || !this.available) return false;
        const rect = this.canvas.getBoundingClientRect();
        if (rect.width < 2 || rect.height < 2 || this.canvas.hidden) return false;
        return Boolean(this.assemblyAnimation || this.targetCamera || this.options.autoRotate ||
            (this.options.animateFlow && this.drawableFlowTracks().length));
    }

    drawableFlowTracks() {
        if (!this.options.showCopper || this.options.explode > 0 || !this.highlight.nets.length) return [];
        const nets = new Set(this.highlight.nets);
        return (this.scene?.tracks || []).filter((track) => nets.has(track.net)
            && Math.hypot(track.a.x - track.b.x, track.a.y - track.b.y) >= 0.8
            && (this.options.xray || bandOf(track.a.z, this.camera.pitch) === 2));
    }

    ensureAnimation() {
        if (!this.canAnimate()) { this.stopAnimation(); return; }
        if (this.raf != null || !globalThis.requestAnimationFrame) return;
        this.raf = globalThis.requestAnimationFrame((timestamp) => {
            this.raf = null;
            if (!this.canAnimate()) return;
            const delta = this.lastFrameTime == null ? 16 : Math.min(50, timestamp - this.lastFrameTime);
            if (this.rendererKind === "canvas" && this.lastFrameTime != null && delta < 30) { this.ensureAnimation(); return; }
            this.lastFrameTime = timestamp; this.time += delta;
            if (this.assemblyAnimation) {
                const animation = this.assemblyAnimation;
                animation.elapsed += delta; animation.sinceGeometry += delta;
                const progress = clamp((animation.elapsed / animation.duration - 0.12) / 0.88, 0, 1);
                // 30 Hz mesh updates during this bounded reveal. Idle/orbit
                // frames continue to reuse the static GPU buffers.
                if (animation.sinceGeometry >= 32 || progress === 1) {
                    animation.sinceGeometry = 0;
                    this.options.explode = 1 - progress * progress * (3 - 2 * progress);
                    this.rebuild(); this.notifyViewChange();
                }
                if (progress === 1) {
                    this.assemblyAnimation = null;
                    this.fitAnimated(); this.notifyViewChange();
                }
            } else if (this.targetCamera) {
                const amount = 1 - Math.exp(-delta * 0.012);
                let remaining = 0;
                for (const key of Object.keys(this.targetCamera)) {
                    this.camera[key] += (this.targetCamera[key] - this.camera[key]) * amount;
                    remaining += Math.abs(this.targetCamera[key] - this.camera[key]);
                }
                if (remaining < 0.05) { Object.assign(this.camera, this.targetCamera); this.targetCamera = null; }
            } else if (this.options.autoRotate && !this.dragging && now() - this.lastInteraction > 1800) {
                this.camera.yaw += delta * 0.000075;
            }
            this.render();
        });
    }

    stopAnimation() {
        if (this.raf != null) globalThis.cancelAnimationFrame?.(this.raf);
        this.raf = null; this.lastFrameTime = null;
    }

    dispose() {
        if (this.disposed) return;
        this.disposed = true; this.stopAnimation();
        this.assemblyAnimation = null; this.targetCamera = null;
        this.cleanups.forEach((cleanup) => cleanup()); this.cleanups = [];
        this.visibilityObserver?.disconnect(); this.resizeObserver?.disconnect();
        this.renderer?.dispose(); this.lostRenderer?.dispose(); this.overlay?.remove(); this.fallbackCanvas?.remove(); this.pointers.clear();
        this.hitRegions = []; this.geometry = null; this.scene = null; this.board = null;
    }
}
