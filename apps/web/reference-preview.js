// A saved reference artifact helps a newcomer explore before starting a job.
// It is deliberately separate from the current run and carries no live verdict.
import { BoardView } from "./board-view.js";
import { initializeCircuitLab } from "./circuit-lab.js";
import { validateLearningSource } from "./learning-model.js";

export async function initializeReferencePreview({ fetcher = globalThis.fetch } = {}) {
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
                || "Explore the power, the brain, and the sensor. Select a part on the board to discover its job.");
        };
        const view = new BoardView(canvas, {
            onSelect: (ref) => {
                const part = reference.components.find((item) => item.ref === ref);
                if (!part) { showSystem("all"); return; }
                view.setHighlight({ refs: [ref] });
                text("#reference-part-name", part.name?.human || part.ref);
                text("#reference-part-description", reference.systems.find((system) => system.system === part.system)?.summary || part.name?.detail || "");
            },
        });
        if (view.available === false) throw new Error("renderer unavailable");
        view.setBoard(reference.board);
        view.camera.yaw = -28 * Math.PI / 180;
        view.camera.pitch = 56 * Math.PI / 180;
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
        text("#reference-caption", "Saved PCB · illustrative component bodies and heights");
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
