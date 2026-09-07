import { BoardView } from "./board-view.js";
import { mountBoardControls } from "./board-controls.js";
import { mountCircuitLessons } from "./circuit-lessons.js";
import { validateLearningSource } from "./learning-model.js";

/** An instant, clearly marked saved-reference lab, separate from an actual run. */
export function initializeCircuitLab(source) {
    const dialog = document.querySelector("#circuit-lab");
    const canvas = document.querySelector("#lab-canvas");
    const launch = document.querySelector("#open-reference-lab");
    if (!dialog?.showModal || !canvas || !launch) return null;
    validateLearningSource(source, { reference: true });
    document.querySelector("#lab-part-count").textContent = `${source.board.components.length} components`;
    document.querySelector("#lab-layer-count").textContent = `${source.board.layer_count} copper layers`;
    document.querySelector("#lab-board-size").textContent = `${source.board.width_mm} × ${source.board.height_mm} mm`;
    let view = null;
    let lessons = null;
    let controls = null;
    const close = () => dialog.close();
    const open = () => {
        dialog.showModal();
        document.body.classList.add("lab-is-open");
        if (!view) {
            view = new BoardView(canvas, {
                onSelect: (ref) => {
                    if (lessons) lessons.select(ref);
                    else view.setHighlight(ref ? { refs: [ref] } : {});
                },
                onHover: (ref) => {
                    const part = source.components.find((item) => item.ref === ref);
                    const label = document.querySelector("#lab-hover-label");
                    label.hidden = !part;
                    label.textContent = part ? `${part.name?.human || ref} · ${ref}` : "";
                },
            });
            if (view.available === false) {
                document.querySelector("#lab-unavailable").hidden = false;
                return;
            }
            view.setBoard(source.board);
            controls = mountBoardControls(document.querySelector("#lab-visual-controls"), view, { explodeControl: document.querySelector("#lab-explode") });
            lessons = mountCircuitLessons(document.querySelector("#lab-lessons"), source, view, { onViewChange: () => controls?.sync() });
            document.querySelector("#lab-explode").addEventListener("input", (event) => {
                view.setOptions({ explode: Number(event.target.value) / 100 });
                view.frame();
            });
            const fit = () => { if (dialog.open && canvas.clientWidth > 0) view.frame(); };
            if (typeof ResizeObserver !== "undefined") new ResizeObserver(fit).observe(canvas);
        }
        view.frame();
        view.render();
        document.querySelector("#close-circuit-lab").focus();
    };
    launch.addEventListener("click", open);
    document.querySelector("#close-circuit-lab").addEventListener("click", close);
    dialog.addEventListener("close", () => {
        document.body.classList.remove("lab-is-open");
        view?.stopAssembly();
        view?.setOptions({ autoRotate: false, animateFlow: false });
        controls?.sync();
        launch.focus();
    });
    dialog.addEventListener("click", (event) => { if (event.target === dialog) close(); });
    launch.disabled = false;
    return { open, close };
}
