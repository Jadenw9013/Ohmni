// Candidate package appearance. Electrical connectivity remains in candidate-board.json.
// The two added bodies use manufacturer envelopes; tiny bevels and finishes are illustrative.
import * as THREE from '../vendor/three.module.js';
import { createAsset, beveledBoxGeometry } from '../visual-assets.js';
import { gullWingLead } from '../component-library/generators/gull-wing-lead.js';

function add(group, name, geometry, material, position = [0, 0, 0]) {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = name; mesh.position.set(...position);
    mesh.castShadow = true; mesh.receiveShadow = true; group.add(mesh);
    return mesh;
}

function inductor(materials) {
    const group = new THREE.Group();
    add(group, 'XAL4020 nominal envelope; cosmetic edge rounding',
        beveledBoxGeometry(4, 4, 2, .12), materials.resin, [0, 0, .1]);
    // Manufacturer terminal drawing: nominal 0.82 x 3.25 mm; not the larger solder lands.
    for (const side of [-1, 1]) add(group, 'winding termination',
        new THREE.BoxGeometry(.82, 3.25, .1), materials.lead, [side * 1.195, 0, .05]);
    group.userData.modelSource = 'Coilcraft XAL4000 drawing; 4 mm nominal square, 2.1 mm max height';
    group.userData.physicalFit = 'NOT_ESTABLISHED';
    return group;
}

function translator(materials, pads) {
    const group = new THREE.Group();
    add(group, 'DCU nominal 2.0 x 2.3 mm body; cosmetic bevel',
        beveledBoxGeometry(2, 2.3, .8, .06), materials.resin, [0, 0, .1]);
    const leadGeometry = gullWingLead({ bodyEdge: 1, exitHeight: .45,
        tip: 1.55, footLength: .4, width: .25, thickness: .12, radius: 0 });
    const electrical = pads.filter(pad => pad.kind !== 'np_thru_hole');
    if (electrical.length !== 8) throw new Error('PCA9306 must have eight source terminals');
    const leads = new THREE.InstancedMesh(leadGeometry, materials.lead, electrical.length);
    leads.name = 'DCU leads; source pitch and cosmetic cross section';
    const transform = new THREE.Object3D();
    electrical.forEach((pad, i) => {
        transform.position.set(0, pad.y_mm, 0);
        transform.rotation.set(0, 0, pad.x_mm < 0 ? Math.PI : 0);
        transform.updateMatrix(); leads.setMatrixAt(i, transform.matrix);
    });
    leads.instanceMatrix.needsUpdate = true; leads.castShadow = true; leads.receiveShadow = true;
    group.add(leads);
    const pin1 = electrical.find(pad => pad.number === '1');
    if (!pin1) throw new Error('PCA9306 source pin 1 absent');
    add(group, 'pin 1 corner indication', new THREE.CircleGeometry(.10, 16), materials.darkMark,
        [Math.sign(pin1.x_mm) * .72, Math.sign(pin1.y_mm) * .88, .904]);
    group.userData.modelSource = 'TI DCU0008A nominal envelope; source footprint lead centers';
    group.userData.physicalFit = 'NOT_ESTABLISHED';
    return group;
}

export function createRedesignModelResolver(source) {
    const parts = new Map(source.board.components.map(part => [part.ref, part]));
    const cards = new Map(source.components.map(part => [part.ref, part]));
    return (instance, materials) => {
        const part = parts.get(instance.id), card = cards.get(instance.id);
        if (!part || !card || part.footprint_id !== instance.sourceFootprintId)
            throw new Error(`Candidate model/source identity mismatch: ${instance.id}`);
        let group;
        if (part.part_id === 'XAL4020-222MEB') group = inductor(materials);
        else if (part.part_id === 'PCA9306DCUT') group = translator(materials, part.pads);
        else {
            const family = card.category === 'capacitor' ? 'ceramic_chip'
                : card.category === 'resistor' ? 'chip_resistor'
                : card.category === 'header' ? 'pin_header' : instance.family;
            const options = { ...instance.options, label: false };
            if (family === 'ceramic_chip' || family === 'chip_resistor') {
                Object.assign(options, { width: 2, depth: 1.25,
                    height: family === 'ceramic_chip' ? .85 : .5 });
            }
            if (family === 'pin_header') options.height = 6.2;
            group = createAsset(family, options, materials);
        }
        group.userData.geometryClaim = 'Package appearance; copper/pads are generated circuit geometry';
        group.userData.sourceComponent = part.ref;
        return group;
    };
}
