import { createLessons, discoveryOutcome } from "./learning-model.js";
import { escapeHtml as esc } from "./view-model.js";

/** One learning controller shared by the instant reference lab and fresh results. */
export class CircuitLessons {
    constructor(container, source, view, { onViewChange = () => {} } = {}) {
        this.container = container;
        this.source = source;
        this.view = view;
        this.onViewChange = onViewChange;
        this.lessons = createLessons(source);
        this.index = 0;
        this.visited = new Set();
        this.selected = null;
        this.started = false;
        this.handleClick = (event) => {
            const action = event.target.closest?.("[data-lesson-action]");
            if (!action) return;
            const name = action.dataset.lessonAction;
            if (name === "start") { this.started = true; this.go(0); }
            if (name === "step") this.go(Number(action.dataset.index));
            if (name === "next") this.go((this.index + 1) % this.lessons.length);
            if (name === "previous") this.go(this.index - 1);
            if (name === "part") {
                this.view.select(action.dataset.ref);
                this.select(action.dataset.ref);
            }
            if (name === "inspect" && this.selected) this.view.focus(this.selected);
            if (name === "fit") this.view.frame();
            if (name === "net") {
                this.view.setHighlight({ refs: this.selected ? [this.selected] : [], nets: [action.dataset.net] });
                this.view.setOptions({ animateFlow: true, showCopper: true });
                this.onViewChange();
                this.container.querySelectorAll("[data-lesson-action=net]").forEach((button) => {
                    button.setAttribute("aria-pressed", String(button === action));
                });
                const label = this.container.querySelector(".connection-readout");
                if (label) label.textContent = `Highlighting ${action.dataset.net}. Pulses are a visual guide, not electrical simulation.`;
            }
            if (name === "all") {
                this.started = false;
                this.selected = null;
                this.view.select(null);
                this.view.setHighlight({});
                this.view.setOptions({ animateFlow: false });
                this.onViewChange();
                this.render();
            }
            if (name === "all") {
                this.container.querySelector('[data-lesson-action="start"]')?.focus({ preventScroll: true });
            }
            if (["start", "step", "next", "previous"].includes(name)) {
                const heading = this.container.querySelector("h3");
                heading?.setAttribute("tabindex", "-1");
                heading?.focus({ preventScroll: true });
            }
            if (name === "part") {
                this.container.querySelector(`[data-lesson-action="part"][data-ref="${CSS.escape(action.dataset.ref)}"]`)?.focus({ preventScroll: true });
            }
        };
        container.addEventListener("click", this.handleClick);
        this.render();
    }

    go(index) {
        if (index < 0 || index >= this.lessons.length) return;
        this.started = true;
        this.index = index;
        this.selected = null;
        this.view.select(null);
        this.view.setOptions({ autoRotate: false, animateFlow: false });
        this.onViewChange();
        this.view.setHighlight({ refs: this.lessons[index].refs });
        this.render();
        this.view.focus(this.lessons[index].refs);
    }

    /** Hand the highlight back to a manual flow/system control. */
    pause() {
        this.started = false;
        this.selected = null;
        this.render();
    }

    select(ref) {
        if (ref !== null && !this.source.components.some((part) => part.ref === ref)) return;
        this.selected = ref;
        const lesson = this.lessons[this.index];
        const matched = this.started && discoveryOutcome(lesson, ref) === "match";
        if (matched) this.visited.add(this.index);
        // Keep the answer targets visible after a wrong choice. Selection is
        // reported by the renderer; never call view.select here, since that
        // would re-enter its onSelect callback.
        this.view.setHighlight(this.started && !matched ? { refs: lesson.refs }
            : ref ? { refs: [ref] } : {});
        this.render();
    }

