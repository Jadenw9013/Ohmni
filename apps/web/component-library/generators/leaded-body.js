import * as THREE from '../../vendor/three.module.js';
import { markingGeometry } from '../../visual-assets.js';

export function box(group, name, size, center, material) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
    mesh.name = name; mesh.position.set(...center); mesh.userData.material_token = material.name;
    group.add(mesh); return mesh;
}

function outline(width, length, notch = 0) {
    const shape = new THREE.Shape();
    shape.moveTo(-width / 2, -length / 2); shape.lineTo(width / 2, -length / 2);
    shape.lineTo(width / 2, length / 2);
    if (notch) { shape.lineTo(notch, length / 2); shape.absarc(0, length / 2, notch, 0, -Math.PI, true); }
    shape.lineTo(-width / 2, length / 2); shape.closePath(); return shape;
}

export function addBody(group, p, lod, material) {
    const sot = p.kind === 'sot23', w = sot ? p.body_length : p.body_width, l = sot ? p.body_width : p.body_length;
    const lower = p.standoff, h = p.overall_height - lower;
    const notch = p.kind === 'dip' ? p.notch_radius : 0;
    const add = (start, height, radius, name) => {
        const geometry = new THREE.ExtrudeGeometry(outline(w, l, radius), {
            depth: height, bevelEnabled: false, steps: lod === 'LOD2' ? 8 : 1, curveSegments: 12 });
        const pos = geometry.attributes.position;
        for (let i = 0; i < pos.count; i++) {
            let z = pos.getZ(i) + start;
            if (lod === 'LOD2' && start === lower && Math.abs(pos.getZ(i) - height / 2) < 1e-5) z = lower + h / 2;
            const relative = z - lower;
            // Maximum envelope remains at body mid-plane; top/bottom draft and
            // a small mid-plane relief are visual conventions from profile data.
            const shrink = lod === 'LOD2' ? Math.abs(relative - h / 2) * Math.tan(p.draft_degrees * Math.PI / 180)
                + (relative > h / 2 + 1e-6 ? p.parting_step : 0) : 0;
            pos.setXYZ(i, pos.getX(i) * (w - 2 * shrink) / w,
                pos.getY(i) * (l - 2 * shrink) / l, z);
        }
        geometry.computeVertexNormals(); geometry.computeBoundingBox();
        const mesh = new THREE.Mesh(geometry, material); mesh.name = name;
        mesh.userData.material_token = material.name; group.add(mesh);
    };
    if (notch && lod !== 'LOD0') {
        add(lower, h - p.notch_depth, 0, 'body');
        add(p.overall_height - p.notch_depth, p.notch_depth, notch, 'notched-top');
    } else add(lower, h, 0, 'body');
}

export function addMarkings(group, p, lod, marking, material) {
    const sot = p.kind === 'sot23', w = sot ? p.body_length : p.body_width, l = sot ? p.body_width : p.body_length;
    const decals = new THREE.Group(); decals.name = 'marking-decals';
    decals.userData = { role: 'separate_visual_decals', electrical_authority: false };
    group.add(decals);
    const decalMaterial = material.clone(); decalMaterial.color.set('#6E6E70');
    decalMaterial.polygonOffset = true; decalMaterial.polygonOffsetFactor = -2; decalMaterial.polygonOffsetUnits = -2;
    decalMaterial.userData = { ...material.userData, appearance_region: 'laser_mark', color_basis: 'spec MAT_EPOXY_BLACK laser region' };
    // Even the lowest LOD retains an orientation cue. SOT23 uses the requested
    // decal dot. Dual-row packages use a dimple-style ring decal at pin 1.
    if (p.mark_dot !== false) {
        const geometry = sot ? new THREE.CircleGeometry(p.dimple_diameter / 2, 24)
            : new THREE.RingGeometry(p.dimple_diameter * 0.3, p.dimple_diameter / 2, 24);
        const dot = new THREE.Mesh(geometry, decalMaterial); dot.name = 'pin1-decal';
        dot.position.set(-w / 2 + p.dimple_inset[0], (sot ? -1 : 1) * (l / 2 - p.dimple_inset[1]), p.overall_height);
        dot.userData = { role: 'pin1_indicator', terminal: '1', geometry_basis: 'separate decal per Stage 2 approval' }; decals.add(dot);
    }
    if (lod !== 'LOD0' && marking) {
        const text = new THREE.Mesh(markingGeometry(marking, w * 0.58, l * 0.16), decalMaterial);
        text.name = 'laser-mark-decal'; text.position.set(0, 0, p.overall_height);
        text.userData = { content: marking, content_basis: 'CALLER_SUPPLIED_VISUAL_TEXT' }; decals.add(text);
    }
    if (!decals.children.length) decalMaterial.dispose();
}
