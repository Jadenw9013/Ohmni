import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from '../vendor/three.module.js';
import { createMaterials } from '../visual-assets.js';
import { createRedesignModelResolver } from '../landing-pcb-redesign/models.js';

function candidate(partId, ref, pads = []) {
    const part = { ref, part_id: partId, footprint_id: `source:${ref}`, pads };
    const source = { board: { components: [part] }, components: [{ ref }] };
    const entry = { id: ref, sourceFootprintId: part.footprint_id, options: { pads } };
    return { source, entry };
}

test('new model resolver rejects an unmatched physical identity', () => {
    const { source, entry } = candidate('XAL4020-222MEB', 'L1');
    assert.throws(() => createRedesignModelResolver(source)(
        { ...entry, sourceFootprintId: 'unrelated-footprint' }, createMaterials()), /mismatch/);
});

test('inductor appearance stays in its sourced envelope and does not rewrite copper', () => {
    const { source, entry } = candidate('XAL4020-222MEB', 'L1', [
        { number: '1', x_mm: -1.185, y_mm: 0, width_mm: .98, height_mm: 3.4 },
        { number: '2', x_mm: 1.185, y_mm: 0, width_mm: .98, height_mm: 3.4 },
    ]);
    const before = JSON.stringify(source);
    const group = createRedesignModelResolver(source)(entry, createMaterials());
    const bounds = new THREE.Box3().setFromObject(group);
    assert.ok(bounds.max.x <= 2.00001 && bounds.min.x >= -2.00001);
    assert.ok(bounds.max.y <= 2.00001 && bounds.min.y >= -2.00001);
    assert.ok(bounds.max.z <= 2.10001 && bounds.min.z >= -.00001);
    assert.equal(JSON.stringify(source), before);
    assert.equal(group.userData.physicalFit, 'NOT_ESTABLISHED');
});

test('translator preserves eight leads and its pin-one source corner', () => {
    const pads = Array.from({ length: 8 }, (_, i) => ({ number: String(i + 1),
        x_mm: i < 4 ? -1.35 : 1.35,
        y_mm: i < 4 ? -.75 + i * .5 : .75 - (i - 4) * .5,
        width_mm: .85, height_mm: .3, kind: 'smd' }));
    const { source, entry } = candidate('PCA9306DCUT', 'U4', pads);
    const group = createRedesignModelResolver(source)(entry, createMaterials());
    const leads = group.children.find(child => child.isInstancedMesh);
    assert.equal(leads.count, 8);
    const marker = group.getObjectByName('pin 1 corner indication');
    assert.equal(Math.sign(marker.position.x), Math.sign(pads[0].x_mm));
    assert.equal(Math.sign(marker.position.y), Math.sign(pads[0].y_mm));
    for (let i = 0; i < pads.length; i++) {
        const matrix = new THREE.Matrix4(); leads.getMatrixAt(i, matrix);
        assert.equal(matrix.elements[13], pads[i].y_mm);
    }
});
