// Read-only authoring report. Redirect stdout to an evidence file when desired.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { buildLandingBindings } from '../apps/web/landing-pcb-bindings.js';

const referenceBytes = readFileSync(new URL('../apps/web/reference-board.json', import.meta.url));
const reference = JSON.parse(referenceBytes);
const datasets = Object.fromEntries(['chip2t', 'led-passive', 'leaded', 'completion-a', 'completion-c'].map(name =>
    [name, JSON.parse(readFileSync(new URL(`../apps/web/component-library/data/${name}.json`, import.meta.url)))]));
const digest = value => createHash('sha256').update(value).digest('hex');
const report = structuredClone(buildLandingBindings(reference.board, reference.source, datasets));
report.source.referenceFileSha256 = digest(referenceBytes);
for (const entry of report.entries) {
    entry.physicalLandProjection.sha256 = digest(entry.physicalLandProjection.canonicalJson);
}
process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
