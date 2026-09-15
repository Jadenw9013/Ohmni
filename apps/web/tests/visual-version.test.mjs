import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { VISUAL_FILE_HASHES, VISUAL_SOURCE_HASH } from '../visual-version.js';
import { createIllustrativeSceneManifest } from '../visual-inventory.js';
import { actualSceneManifest } from '../visual-board-scene.js';

test('shipped visual manifest matches source bytes and separates actual/sample cache identities', () => {
    for (const [file, expected] of Object.entries(VISUAL_FILE_HASHES)) {
        const actual = createHash('sha256').update(readFileSync(new URL(`../${file}`, import.meta.url))).digest('hex');
        assert.equal(actual, expected, `Stale visual manifest: run scripts/prepare_visual_assets.py (${file})`);
    }
    assert.ok(VISUAL_FILE_HASHES['visual-board-scene.js'], 'Source footprint/model mapping participates in visual identity');
    const source = JSON.parse(readFileSync(new URL('../reference-board.json', import.meta.url))).board;
    const actual = actualSceneManifest(source), sample = createIllustrativeSceneManifest();
    assert.ok(actual.id.includes(source.artifact_fingerprint));
    assert.ok(actual.id.endsWith(VISUAL_SOURCE_HASH));
    assert.equal(sample.id, `ohmni:illustrative-reference:v1:${VISUAL_SOURCE_HASH}`);
    assert.notEqual(sample.id, actual.id);
    assert.equal(sample.sourceArtifactFingerprint, undefined);
});
