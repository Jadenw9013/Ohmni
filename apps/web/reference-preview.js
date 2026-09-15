// A saved reference artifact helps a newcomer explore before starting a job.
// It is deliberately separate from the current run and carries no live verdict.
import { BoardView } from "./board-view.js";
import { initializeCircuitLab } from "./circuit-lab.js";
import { validateLearningSource, recordedCheckRows } from "./learning-model.js";
import { escapeHtml as esc } from "./view-model.js";

export async function initializeReferencePreview({ fetcher = globalThis.fetch, onCustomize = () => {} } = {}) {
    const canvas = document.querySelector("#reference-canvas");
    if (!canvas || typeof canvas.getContext !== "function") return null;
    const text = (id, value) => {
        const node = document.querySelector(id);
        if (node) node.textContent = value;
    };
    try {
        const response = await fetcher("/reference-board.json", { cache: "no-store" });
        if (!response.ok) throw new Error("reference unavailable");
        const reference = await response.json();
        validateLearningSource(reference, { reference: true });
        const controls = document.querySelector("#reference-focus");
        if (controls) {
            controls.replaceChildren();
            for (const system of [{ system: "all", label: "Whole board" }, ...reference.systems.filter((item) => item.component_refs.length)]) {
                const button = document.createElement("button");
                button.type = "button";
                button.dataset.referenceSystem = system.system;
                button.textContent = system.label;
                controls.append(button);
            }
        }
        text("#reference-title", reference.confirmed_brief?.project_name || "Explore this circuit");
        text("#reference-stats", `${reference.board.components.length} parts · ${reference.board.net_names.length} nets · ${reference.board.layer_count} layers · ${reference.board.width_mm} × ${reference.board.height_mm} mm`);
        const evidence = document.querySelector("#reference-evidence");
        if (evidence && reference.checks) {
            evidence.hidden = false;
            evidence.innerHTML = `<summary>Design checks and limits</summary><p>Recorded with this saved design on ${esc(reference.source.captured_on || "an unspecified date")}.</p><dl>${recordedCheckRows(reference).map(({ label, value }) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>${(reference.limitations || []).map((limit) => `<p>${esc(limit)}</p>`).join("")}<p>Inspect the exact <a href="/reference-board.json" target="_blank" rel="noopener">design data and source fingerprints</a>.</p>`;
        }
        const customize = document.querySelector("#customize-reference");
        if (customize && reference.confirmed_brief) {
            customize.hidden = false;
            customize.addEventListener("click", () => onCustomize(structuredClone(reference.confirmed_brief)));
        }
        const buttons = Array.from(document.querySelectorAll("[data-reference-system]"));
        const showSystem = (systemId) => {
            const system = reference.systems.find((item) => item.system === systemId);
            view.selected = null;
            view.setHighlight(system ? { refs: system.component_refs } : {});
            buttons.forEach((button) => {
                const active = button.dataset.referenceSystem === (system?.system || "all");
                button.classList.toggle("on", active);
                button.setAttribute("aria-pressed", String(active));
            });
            text("#reference-part-name", system?.label || "Every part has a purpose.");
            text("#reference-part-description", system?.summary
                || "Select any component to learn its job, then open the lab to follow its pins and connections. Customize this board to generate your own version.");
        };
        const view = new BoardView(canvas, {
            onSelect: (ref) => {
                const part = reference.components.find((item) => item.ref === ref);
                if (!part) { showSystem("all"); return; }
                view.setHighlight({ refs: [ref] });
                text("#reference-part-name", part.name?.human || part.ref);
                text("#reference-part-description", part.purpose || part.name?.detail || "No component explanation was recorded.");
            },
        });
        if (view.available === false) throw new Error("renderer unavailable");
        view.setBoard(reference.board);
        view.camera.yaw = -22 * Math.PI / 180;
        view.camera.pitch = 50 * Math.PI / 180;
        view.frame();
        view.render();
        buttons.forEach((button) => button.addEventListener("click", () => {
            showSystem(button.dataset.referenceSystem);
            const system = reference.systems.find((item) => item.system === button.dataset.referenceSystem);
            if (system) view.focus(system.component_refs);
            else view.setCameraPreset("front");
        }));
        let entrancePlayed = false;
        const resize = () => {
            if (canvas.getBoundingClientRect().width <= 0) return;
            view.frame();
            // One quiet camera reveal introduces the physical object. It stops
            // after settling, and direct interaction immediately interrupts it.
            if (!entrancePlayed) {
                entrancePlayed = true;
                const target = { ...view.camera };
                view.camera.pitch = 32 * Math.PI / 180;
                view.camera.yaw -= 12 * Math.PI / 180;
                view.moveCameraTo(target);
            }
        };
        if (typeof ResizeObserver !== "undefined") new ResizeObserver(resize).observe(canvas);
        else { resize(); globalThis.addEventListener?.("resize", resize); }
        text("#reference-caption", "Generated PCB · saved design · illustrative bodies and heights");
        showSystem("all");
        initializeCircuitLab(reference);
        return view;
    } catch {
        canvas.hidden = true;
        text("#reference-part-name", "The guided project is still available.");
        text("#reference-part-description", "Start the project to run the checks and create a fresh board view.");
        text("#reference-caption", "The saved reference preview could not load. Reload the page to try again.");
        return null;
    }
}
