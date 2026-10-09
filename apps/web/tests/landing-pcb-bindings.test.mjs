import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { buildLandingBindings, LANDING_REFERENCE_FINGERPRINT, transformLandingPoint,
    checkLandingContactOverlap, checkLandingThroughHoleFit } from '../landing-pcb-bindings.js';

const read = path => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
const reference = read('../reference-board.json');
const datasets = Object.fromEntries(['chip2t', 'led-passive', 'leaded', 'completion-a', 'completion-c']
    .map(name => [name, read(`../component-library/data/${name}.json`)]));
const report = buildLandingBindings(reference.board, reference.source, datasets);
const entry = ref => report.entries.find(entry => entry.ref === ref);
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} differs from ${b}`);
const expectedRefs = ['C1','C2','C3','C4','C5','C6','C7','D1','D2','D3','D4','J1','J2',
    'R1','R2','R3','R4','R5','R10','R11','R12','R13','R20','R21','SW1','SW2','U1','U2','U3'];

test('binding inventory preserves all 29 identities and every source land without mutating input', () => {
    const before = JSON.stringify(reference), candidateBefore = JSON.stringify(datasets);
    const second = buildLandingBindings(reference.board, reference.source, datasets);
    assert.deepEqual(second, report);
    assert.deepEqual(report.entries.map(entry => entry.ref).sort(), [...expectedRefs].sort());
    assert.equal(report.source.artifactFingerprint, LANDING_REFERENCE_FINGERPRINT);
    assert.equal(report.source.footprintGeometryFingerprint, reference.source.footprint_geometry_fingerprint);
    assert.equal(report.source.footprintGeometryScope, 'local_registry');
    assert.equal(report.source.sourceFootprintFileSha256, null);
    for (const component of reference.board.components) {
        const binding = entry(component.ref);
        assert.equal(binding.partId, component.part_id);
        assert.equal(binding.footprintId, component.footprint_id);
        assert.deepEqual(binding.physicalLands.map(land => land.sourceGeometry), component.pads);
        assert.equal(binding.physicalLands.length, component.pads.length);
        assert.equal(binding.approximation.status, 'PACKAGE_APPROXIMATION');
        assert.equal(binding.approximation.physicalFitEstablished, false);
        assert.equal(binding.fit.status, 'NOT_ESTABLISHED');
        assert.equal(binding.libraryCandidate?.eligible ?? false, false);
        assert.equal(binding.physicalLandProjection.sha256, null);
    }
    assert.equal(JSON.stringify(reference), before);
    assert.equal(JSON.stringify(datasets), candidateBefore);
    assert.ok(Object.isFrozen(report) && Object.isFrozen(entry('R1').physicalLands[0].sourceGeometry));
});

test('board-only call does not invent the external registry identity or candidate source revision', () => {
    const bare = buildLandingBindings(reference.board);
    assert.equal(bare.source.footprintGeometryFingerprint, null);
    assert.equal(bare.entries.find(entry => entry.ref === 'R1').libraryCandidate.sourceSpecSha256, null);
    assert.equal(bare.entries.flatMap(entry => entry.fit.observations).length, 0);
    assert.throws(() => buildLandingBindings(reference.board, { artifact_fingerprint: '0'.repeat(64) }), /disagree/);
    assert.throws(() => buildLandingBindings({ ...reference.board, artifact_fingerprint: '0'.repeat(64) }), /Frozen/);
});

test('approved LED polarity is preserved without silently rewriting the older saved board', () => {
    const approved = read('../../../src/ohmni/behavior/data/bindings/GENERIC_LED_GREEN.json')
        .package_pin_orders.find(order => order.package_name === '0805');
    for (const ref of ['D1','D2','D3','D4']) {
        const binding = entry(ref), mapping = binding.terminalMapping;
        assert.deepEqual(mapping.approvedCatalogToPackageTerminal, { '1':'2', '2':'1' });
        assert.deepEqual(mapping.approvedCatalogToPackageTerminal, approved.catalog_to_package_terminal);
        assert.deepEqual(mapping.approvedCatalogToCurrentFootprintPad, approved.catalog_to_footprint_pad);
        assert.equal(mapping.status, 'BLOCKED_SOURCE_DISCREPANCY');
        assert.equal(mapping.packageTerminalToSavedLand, null);
        assert.match(binding.physicalLands[0].sourceGeometry.net_name, /^LED[1-4]_A$/);
        assert.equal(binding.physicalLands[0].electricalPadNumber, '1');
        assert.equal(binding.physicalLands[1].sourceGeometry.net_name, 'GND');
        assert.equal(binding.libraryCandidate.candidateToFootprint, null);
    }
});

test('switch repeated electrical numbers remain four distinct physical lands', () => {
    for (const ref of ['SW1','SW2']) {
        const binding = entry(ref);
        assert.deepEqual(binding.physicalLands.map(land => land.id), [[ref,0,'1'],[ref,1,'1'],[ref,2,'2'],[ref,3,'2']]);
        assert.deepEqual(binding.physicalLands.map(land => land.footprintLocalCenterMm),
            [[-3.25,-2.25,0],[3.25,-2.25,0],[-3.25,2.25,0],[3.25,2.25,0]]);
        assert.equal(binding.terminalMapping.sourceElectricalGroups['1'].length, 2);
        assert.equal(binding.terminalMapping.sourceElectricalGroups['2'].length, 2);
        assert.equal(binding.terminalMapping.packageTerminalToSavedLand, null);
    }
});

test('USB mechanical holes and variant uncertainty survive the inventory', () => {
    const usb = entry('J1'), mechanical = usb.physicalLands.filter(land => land.sourceGeometry.kind === 'np_thru_hole');
    assert.equal(mechanical.length, 2);
    assert.equal(new Set(mechanical.map(land => JSON.stringify(land.id))).size, 2);
    assert.equal(Object.hasOwn(usb.terminalMapping.sourceElectricalGroups, ''), false);
    assert.equal(usb.libraryCandidate.status, 'REJECTED_VARIANT');
    assert.match(usb.libraryCandidate.reason, /Amphenol.*HRO/);
    assert.equal(entry('U1').libraryCandidate, null);
    assert.equal(entry('U3').libraryCandidate, null);
});

test('independent quarter-turn expectations expose mirror and double-mirror mistakes', () => {
    const expected = [[11,22,3],[8,21,3],[9,18,3],[12,19,3]];
    const mirrored = [[9,22,-3],[8,19,-3],[11,18,-3],[12,21,-3]];
    [0,90,180,270].forEach((rotationDeg, index) => {
        transformLandingPoint([1,2,3], { translationMm:[10,20,0],rotationDeg }).forEach((value, axis) => near(value, expected[index][axis]));
        transformLandingPoint([1,2,3], { translationMm:[10,20,0],rotationDeg,mirrorX:true,mirrorZ:true })
            .forEach((value, axis) => near(value, mirrored[index][axis]));
    });
});

test('bottom source lands rotate once and retain source physical coordinates', () => {
    const board = structuredClone(reference.board), resistor = board.components.find(component => component.ref === 'R1');
    resistor.side = 'B.Cu'; resistor.rotation_deg = 90;
    const bottom = buildLandingBindings(board).entries.find(entry => entry.ref === 'R1');
    near(bottom.physicalLands[0].boardCenterMm[0], -5);
    near(bottom.physicalLands[0].boardCenterMm[1], 14.5875);
    assert.equal(bottom.placement.sourcePadMirror, false);
});

test('0805 scoped overlap uses contact surfaces, not falsely coincident centers', () => {
    const resistor = entry('R1'), capacitor = entry('C1');
    near(resistor.physicalLands[0].candidateModelContact.centerMm[0], -0.825);
    near(resistor.physicalLands[0].footprintLocalCenterMm[0], -0.9125);
    near(resistor.fit.observations[0].centerDistanceMm, 0.0875);
    near(resistor.fit.observations[0].overlapLowerBoundMm2, Math.PI * 0.175 ** 2);
    near(capacitor.physicalLands[0].candidateModelContact.centerMm[0], -0.75);
    for (const binding of [resistor,capacitor]) {
        assert.ok(binding.fit.observations.every(item => item.status === 'SUPPORTED_OVERLAP_LOWER_BOUND'));
        assert.equal(binding.fit.status, 'NOT_ESTABLISHED');
        assert.equal(binding.libraryCandidate.eligible, false);
    }
});

test('contact observation rejects disconnected and floating contacts without guessing a radius', () => {
    const pad = {x_mm:0,y_mm:0,width_mm:1,height_mm:1.4,shape:'roundrect',kind:'smd'};
    const contact = {centerMm:[0,0,0],widthMm:0.35,heightMm:1.25};
    for (const rotationDeg of [0,90,180,270]) {
        assert.equal(checkLandingContactOverlap(contact,pad,{rotationDeg,mirrorX:true}).status, 'SUPPORTED_OVERLAP_LOWER_BOUND');
    }
    assert.equal(checkLandingContactOverlap(contact,pad,{translationMm:[5,0,0]}).status,'FAIL_DISJOINT');
    assert.equal(checkLandingContactOverlap(contact,pad,{translationMm:[0,0,0.05]}).status,'FAIL_SEATING_PLANE');
    assert.equal(checkLandingContactOverlap(contact,pad,{translationMm:[0.6,0,0]}).status,'NOT_ESTABLISHED');
});

test('six-pin candidate requires centered-model to pin-one-anchor transform and scoped hole clearance', () => {
    const header = entry('J2');
    assert.deepEqual(header.libraryCandidate.options,{N:6});
    assert.equal(header.libraryCandidate.candidateToFootprint.rotationDeg,180);
    near(header.libraryCandidate.candidateToFootprint.translationMm[1],6.35);
    assert.equal(header.fit.observations.length,6);
    header.fit.observations.forEach((observation,index) => {
        near(observation.contactCenterMm[0],0); near(observation.contactCenterMm[1],index*2.54);
        near(observation.radialClearanceMm,0.5-0.64/Math.sqrt(2));
        assert.equal(observation.status,'SUPPORTED_HOLE_XY_CONTAINMENT');
        assert.equal(observation.tailDepthEstablished,false);
    });
    const first = header.physicalLands[0];
    assert.equal(checkLandingThroughHoleFit(first.candidateModelContact,first.sourceGeometry).status,'FAIL_HOLE_XY_CONTAINMENT');
    const tooWide = {...first.candidateModelContact,centerMm:[0,0,0],squareTailWidthMm:1};
    assert.equal(checkLandingThroughHoleFit(tooWide,first.sourceGeometry).status,'FAIL_HOLE_XY_CONTAINMENT');
});

test('duplicate refs, malformed geometry and incomplete inventories fail closed', () => {
    const duplicate = structuredClone(reference.board); duplicate.components[0].ref=duplicate.components[1].ref;
    assert.throws(()=>buildLandingBindings(duplicate),/Duplicate/);
    assert.throws(()=>buildLandingBindings({...reference.board,components:reference.board.components.slice(1)}),/29/);
    const malformed=structuredClone(reference.board);malformed.components[0].pads[0].width_mm=NaN;
    assert.throws(()=>buildLandingBindings(malformed),/finite/);
    assert.throws(()=>transformLandingPoint([NaN,0,0]),/finite/);
});

test('authoring report distinguishes derived projection hashes from missing original footprint hashes', () => {
    const output = JSON.parse(execFileSync(process.execPath,[fileURLToPath(new URL('../../../scripts/report_landing_pcb_bindings.mjs',import.meta.url))],{encoding:'utf8'}));
    assert.equal(output.source.referenceFileSha256,createHash('sha256').update(readFileSync(new URL('../reference-board.json',import.meta.url))).digest('hex'));
    for (const binding of output.entries) {
        assert.equal(binding.physicalLandProjection.sha256,createHash('sha256').update(binding.physicalLandProjection.canonicalJson).digest('hex'));
        assert.equal(binding.sourceIdentity.sourceFootprintFileSha256,null);
        assert.equal(binding.fit.status,'NOT_ESTABLISHED');
    }
});
