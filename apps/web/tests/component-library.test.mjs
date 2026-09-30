import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { ASSET_REGISTRY, ASSET_VERSION, createAsset } from '../visual-assets.js';

const manifest = JSON.parse(readFileSync(new URL('../component-visuals.json', import.meta.url)));

test('the served library manifest uses existing local procedural families', () => {
    assert.equal(manifest.asset_version, ASSET_VERSION);
    const samples = new Map(manifest.samples.map(sample => [sample.family, sample]));
    assert.equal(samples.size, manifest.samples.length);
    for (const binding of manifest.bindings) {
        const sample = samples.get(binding.family);
        assert.ok(sample);
        assert.ok(ASSET_REGISTRY[binding.family]);
        assert.equal(ASSET_REGISTRY[binding.family].modelAssetId,
            `ohmni-procedural/${binding.family}@${manifest.asset_version}`);
    }
});

test('every library illustration renders without inventing source pads', () => {
    for (const sample of manifest.samples) {
        assert.equal(sample.dimensions.basis, 'ARTISTIC_SAMPLE');
        const group = createAsset(sample.family, {
            width: sample.dimensions.width_nm / 1e6,
            depth: sample.dimensions.depth_nm / 1e6,
            height: sample.dimensions.height_nm / 1e6,
            label: false,
        });
        assert.equal(group.userData.appearanceOnly, true);
        assert.equal(group.userData.dimensionsAreIllustrative, true);
        assert.equal(group.userData.sourceContacts?.length ?? 0, 0);
        group.traverse(object => {
            if (object.geometry) {
                assert.ok(object.geometry.attributes.position.array.every(Number.isFinite));
                object.geometry.dispose();
            }
            object.material?.dispose();
        });
    }
});
