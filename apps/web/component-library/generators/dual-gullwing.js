import * as THREE from '../../vendor/three.module.js';
import { gullWingLead } from './gull-wing-lead.js';
import { addBody, addMarkings, box } from './leaded-body.js';
import { terminalLayout } from '../leaded-validation.js';

export function generateDualGullwing(record, p, { lod, marking }, materials) {
    const group = new THREE.Group(); group.name = record.id;
    const sot = p.kind === 'sot23', contacts = terminalLayout(p);
    addBody(group, p, lod, materials[record.body.material]);
    if (lod === 'LOD0' && !sot) {
        const span = (p.pin_count / 2 - 1) * p.pitch + p.lead_width;
        for (const side of [-1, 1]) {
            const mesh = box(group, `merged-foot-bar-${side}`, [p.foot_length, span, p.lead_thickness],
                [side * (p.lead_span - p.foot_length) / 2, 0, p.lead_thickness / 2], materials[record.terminals.material]);
            mesh.userData.terminals = contacts.filter(c => c.side === side).map(c => c.terminal);
        }
    } else for (const contact of contacts) {
        const foot = contact.geometric_center_mm ?? contact.center_mm;
        let mesh;
        if (lod === 'LOD0') {
            mesh = box(group, `terminal-${contact.terminal}`, [p.lead_width, p.foot_length, p.lead_thickness],
                [foot[0], foot[1], p.lead_thickness / 2], materials[record.terminals.material]);
        } else {
            const geometry = gullWingLead({ bodyEdge: p.body_width / 2, exitHeight: (p.overall_height + p.standoff) / 2,
                tip: p.lead_span / 2, footLength: p.foot_length, width: p.lead_width,
                thickness: p.lead_thickness, radius: lod === 'LOD2' ? p.bend_radius : 0 });
            mesh = new THREE.Mesh(geometry, materials[record.terminals.material]); mesh.name = `terminal-${contact.terminal}`;
            mesh.rotation.z = sot ? contact.side * Math.PI / 2 : contact.side < 0 ? Math.PI : 0;
            if (sot) mesh.position.x = contact.center_mm[0]; else mesh.position.y = contact.center_mm[1];
            group.add(mesh);
        }
        mesh.userData = { terminal: contact.terminal, material_token: record.terminals.material };
    }
    addMarkings(group, p, lod, marking, materials[record.body.material]);
    return { group, contacts: contacts.map(c => ({ ...c, size_mm: sot ? [p.lead_width, p.foot_length] : [p.foot_length, p.lead_width],
        reference_basis: sot ? 'SPEC_MANDATED_CONTACT_REFERENCE; physical centroid separately reported' : 'GEOMETRIC_FOOT_CENTER' })) };
}
