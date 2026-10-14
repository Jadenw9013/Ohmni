import assert from "node:assert/strict";
import test from "node:test";

import { serverErrorKind } from "../client-contract.js";
import { projectRequest } from "../project-contract.js";

const identity = { api_version: 2, server_instance_id: "a".repeat(16), ui_version: "b".repeat(64) };
const json = (status, body, headers = {}) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", ...headers } });

test("a 429 from the brief or demo route becomes the limited message kind", async () => {
    assert.equal(await serverErrorKind(json(429, { error: "ai_request_limited" }, { "retry-after": "60" }), "backend_unavailable"), "ai_request_limited");
    assert.equal(await serverErrorKind(json(503, { error: "ai_budget_unavailable" }), "backend_unavailable"), "ai_budget_unavailable");
});

test("a limited planner request keeps the user's text and makes exactly one call", async () => {
    let calls = 0;
    const fetcher = async () => { calls += 1; return json(429, { error: "ai_request_limited", refusal: { message: "AI requests are paused for a moment to keep demo usage bounded. Your text is still here. Try again later, or continue with guided setup." } }, { "retry-after": "60" }); };
    await assert.rejects(() => projectRequest("/api/project-plans", { fetcher, identity, method: "POST", data: { message: "A USB board", parent_id: null } }),
        (error) => error.message.includes("Your text is still here"));
    assert.equal(calls, 1, "no automatic retry");
});
