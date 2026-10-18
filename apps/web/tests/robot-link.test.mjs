import assert from "node:assert/strict";
import test from "node:test";

import { boardContext, createRobotLink, ROBOT_COMMANDS, runCommand, validateCommand } from "../robot-link.js";

const experience = () => ({
    components: [
        { ref: "U2", part_id: "AP2112K-3.3", name: { human: "3.3 V voltage regulator", detail: "LDO" }, purpose: "Turns 5 V into 3.3 V.", system: "power", value: "" },
        { ref: "R1", part_id: "R_4k7", display_name: "Pull-up resistor", purpose: "Holds SDA high.", system: "sensor", value: "4.7k" },
    ],
    board: { components: [{ ref: "U2", net_names: ["VBUS", "+3V3", "GND"] }, { ref: "R1", net_names: ["SDA", "+3V3"] }] },
    systems: [{ system: "power", label: "Power" }],
    tour: { narration_source: "deterministic_projection_not_a_language_model", steps: [
        { title: "Power", narration: "USB power becomes 3.3 V.", facts: ["600 mA"], component_refs: ["U2"], net_names: ["+3V3"] },
        { title: "Sensor", narration: "The sensor talks I2C.", facts: [], component_refs: [], net_names: [] },
    ] },
    check_sections: [{ label: "Electrical", groups: [{ label: "Power rails", status: "PASS", rule_count: 3 }] }],
});

const context = () => boardContext(experience(), { jobId: "a".repeat(12), projectId: "p".repeat(16), revisionId: "r".repeat(16) }, "U2");

test("board context carries plain-language parts, the deterministic tour and check statuses only", () => {
    const ctx = context();
    assert.equal(ctx.type, "context");
    assert.equal(ctx.job_id, "a".repeat(12));
    assert.deepEqual(ctx.components[0], { ref: "U2", name: "3.3 V voltage regulator", detail: "LDO", part_id: "AP2112K-3.3", purpose: "Turns 5 V into 3.3 V.", system: "power", value: "", net_names: ["VBUS", "+3V3", "GND"] });
    assert.equal(ctx.components[1].name, "Pull-up resistor", "falls back to display_name");
    assert.equal(ctx.tour.length, 2);
    assert.equal(ctx.tour_source, "deterministic_projection_not_a_language_model");
    assert.deepEqual(ctx.checks, [{ label: "Electrical", groups: [{ label: "Power rails", status: "PASS" }] }]);
    assert.equal(ctx.selected, "U2");
    assert.equal(boardContext(null), null);
    assert.equal(boardContext({ components: [] }), null, "no board, no context");
});

test("only the closed, view-only command set is accepted", () => {
    const ctx = context();
    assert.deepEqual([...ROBOT_COMMANDS], ["focus", "isolate", "trace", "frame", "camera", "tour", "ask"]);
    assert.deepEqual(validateCommand({ type: "command", name: "focus", args: { ref: "U2" } }, ctx), { name: "focus", args: { ref: "U2" } });
    assert.deepEqual(validateCommand({ type: "command", name: "isolate", args: { ref: null } }, ctx).args, { ref: null });
    assert.deepEqual(validateCommand({ type: "command", name: "camera", args: { preset: "back" } }, ctx).args, { preset: "back" });
    assert.deepEqual(validateCommand({ type: "command", name: "tour", args: { index: 1 } }, ctx).args, { index: 1 });
    assert.deepEqual(validateCommand({ type: "command", name: "ask", args: { ref: "R1", question: "  why 4.7k? " } }, ctx).args, { ref: "R1", question: "why 4.7k?" });
    for (const [message, error] of [
        [{ type: "command", name: "run" }, /unknown command/],
        [{ type: "command", name: "apply", args: {} }, /unknown command/],
        [{ type: "command", name: "focus", args: { ref: "U99" } }, /unknown part/],
        [{ type: "command", name: "trace", args: {} }, /unknown part/],
        [{ type: "command", name: "camera", args: { preset: "side" } }, /camera preset/],
        [{ type: "command", name: "tour", args: { index: 2 } }, /tour step/],
        [{ type: "command", name: "tour", args: { index: "0" } }, /tour step/],
        [{ type: "command", name: "ask", args: { ref: "U2", question: "" } }, /question/],
        [{ type: "command", name: "ask", args: { ref: "U2", question: "x".repeat(2001) } }, /question/],
        [{ type: "context" }, /not a command/],
    ]) assert.throws(() => validateCommand(message, ctx), error);
});

