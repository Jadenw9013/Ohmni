// Pure projection of the saved hackathon demonstration. It formats recorded
// receipts; it never computes an engineering verdict and never lets the damaged
// diagnostic copy borrow a result from the original board.

const DIGEST = /^[0-9a-f]{64}$/;

export class DemoDataError extends Error {}

function require(condition, message) {
    if (!condition) throw new DemoDataError(message);
}

export function validateDemo(demo) {
    require(demo && demo.schema_version === 1 && demo.kind === "saved_hackathon_demonstration", "Unsupported saved demonstration");
    const { good, fault } = demo;
    require(good?.board && fault?.board, "Saved demonstration is missing a board");
    require(DIGEST.test(good.board.artifact_fingerprint) && DIGEST.test(fault.snapshot_sha256), "Saved boards need fingerprints");
    require(fault.board.artifact_fingerprint === fault.snapshot_sha256, "Damaged board geometry is not bound to its snapshot");
    require(fault.source_pcb_sha256 === good.board.artifact_fingerprint, "Damaged copy is not derived from the original board");
    require(fault.snapshot_sha256 !== good.board.artifact_fingerprint, "Damaged copy must differ from the original");
    require(fault.releasable === false && fault.kind === "diagnostic_fault_only", "Damaged copy must be diagnostic-only");
    require(!("checks" in fault), "Damaged copy cannot carry the original board's checks");
    return demo;
}

const status = (value) => typeof value === "string" ? value.replaceAll("_", " ").toUpperCase() : "UNKNOWN";
const count = (value) => Number.isInteger(value) && value >= 0 ? value : null;

/** One row per check, keeping outcome, severity and tier apart. */
export function goodReport(demo) {
    const checks = demo.good.checks || {};
    const erc = checks.erc || {};
    const drc = checks.drc || {};
    const recorded = [status(erc.status), status(drc.status)];
    const outcome = recorded.every((value) => value === "PASS") ? "PASS"
        : recorded.every((value) => value === "PASS" || value === "PASS WITH WARNINGS") ? "PASS_WITH_WARNINGS" : "UNKNOWN";
    return {
        title: "Original board",
        outcome,
        summary: outcome === "UNKNOWN" ? "The saved checks for this board are incomplete; nothing is inferred."
            : "The saved original board passed the KiCad checks recorded for it. Warnings are kept below.",
        artifact: demo.good.board.artifact_fingerprint,
        rows: [
            { check: "Schematic ERC", checker: `KiCad ${erc.kicad_version || "unknown"}`, outcome: status(erc.status),
                detail: `${count(erc.finding_count) ?? "unknown"} findings recorded (see warnings)` },
            { check: "PCB DRC", checker: `KiCad ${drc.kicad_version || "unknown"}`, outcome: status(drc.status),
                detail: `violations: ${count(drc.finding_count) ?? "unknown"}, unconnected: ${count(drc.unconnected_count) ?? "unknown"}` },
            { check: "Copper routing", checker: "Ohmni routing verifier", outcome: checks.routing?.passed === true ? "PASS" : "UNKNOWN",
                detail: `${count(checks.routing?.finding_count) ?? "unknown"} rules` },
            { check: "Manufacturing profile", checker: "Ohmni (synthetic profile)", outcome: checks.manufacturing?.passed === true ? "PASS" : "UNKNOWN",
                detail: "Synthetic example limits; a fabricator must confirm" },
            { check: "Simulation", checker: "none", outcome: status(checks.simulation), detail: "Not part of this board's evidence" },
            { check: "Bench testing", checker: "none", outcome: status(checks.bench), detail: "Nothing has been built or measured" },
        ],
        warnings: demo.capture?.warnings || [],
        limitations: demo.good.limitations || [],
        downloadable: true,
    };
}

export function faultReport(demo) {
    const { fault } = demo;
    const drc = fault.drc || {};
    const findings = [...(drc.unconnected_items || []), ...(drc.findings || [])];
    return {
        title: "Damaged copy (diagnostic only)",
        outcome: status(drc.status),
        summary: `KiCad DRC on this copy recorded missing connections: ${count(drc.unconnected_count) ?? "unknown"}; other findings: ${count(drc.finding_count) ?? "unknown"}.`,
        artifact: fault.snapshot_sha256,
        removed: fault.removed_segment,
        rows: [
            { check: "PCB DRC", checker: `KiCad ${fault.checker?.kicad_version || "unknown"}`, outcome: status(drc.status),
                detail: `violations: ${count(drc.finding_count) ?? "unknown"}, unconnected: ${count(drc.unconnected_count) ?? "unknown"}` },
            ...(fault.not_checked || []).map((name) => ({ check: name.replaceAll("_", " "), checker: "not run on this copy",
                outcome: "NOT_CHECKED", detail: "Not inherited from the original board" })),
        ],
        findings: findings.map((item) => ({
            severity: String(item.severity || "unknown"),
            type: String(item.type || "unknown"),
            description: String(item.description || "").slice(0, 300),
            items: (item.items || []).slice(0, 4).map((part) => String(part.description || "").slice(0, 200)),
        })),
        explanation: fault.explanation || [],
        downloadable: false,
    };
}

/**
 * Selection guard: each request gets a token, and only the latest token may
 * update the page. A slow verification for an earlier choice cannot overwrite
 * the board the presenter has since selected.
 */
export function createSelection() {
    let current = 0;
    return {
        begin() { current += 1; return current; },
        isCurrent(token) { return token === current; },
    };
}

export async function sha256Hex(bytes, subtle = globalThis.crypto?.subtle) {
    if (!subtle) throw new DemoDataError("This browser cannot verify file hashes");
    const digest = await subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}
