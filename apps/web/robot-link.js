// Opt-in link between the workspace and a Stack-chan desk robot companion running on
// this computer (tools/stackchan). The page sends a read-only description of the board;
// the companion may ask for view-only actions (camera, highlight, tour step) and ask
// the existing component tutor. Nothing here can change a design, start a run or
// download anything.

export const ROBOT_LINK_URL = "ws://127.0.0.1:8770";
export const ROBOT_LINK_PREF = "ohmni.robotLink";
export const CAMERA_PRESETS = Object.freeze(["top", "front", "back"]);
export const ROBOT_COMMANDS = Object.freeze(["focus", "isolate", "trace", "frame", "camera", "tour", "ask"]);
const MAX_QUESTION = 2000;
const MAX_QUEUED = 4;          // commands waiting or running; more are refused as busy
const MIN_ASK_INTERVAL_MS = 3000;

// What the companion may know about the board: identities, plain-language component
// cards, the deterministic tour and the recorded check statuses. No artifacts or tokens.
export function boardContext(experience, ids = {}, selected = null) {
    if (!experience?.components || !experience.board) return null;
    const placed = new Map((experience.board.components || []).map((c) => [c.ref, c]));
    return {
        type: "context",
        version: 1,
        job_id: ids.jobId ?? null,
        project_id: ids.projectId ?? null,
        revision_id: ids.revisionId ?? null,
        components: experience.components.map((c) => ({
            ref: c.ref,
            name: c.name?.human || c.display_name || c.ref,
            detail: c.name?.detail || "",
            part_id: c.part_id,
            purpose: c.purpose || "",
            system: c.system || "",
            value: c.value || "",
            net_names: placed.get(c.ref)?.net_names || [],
        })),
        systems: (experience.systems || []).map((s) => ({ system: s.system, label: s.label })),
        tour: (experience.tour?.steps || []).map((step) => ({
            title: step.title,
            narration: step.narration,
            facts: step.facts || [],
            component_refs: step.component_refs || [],
            net_names: step.net_names || [],
        })),
        tour_source: experience.tour?.narration_source || null,
        checks: (experience.check_sections || []).map((section) => ({
            label: section.label,
            groups: (section.groups || []).map((g) => ({ label: g.label, status: g.status })),
        })),
        selected,
    };
}

function refusal(message) {
    const error = new Error(message);
    error.robotRefusal = true;
    return error;
}

// Validate a companion command against the closed set and the rendered board.
export function validateCommand(message, context) {
    if (!message || message.type !== "command") throw refusal("not a command");
    const name = message.name;
    if (!ROBOT_COMMANDS.includes(name)) throw refusal(`unknown command: ${String(name).slice(0, 40)}`);
    const args = message.args && typeof message.args === "object" ? message.args : {};
    const refs = new Set((context?.components || []).map((c) => c.ref));
    const needRef = (ref, optional = false) => {
        if (optional && (ref === null || ref === undefined)) return null;
        if (typeof ref !== "string" || !refs.has(ref)) throw refusal("unknown part on this board");
        return ref;
    };
    switch (name) {
        case "focus":
        case "trace":
            return { name, args: { ref: needRef(args.ref) } };
        case "isolate":
            return { name, args: { ref: needRef(args.ref, true) } };
        case "frame":
            return { name, args: {} };
        case "camera":
            if (!CAMERA_PRESETS.includes(args.preset)) throw refusal("unknown camera preset");
            return { name, args: { preset: args.preset } };
        case "tour": {
            const index = args.index;
            if (!Number.isInteger(index) || index < 0 || index >= (context?.tour?.length || 0)) throw refusal("no such tour step");
            return { name, args: { index } };
        }
        case "ask": {
            const question = typeof args.question === "string" ? args.question.trim() : "";
            if (!question || question.length > MAX_QUESTION) throw refusal("question must be 1-2000 characters");
            return { name, args: { ref: needRef(args.ref), question } };
        }
        default:
            throw refusal("unknown command");
    }
}