    render() {
        const lesson = this.lessons[this.index];
        const card = this.source.components.find((part) => part.ref === this.selected);
        const placed = this.source.board.components.find((part) => part.ref === this.selected);
        const system = this.lessons.find((item) => item.refs.includes(this.selected));
        const found = this.started && card && discoveryOutcome(lesson, card.ref) === "match";
        this.container.innerHTML = `
          <div class="lab-lesson-top"><span class="lab-eyebrow">A circuit, made understandable</span><span class="discovery-count">${this.visited.size}/${this.lessons.length} explored</span></div>
          ${this.started ? `
            <div class="lesson-stops" role="group" aria-label="Circuit tour stops">${this.lessons.map((item, index) => `
              <button type="button" data-lesson-action="step" data-index="${index}" aria-pressed="${index === this.index}" aria-label="${esc(item.title)}">${this.visited.has(index) ? "✓" : String(index + 1).padStart(2, "0")}</button>`).join("")}</div>
            <p class="lesson-position">STOP ${String(this.index + 1).padStart(2, "0")} / ${String(this.lessons.length).padStart(2, "0")}</p>
            <h3>${esc(lesson.title)}</h3><p class="lesson-description">${esc(lesson.description)}</p>
            <div class="discovery-prompt ${found ? "found" : ""}" role="status"><span aria-hidden="true">${found ? "✓" : "↳"}</span><p>${found ? `You found ${esc(card.name?.human || card.ref)}.` : card ? "That belongs to a different system. Try one of the highlighted parts." : "Your turn: select a highlighted part on the board, or choose one below."}</p></div>
            <div class="lesson-parts" role="group" aria-label="Parts in this system">${lesson.parts.map((part) => `<button type="button" data-lesson-action="part" data-ref="${esc(part.ref)}" aria-pressed="${this.selected === part.ref}"><span>${esc(part.name)}</span><code>${esc(part.ref)}</code></button>`).join("")}</div>
            <div class="lesson-nav"><button type="button" data-lesson-action="previous" ${this.index === 0 ? "disabled" : ""} aria-label="Previous tour stop">←</button><button type="button" data-lesson-action="next">${this.index === this.lessons.length - 1 ? "Explore again" : "Next discovery"} <span aria-hidden="true">→</span></button></div>
            <button type="button" data-lesson-action="all" class="lab-free-explore">Return to free exploration</button>
          ` : `<h3>Big ideas.<br>Tiny components.</h3><p class="lesson-description">Every part has a job. Discover how power, the processor, the sensor, and the connections work together.</p><button type="button" data-lesson-action="start" class="lab-start-tour">Take the ${this.lessons.length}-stop tour <span aria-hidden="true">→</span></button><p class="lab-tour-note">Explore at your pace. No electronics knowledge needed.</p>`}
          ${card ? `<section class="lab-part-detail"><div class="lab-part-heading"><span class="lab-eyebrow">Selected component</span><code>${esc(card.ref)}</code></div><h4>${esc(card.name?.human || card.ref)}</h4><button type="button" data-lesson-action="inspect" class="lab-free-explore" aria-label="Inspect ${esc(card.name?.human || card.ref)} on the board">Inspect this part</button><p>${esc(system?.description || "")}</p>${card.name?.detail ? `<details><summary>About this component</summary><p>${esc(card.name.detail)}</p></details>` : ""}
              <div class="net-inspector"><h5>See its connections</h5><p>Each net is a set of electrically connected pins. Pick one to highlight its copper.</p><div>${(placed?.net_names || []).map((net) => `<button type="button" data-lesson-action="net" data-net="${esc(net)}" aria-pressed="false">${esc(net)}</button>`).join("")}</div><p class="connection-readout" role="status"></p></div></section>` : ""}
          <button type="button" data-lesson-action="fit" class="lab-free-explore">Fit whole board</button>
          <details class="lab-visual-limits"><summary>What this view represents</summary><p>${this.source.source ? "A saved reference from an earlier generated design." : "Geometry from this completed design."} Footprints, pads, and copper follow the PCB artifact. Component bodies, heights, colors, and board thickness are illustrative. Light pulses highlight connections; they do not simulate electricity.</p><code>PCB ${esc(this.source.board.artifact_fingerprint.slice(0, 16))}…</code></details>`;
    }

    dispose() { this.container.removeEventListener("click", this.handleClick); }
}

export function mountCircuitLessons(container, source, view, options = {}) {
    if (!container || typeof container.querySelectorAll !== "function" || !view || view.available === false) return null;
    try { return new CircuitLessons(container, source, view, options); }
    catch { container.innerHTML = '<p class="lab-tour-note">The guided tour is unavailable for this projection. You can still explore the board and its recorded parts.</p>'; return null; }
}