test("commands run their action and report results or refusals with the request id", async () => {
    const calls = [];
    const actions = { focus: (args) => { calls.push(["focus", args]); }, trace: () => ({ nets: ["SDA"] }), ask: async () => { throw new Error("tutor offline"); } };
    assert.deepEqual(await runCommand({ type: "command", id: 7, name: "focus", args: { ref: "U2" } }, context(), actions), { type: "result", id: 7, ok: true });
    assert.deepEqual(calls, [["focus", { ref: "U2" }]]);
    assert.deepEqual(await runCommand({ type: "command", id: "t", name: "trace", args: { ref: "R1" } }, context(), actions), { type: "result", id: "t", ok: true, data: { nets: ["SDA"] } });
    assert.deepEqual(await runCommand({ type: "command", id: 8, name: "ask", args: { ref: "U2", question: "why?" } }, context(), actions), { type: "result", id: 8, ok: false, error: "tutor offline" });
    const refused = await runCommand({ type: "command", id: 9, name: "focus", args: { ref: "Q1" } }, context(), actions);
    assert.equal(refused.ok, false);
    assert.equal(calls.length, 1, "a refused command never reaches an action");
});

class FakeSocket {
    static made = [];
    constructor(url) { this.url = url; this.readyState = 0; this.sent = []; FakeSocket.made.push(this); }
    send(data) { this.sent.push(JSON.parse(data)); }
    close() { this.readyState = 3; this.onclose?.(); }
    open() { this.readyState = 1; this.onopen?.(); }
    async receive(payload) { await this.onmessage?.({ data: JSON.stringify(payload) }); }
}

function harness(overrides = {}) {
    FakeSocket.made = [];
    const statuses = [];
    const timers = [];
    const calls = [];
    const link = createRobotLink({
        WebSocketImpl: FakeSocket,
        actions: { focus: async ({ ref }) => { calls.push(ref); link.notifySelected(ref); } },
        getContext: context,
        onStatus: (status) => statuses.push(status),
        setTimer: (fn, ms) => { timers.push({ fn, ms }); return timers.length; },
        clearTimer: (handle) => { timers[handle - 1].cleared = true; },
        ...overrides,
    });
    return { link, statuses, timers, calls };
}

test("enabling connects to loopback and sends the board context once open", () => {
    const { link, statuses } = harness();
    assert.equal(link.status, "off");
    assert.equal(FakeSocket.made.length, 0, "nothing connects until the user opts in");
    link.enable();
    assert.equal(FakeSocket.made[0].url, "ws://127.0.0.1:8770");
    FakeSocket.made[0].open();
    assert.deepEqual(statuses, ["connecting", "connected"]);
    assert.equal(FakeSocket.made[0].sent[0].type, "context");
    assert.equal(FakeSocket.made[0].sent[0].components.length, 2);
});

test("companion commands are answered and robot-driven selection is marked as such", async () => {
    const { link, calls } = harness();
    link.enable();
    const socket = FakeSocket.made[0];
    socket.open();
    await socket.receive({ type: "command", id: 1, name: "focus", args: { ref: "R1" } });
    await socket.receive({ type: "command", id: 2, name: "isolate", args: { ref: "R1" } });
    await socket.receive({ type: "hello" });
    await socket.receive("not json");
    assert.deepEqual(calls, ["R1"]);
    const messages = socket.sent.slice(1);
    assert.deepEqual(messages[0], { type: "selected", ref: "R1", by: "robot" });
    assert.deepEqual(messages[1], { type: "result", id: 1, ok: true });
    assert.equal(messages[2].ok, false, "an action the page does not provide is refused");
    assert.equal(messages.length, 3, "non-commands are ignored");
    link.notifySelected("U2");
    assert.deepEqual(socket.sent.at(-1), { type: "selected", ref: "U2", by: "user" });
});

test("a missing companion fails quietly and retries while enabled; disabling stops everything", () => {
    const { link, statuses, timers } = harness();
    link.enable();
    FakeSocket.made[0].close();
    assert.equal(link.status, "waiting");
    assert.equal(timers.length, 1);
    assert.equal(timers[0].ms, 5000);
    timers[0].fn();
    assert.equal(FakeSocket.made.length, 2, "retried once the timer fired");
    FakeSocket.made[1].close();
    link.disable();
    assert.equal(link.status, "off");
    assert.equal(timers[1].cleared, true);
    assert.deepEqual(statuses, ["connecting", "waiting", "connecting", "waiting", "off"]);
    link.notifySelected("U2");
    assert.equal(FakeSocket.made[1].sent.length, 0, "nothing is sent without an open socket");
});

test("without WebSocket support the link stays off", () => {
    const { link } = harness({ WebSocketImpl: null });
    link.enable();
    assert.equal(link.status, "off");
});