export async function runCommand(message, context, actions) {
    const id = message && (typeof message.id === "string" || typeof message.id === "number") ? message.id : null;
    try {
        const { name, args } = validateCommand(message, context);
        const data = await actions[name](args);
        return { type: "result", id, ok: true, ...(data === undefined ? {} : { data }) };
    } catch (error) {
        return { type: "result", id, ok: false, error: String(error?.message || error).slice(0, 300) };
    }
}

// The socket lifecycle. Statuses: off, connecting, connected, waiting (companion not found; retrying).
// Commands run one at a time, in order; the page never trusts the companion with concurrency.
export function createRobotLink({
    url = ROBOT_LINK_URL,
    WebSocketImpl = globalThis.WebSocket,
    actions,
    getContext,
    onStatus = () => {},
    onDisable = () => {},
    retryMs = 5000,
    setTimer = (fn, ms) => globalThis.setTimeout(fn, ms),
    clearTimer = (handle) => globalThis.clearTimeout(handle),
    now = () => Date.now(),
} = {}) {
    let socket = null;
    let enabled = false;
    let timer = null;
    let status = "off";
    let chain = Promise.resolve();
    let queued = 0;
    let lastAsk = -Infinity;
    let lastSelected = null;

    const setStatus = (next) => { if (next !== status) { status = next; onStatus(next); } };
    const send = (payload) => {
        if (socket && socket.readyState === 1) socket.send(JSON.stringify(payload));
    };
    const sendContext = () => { const context = getContext?.(); if (context) send(context); };

    function schedule() {
        if (!enabled || timer !== null) return;
        timer = setTimer(() => { timer = null; connect(); }, retryMs);
    }

    function connect() {
        if (!enabled || socket || typeof WebSocketImpl !== "function") {
            if (typeof WebSocketImpl !== "function") setStatus("off");
            return;
        }
        setStatus("connecting");
        let ws;
        try {
            ws = new WebSocketImpl(url);
        } catch {
            setStatus("waiting");
            schedule();
            return;
        }
        socket = ws;
        ws.onopen = () => { setStatus("connected"); sendContext(); };
        ws.onmessage = (event) => {
            let message;
            try { message = JSON.parse(typeof event.data === "string" ? event.data : ""); } catch { return chain; }
            if (message?.type !== "command") return chain;
            const id = typeof message.id === "string" || typeof message.id === "number" ? message.id : null;
            if (queued >= MAX_QUEUED) {
                send({ type: "result", id, ok: false, error: "busy: too many commands waiting" });
                return chain;
            }
            if (message.name === "ask") {
                if (now() - lastAsk < MIN_ASK_INTERVAL_MS) {
                    send({ type: "result", id, ok: false, error: "busy: wait a moment between questions" });
                    return chain;
                }
                lastAsk = now();
            }
            queued += 1;
            chain = chain.then(async () => {
                try { send(await runCommand(message, getContext?.(), actions)); } finally { queued -= 1; }
            });
            return chain;
        };
        ws.onerror = () => {};
        ws.onclose = () => {
            if (socket === ws) socket = null;
            if (enabled) { setStatus("waiting"); schedule(); } else setStatus("off");
        };
    }

    return {
        get status() { return status; },
        get enabled() { return enabled; },
        enable() { enabled = true; connect(); },
        disable() {
            enabled = false;
            if (timer !== null) { clearTimer(timer); timer = null; }
            const ws = socket;
            socket = null;
            lastSelected = null;
            ws?.close();
            setStatus("off");
            onDisable();
        },
        sendContext,
        // by: "robot" for selections a companion command made, so they are not echoed back as user actions.
        // Identical consecutive notifications (one click renders the selection twice) are sent once.
        notifySelected(ref, by = "user") {
            const key = `${by}:${ref ?? ""}`;
            if (key === lastSelected || !socket || socket.readyState !== 1) return;
            lastSelected = key;
            send({ type: "selected", ref: ref ?? null, by });
        },
    };
}
