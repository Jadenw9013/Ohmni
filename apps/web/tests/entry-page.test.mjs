import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("the primary project prompt has an explicit label and review boundary", () => {
    assert.match(html, /<label class="free-text-label" for="free-text-request">/);
    assert.match(html, /<textarea id="free-text-request"[^>]*placeholder="For example:/);
    assert.match(html, /<button type="button" id="start-free-text" class="primary">/);
    assert.match(html, /You will review and edit the plan before Ohmni builds or checks anything/);
});

test("starter projects are named buttons inside an accessible group", () => {
    assert.match(html, /role="group" aria-label="Quick-start projects"/);
    for (const label of ["Measure my room", "Buttons and lights", "Store readings"]) {
        assert.match(html, new RegExp(`<strong>${label}<\\/strong>`));
    }
});

test("the complete workspace uses a persistent project rail and mobile drawer controls", () => {
    assert.match(html, /<aside class="sidebar" id="workspace-sidebar" aria-label="Workspace navigation">/);
    assert.match(html, /id="sidebar-new-project"[^>]*>.*New project/s);
    assert.match(html, /id="project-shelf" class="sidebar-history"/);
    assert.match(html, /id="saved-projects" class="saved-projects"/);
    assert.match(html, /id="sidebar-toggle" aria-controls="workspace-sidebar" aria-expanded="false"/);
    assert.match(html, /id="sidebar-scrim" aria-label="Close navigation" hidden/);
});
