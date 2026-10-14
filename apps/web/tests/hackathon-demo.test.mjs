import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { createSelection, DemoDataError, faultReport, goodReport, sha256Hex, validateDemo } from "../hackathon-demo-model.js";

const demo = JSON.parse(await readFile(new URL("../../../examples/hackathon-demo/demo.json", import.meta.url), "utf8"));
const copy = () => structuredClone(demo);

test("saved demonstration validates and keeps both boards separate", () => {
    validateDemo(demo);
    assert.notEqual(demo.fault.board.artifact_fingerprint, demo.good.board.artifact_fingerprint);
    assert.equal(demo.fault.board.tracks.length, demo.good.board.tracks.length - 1);
});

test("damaged copy cannot borrow the original board's checks or geometry", () => {
    const borrowed = copy();
    borrowed.fault.checks = borrowed.good.checks;
    assert.throws(() => validateDemo(borrowed), DemoDataError);
    const sameBoard = copy();
    sameBoard.fault.board.artifact_fingerprint = sameBoard.good.board.artifact_fingerprint;
    assert.throws(() => validateDemo(sameBoard), DemoDataError);
    const releasable = copy();
    releasable.fault.releasable = true;
    assert.throws(() => validateDemo(releasable), DemoDataError);
    const lineage = copy();
    lineage.fault.board.routing_plan_fingerprint = lineage.good.board.routing_plan_fingerprint;
    assert.throws(() => validateDemo(lineage), DemoDataError);
    const unrelated = copy();
    unrelated.fault.source_pcb_sha256 = "0".repeat(64);
    assert.throws(() => validateDemo(unrelated), DemoDataError);
});

test("fault report shows its own failure and NOT_CHECKED for every check it did not run", () => {
    const report = faultReport(demo);
    assert.equal(report.outcome, "FAIL");
    assert.equal(report.downloadable, false);
    assert.equal(report.artifact, demo.fault.snapshot_sha256);
    assert.ok(report.findings.some((item) => item.type === "unconnected_items" && item.severity === "error"));
    assert.ok(report.findings.some((item) => item.items.some((part) => part.includes("D1") && part.includes("LED1_A"))));
    const notChecked = report.rows.filter((row) => row.outcome === "NOT_CHECKED").map((row) => row.check);
    assert.equal(notChecked.length, demo.fault.not_checked.length);
    assert.ok(!report.rows.some((row) => row.outcome.startsWith("PASS")));
});

test("original report keeps warnings and never claims an all-green verdict", () => {
    const report = goodReport(demo);
    assert.equal(report.outcome, "PASS_WITH_WARNINGS");
    assert.equal(report.downloadable, true);
    assert.ok(report.warnings.some((line) => line.includes("lib_symbol_issues")));
    assert.ok(report.rows.some((row) => row.check === "Simulation" && row.outcome === "NOT RUN"));
    assert.ok(report.rows.some((row) => row.check === "Bench testing" && row.outcome === "NOT VERIFIED"));
    const missing = copy();
    delete missing.good.checks.drc;
    assert.equal(goodReport(missing).outcome, "UNKNOWN");
});

test("only the latest selection may update the page", () => {
    const selection = createSelection();
    const fault = selection.begin();
    const original = selection.begin();
    assert.equal(selection.isCurrent(fault), false);
    assert.equal(selection.isCurrent(original), true);
});

test("browser hash helper matches SHA-256 and refuses without crypto", async () => {
    const digest = await sha256Hex(new TextEncoder().encode("abc"));
    assert.equal(digest, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    await assert.rejects(() => sha256Hex(new Uint8Array(), null), DemoDataError);
});
