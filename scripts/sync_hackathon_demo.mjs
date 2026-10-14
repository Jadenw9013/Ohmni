// Publish only the saved viewer's four capture dependencies, preserving their bytes.
// Run `node scripts/sync_hackathon_demo.mjs --check` to check the committed mirror.
import { createHash } from "node:crypto";
import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { validateDemo } from "../apps/web/hackathon-demo-model.js";

export const SOURCE_ROOT = fileURLToPath(new URL("../examples/hackathon-demo/", import.meta.url));
export const PUBLIC_ROOT = fileURLToPath(new URL("../apps/web/hackathon-demo/", import.meta.url));
export const PUBLIC_FILES = Object.freeze([
    "demo.json",
    "saved-run/golden.kicad_pcb",
    "saved-run/fault/diagnostic-fault.kicad_pcb",
    "ohmni-demo-fabrication.zip",
]);
const PUBLIC_DIRECTORIES = new Set(["saved-run", "saved-run/fault"]);
const sha256 = bytes => createHash("sha256").update(bytes).digest("hex");

function requirePlainPath(root, relative, directory = false) {
    const parts = relative ? relative.split("/") : [];
    const paths = [root, ...parts.map((_, index) => join(root, ...parts.slice(0, index + 1)))];
    for (let index = 0; index < paths.length; index += 1) {
        const path = paths[index];
        if (!existsSync(path)) throw new Error(`Missing saved demo file or directory: ${path}`);
        const entry = lstatSync(path);
        const wantsDirectory = index < paths.length - 1 || directory;
        if (entry.isSymbolicLink() || (wantsDirectory ? !entry.isDirectory() : !entry.isFile())) {
            throw new Error(`Saved demo paths must be ordinary files and directories: ${path}`);
        }
    }
}

function inspectPublicTree(root, relative = "") {
    if (!existsSync(root)) return;
    requirePlainPath(root, relative, true);
    for (const name of readdirSync(join(root, relative))) {
        const child = relative ? `${relative}/${name}` : name;
        const entry = lstatSync(join(root, child));
        if (entry.isDirectory() && PUBLIC_DIRECTORIES.has(child)) inspectPublicTree(root, child);
        else if (!entry.isFile() || !PUBLIC_FILES.includes(child)) {
            throw new Error(`Unexpected public saved demo entry: ${child}`);
        }
    }
}

function validatedSource(sourceRoot) {
    const files = new Map(PUBLIC_FILES.map(name => {
        requirePlainPath(sourceRoot, name);
        return [name, readFileSync(join(sourceRoot, name))];
    }));
    const demo = validateDemo(JSON.parse(files.get("demo.json").toString("utf8")));
    if (demo.download?.href !== "ohmni-demo-fabrication.zip") {
        throw new Error("Saved demo download must name the allowlisted fabrication ZIP");
    }
    for (const [name, expected] of [
        ["saved-run/golden.kicad_pcb", demo.good.board.artifact_fingerprint],
        ["saved-run/fault/diagnostic-fault.kicad_pcb", demo.fault.snapshot_sha256],
        ["ohmni-demo-fabrication.zip", demo.download.sha256],
    ]) {
        if (!/^[0-9a-f]{64}$/.test(expected) || sha256(files.get(name)) !== expected) {
            throw new Error(`Saved demo recorded SHA-256 does not match: ${name}`);
        }
    }
    return files;
}

export function syncHackathonDemo({ sourceRoot = SOURCE_ROOT, publicRoot = PUBLIC_ROOT, check = false } = {}) {
    sourceRoot = resolve(sourceRoot);
    publicRoot = resolve(publicRoot);
    // Validate every source before creating or changing a public file. Raw checker
    // reports and other canonical evidence are deliberately outside this allowlist.
    const files = validatedSource(sourceRoot);
    inspectPublicTree(publicRoot);
    if (check) {
        for (const [name, bytes] of files) {
            requirePlainPath(publicRoot, name);
            if (!readFileSync(join(publicRoot, name)).equals(bytes)) {
                throw new Error(`Public saved demo differs from its canonical capture: ${name}`);
            }
        }
    } else {
        for (const [name, bytes] of files) {
            const destination = join(publicRoot, name);
            mkdirSync(dirname(destination), { recursive: true });
            writeFileSync(destination, bytes);
        }
    }
    return { files: files.size, bytes: [...files.values()].reduce((sum, bytes) => sum + bytes.length, 0) };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    try {
        const args = process.argv.slice(2);
        if (args.length > 1 || (args.length === 1 && args[0] !== "--check")) {
            throw new Error("Usage: node scripts/sync_hackathon_demo.mjs [--check]");
        }
        const check = args.includes("--check");
        const result = syncHackathonDemo({ check });
        console.log(`Saved demo public mirror ${check ? "is current" : "synchronized"} (${result.files} files, ${result.bytes} bytes).`);
    } catch (error) {
        console.error(error.message);
        process.exitCode = 1;
    }
}
