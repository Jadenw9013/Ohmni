import assert from "node:assert/strict";
import { cpSync, existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { PUBLIC_FILES, PUBLIC_ROOT, SOURCE_ROOT, syncHackathonDemo } from "../../../scripts/sync_hackathon_demo.mjs";

function fixture(t) {
    const root = mkdtempSync(join(tmpdir(), "ohmni-demo-publication-"));
    t.after(() => rmSync(root, { recursive: true, force: true }));
    const sourceRoot = join(root, "source"), publicRoot = join(root, "public");
    cpSync(SOURCE_ROOT, sourceRoot, { recursive: true });
    return { sourceRoot, publicRoot };
}

function editDemo(sourceRoot, edit) {
    const path = join(sourceRoot, "demo.json");
    const data = JSON.parse(readFileSync(path, "utf8"));
    edit(data);
    writeFileSync(path, JSON.stringify(data));
}

test("committed public mirror contains exactly the viewer capture files and canonical bytes", () => {
    assert.equal(syncHackathonDemo({ check: true }).files, 4);
    assert.deepEqual(readdirSync(PUBLIC_ROOT, { recursive: true }).filter(name => !["saved-run", "saved-run/fault", "saved-run\\fault"].includes(name))
        .map(name => name.replaceAll("\\", "/")).sort(), [...PUBLIC_FILES].sort());
    for (const name of PUBLIC_FILES) {
        assert.ok(readFileSync(join(PUBLIC_ROOT, name)).equals(readFileSync(join(SOURCE_ROOT, name))), name);
    }
});

test("every capture requested by the saved viewer is explicitly published", () => {
    const viewer = readFileSync(new URL("../hackathon-demo.js", import.meta.url), "utf8");
    assert.match(viewer, /const BASE = "\/hackathon-demo\/"/);
    const boardFiles = [...viewer.matchAll(/(?:good|fault): "([^"]+\.kicad_pcb)"/g)].map(match => match[1]);
    assert.equal(boardFiles.length, 2);
    const requestedJson = [...viewer.matchAll(/fetchOk\("([^"]+)"/g)].map(match => match[1]);
    const demo = JSON.parse(readFileSync(join(SOURCE_ROOT, "demo.json"), "utf8"));
    assert.deepEqual([...new Set([...boardFiles, ...requestedJson, demo.download.href])].sort(), [...PUBLIC_FILES].sort());
});

test("synchronization preserves bytes and excludes raw evidence reports", t => {
    const paths = fixture(t);
    syncHackathonDemo(paths);
    assert.equal(syncHackathonDemo({ ...paths, check: true }).files, 4);
    for (const name of ["harness-summary.json", "saved-run/erc-report.json", "saved-run/drc-report.json", "saved-run/circuit.json"]) {
        assert.ok(existsSync(join(paths.sourceRoot, name)), name);
        assert.equal(existsSync(join(paths.publicRoot, name)), false, name);
    }
});

for (const name of PUBLIC_FILES.filter(name => name !== "demo.json")) {
    test(`canonical artifact corruption prevents all publication: ${name}`, t => {
        const paths = fixture(t);
        writeFileSync(join(paths.sourceRoot, name), "corrupted capture");
        assert.throws(() => syncHackathonDemo(paths), /recorded SHA-256 does not match/);
        assert.equal(existsSync(paths.publicRoot), false);
    });
}

test("canonical metadata cannot redirect the ZIP or lend good evidence to the fault", t => {
    const paths = fixture(t);
    editDemo(paths.sourceRoot, data => { data.download.href = "../private.zip"; });
    assert.throws(() => syncHackathonDemo(paths), /allowlisted fabrication ZIP/);
    editDemo(paths.sourceRoot, data => { data.download.href = "ohmni-demo-fabrication.zip"; data.fault.releasable = true; });
    assert.throws(() => syncHackathonDemo(paths), /diagnostic-only/);
    assert.equal(existsSync(paths.publicRoot), false);
});

test("check rejects changed, missing and extra public files without modifying them", t => {
    const paths = fixture(t);
    syncHackathonDemo(paths);
    const board = join(paths.publicRoot, "saved-run/golden.kicad_pcb");
    writeFileSync(board, "mirror drift");
    assert.throws(() => syncHackathonDemo({ ...paths, check: true }), /differs from its canonical capture/);
    assert.equal(readFileSync(board, "utf8"), "mirror drift");
    syncHackathonDemo(paths);
    rmSync(board);
    assert.throws(() => syncHackathonDemo({ ...paths, check: true }), /Missing saved demo/);
    assert.equal(existsSync(board), false);
    syncHackathonDemo(paths);
    const extra = join(paths.publicRoot, "saved-run/erc-report.json");
    writeFileSync(extra, "private report sentinel");
    for (const check of [true, false]) {
        assert.throws(() => syncHackathonDemo({ ...paths, check }), /Unexpected public saved demo entry/);
        assert.equal(readFileSync(extra, "utf8"), "private report sentinel");
    }
});

test("a missing canonical file blocks checking and leaves the committed mirror alone", t => {
    const paths = fixture(t);
    syncHackathonDemo(paths);
    const before = readFileSync(join(paths.publicRoot, "demo.json"));
    rmSync(join(paths.sourceRoot, "saved-run/fault/diagnostic-fault.kicad_pcb"));
    assert.throws(() => syncHackathonDemo({ ...paths, check: true }), /Missing saved demo/);
    assert.ok(readFileSync(join(paths.publicRoot, "demo.json")).equals(before));
});
