/** Presentation controls: never change the projected circuit or verification. */
export function mountBoardControls(container, view, { stage = null, fullscreen = false, explodeControl = null } = {}) {
    if (!container || typeof container.querySelectorAll !== "function" || !view) return null;
    const reduced = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
    container.innerHTML = `<div class="visual-control-group" role="group" aria-label="3D display options">
        <button type="button" data-lab-assembly ${reduced ? 'disabled title="Your device requests reduced motion"' : ""}><span aria-hidden="true">▷</span> <span data-assembly-label>Watch assembly</span></button>
        <button type="button" data-lab-option="autoRotate" aria-pressed="false" ${reduced ? 'disabled title="Your device requests reduced motion"' : ""}><span aria-hidden="true">↻</span> Orbit</button>
        <button type="button" data-lab-option="xray" aria-pressed="false"><span aria-hidden="true">▱</span> X-ray</button>
        <button type="button" data-lab-option="showLabels" aria-pressed="false"><span aria-hidden="true">Aa</span> Labels</button>
        <button type="button" data-lab-option="animateFlow" aria-pressed="false" ${reduced ? 'disabled title="Your device requests reduced motion"' : ""}><span aria-hidden="true">⌁</span> Pulse traces</button>
        <button type="button" data-lab-camera="top"><span aria-hidden="true">⊞</span> Top view</button>
        <button type="button" data-lab-camera="back">Underside</button>
        <button type="button" data-lab-option="showMask" aria-pressed="true">Solder mask</button>
        <button type="button" data-lab-option="showCopper" aria-pressed="true">Copper</button>
        <button type="button" data-lab-option="showComponents" aria-pressed="true">Components</button>
        <button type="button" data-lab-camera="reset"><span aria-hidden="true">⟲</span> Reset view</button>
        ${fullscreen && stage?.requestFullscreen ? '<button type="button" data-lab-fullscreen><span aria-hidden="true">⛶</span> Focus mode</button>' : ""}
      </div><span class="visual-mode-note" role="status">${["webgl", "three"].includes(view.rendererKind) ? "Interactive 3D · drag to explore" : "Compatibility view · learning tools available"}</span>
      <details class="board-keyboard-help"><summary>Keyboard controls</summary><p>Focus the board, then use arrow keys to rotate and + / − to zoom. [ and ] select parts; Enter inspects a part; Home fits the board. Escape clears your selection, then closes the lab.</p></details>`;
    const sync = () => {
        const assembly = container.querySelector("[data-lab-assembly]");
        assembly.disabled = view.reducedMotion === true;
        assembly.title = view.reducedMotion ? "Your device requests reduced motion" : "Illustrative assembly of the circuit's systems";
        container.querySelector("[data-assembly-label]").textContent = view.assemblyAnimation ? "Stop assembly" : "Watch assembly";
        if (explodeControl) explodeControl.value = String(Math.round(view.options.explode * 100));
        container.querySelectorAll("[data-lab-option]").forEach((button) => {
            button.setAttribute("aria-pressed", String(view.options[button.dataset.labOption] === true));
            const key = button.dataset.labOption;
            if (["autoRotate", "animateFlow"].includes(key)) {
                const noNet = key === "animateFlow" && !view.highlight?.nets?.length && !view.options.animateFlow;
                button.disabled = view.reducedMotion === true || noNet;
                button.title = view.reducedMotion ? "Your device requests reduced motion"
                    : noNet ? "Select a component, then a connected net to highlight its traces" : "";
            }
        });
        stage?.querySelectorAll("[data-view]").forEach((button) => {
            if (button.dataset.view === "reset") return;
            const active = button.dataset.view === (view.options.showBack ? "back" : "front");
            button.classList.toggle("on", active);
            button.setAttribute("aria-pressed", String(active));
        });
        stage?.querySelectorAll("[data-toggle]").forEach((button) => {
            const active = view.options[button.dataset.toggle] === true;
            button.classList.toggle("on", active);
            button.setAttribute("aria-pressed", String(active));
        });
        const note = container.querySelector(".visual-mode-note");
        note.textContent = view.assemblyAnimation ? "Assembly reveal · illustrative system separation"
            : view.reducedMotion && (view.options.animateFlow || view.options.autoRotate) ? "Static connection highlight · reduced motion"
            : view.options.animateFlow && !view.options.showCopper ? "Pulses paused · show copper to follow the connection"
            : view.options.animateFlow && (view.options.explode > 0 || !view.highlight?.nets?.length)
            ? "Pulses paused · select a net with the board assembled"
            : view.options.animateFlow ? "Connection highlight · not electrical simulation"
            : view.options.xray ? "Both copper layers revealed"
            : ["webgl", "three"].includes(view.rendererKind) ? "Interactive 3D · drag to explore" : "Compatibility view · learning tools available";
    };
    const click = async (event) => {
        const option = event.target.closest?.("[data-lab-option]");
        if (option) {
            const key = option.dataset.labOption;
            view.interacted();
            view.setOptions({ [key]: !view.options[key] });
            sync();
        }
        const camera = event.target.closest?.("[data-lab-camera]");
        if (camera) {
            view.setCameraPreset(camera.dataset.labCamera);
            sync();
        }
        if (event.target.closest?.("[data-lab-assembly]")) {
            if (view.assemblyAnimation) view.stopAssembly();
            else view.animateAssembly();
            sync();
        }
        if (event.target.closest?.("[data-lab-fullscreen]")) {
            try {
                if (document.fullscreenElement) await document.exitFullscreen();
                else await stage.requestFullscreen();
                view.frame();
            } catch {
                container.querySelector(".visual-mode-note").textContent = "Full screen is unavailable in this browser. All board controls still work here.";
            }
        }
    };
    container.addEventListener("click", click);
    view.canvas?.addEventListener("ohmni:viewchange", sync);
    sync();
    return { sync, dispose() { container.removeEventListener("click", click); view.canvas?.removeEventListener("ohmni:viewchange", sync); } };
}
