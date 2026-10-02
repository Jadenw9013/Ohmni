import * as THREE from '../../vendor/three.module.js';
import { extrudedLeadProfile } from './gull-wing-lead.js';
import { addBody, addMarkings, box } from './leaded-body.js';
import { terminalLayout } from '../leaded-validation.js';

export function generateDip(record, p, { lod, marking }, materials) {
    const group = new THREE.Group(); group.name = record.id;
    addBody(group, p, lod, materials[record.body.material]);
    const contacts = terminalLayout(p), row = p.row_spacing / 2, c = p.lead_thickness;
    const exit = (p.standoff + p.overall_height) / 2, edge = p.body_width / 2;
    for (const contact of contacts) {
        const lead = new THREE.Group(); lead.name = `terminal-${contact.terminal}`;
        lead.userData.terminal = contact.terminal;
        const corner = [1, p.pin_count / 2, p.pin_count / 2 + 1, p.pin_count].includes(Number(contact.terminal));
        const width = lod === 'LOD0' ? p.lead_width : corner && p.corner_lead_slim ? p.corner_shoulder_width : p.shoulder_width;
        const r = lod === 'LOD2' ? Math.min(p.bend_radius, (row - edge) / 3) : 0;
        const points = [[edge, exit - c / 2], [row - c / 2, exit - c / 2], [row - c / 2, 0],
            [row + c / 2, 0], [row + c / 2, exit + c / 2 - r]];
        if (r) points.push([row + c / 2, exit + c / 2, row + c / 2 - r, exit + c / 2]);
        points.push([edge, exit + c / 2]);
        const geo = extrudedLeadProfile(points, width, r ? 6 : 1);
        if (lod === 'LOD2') {
            const pos = geo.attributes.position;
            for (let i = 0; i < pos.count; i++) if (pos.getZ(i) === 0) pos.setY(i, pos.getY(i) * 0.8);
            geo.computeVertexNormals();
        }
        const shoulder = new THREE.Mesh(geo, materials[record.terminals.material]); shoulder.name = 'shoulder';
        shoulder.userData.material_token = record.terminals.material; lead.add(shoulder);
        box(lead, 'tail', [c, p.lead_width, p.tail_length], [row, 0, -p.tail_length / 2], materials[record.terminals.material]);
        lead.rotation.z = contact.side < 0 ? Math.PI : 0; lead.position.y = contact.center_mm[1];
        group.add(lead);
    }
    addMarkings(group, p, lod, marking, materials[record.body.material]);
    return { group, contacts: contacts.map(c => ({ ...c, size_mm: [p.lead_thickness, p.lead_width],
        tail_bottom_mm: -p.tail_length, reference_basis: 'THT_LEAD_AXIS_AT_BOARD_TOP' })) };
}
