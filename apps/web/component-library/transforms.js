import * as THREE from '../vendor/three.module.js';
import { finite, positive } from './validate.js';

// Model coordinates: board top z=0. Existing viewer: board centered on z=0.
// This wrapper never changes the canonical child geometry or local metadata.
export function placeInViewer(model, { x_mm = 0, y_mm = 0, rotation_deg = 0,
    side = 'F.Cu', board_thickness_mm = 1.6 } = {}) {
    [x_mm, y_mm, rotation_deg].forEach(v => finite(v, 'placement'));
    positive(board_thickness_mm, 'board thickness');
    if (!['F.Cu', 'B.Cu'].includes(side)) throw new RangeError('Unknown board side');
    const root = new THREE.Group(); root.name = `placement:${model.name}`;
    root.position.set(x_mm, y_mm, (side === 'B.Cu' ? -1 : 1) * board_thickness_mm / 2);
    root.rotation.z = rotation_deg * Math.PI / 180;
    if (side === 'B.Cu') root.scale.set(-1, 1, -1);
    root.add(model); return root;
}

// Use actual pad/hole extents, not the average of pad centers or the body box.
export function footprintFCO(pads, frame) {
    if (!['OHMNI_Y_UP', 'KICAD_Y_DOWN'].includes(frame) || !Array.isArray(pads) || !pads.length) throw new RangeError('Explicit footprint frame and pads required');
    const bounds = [Infinity, Infinity, -Infinity, -Infinity];
    for (const pad of pads) {
        const x = finite(pad.x_mm, 'pad x'), y = finite(pad.y_mm, 'pad y') * (frame === 'KICAD_Y_DOWN' ? -1 : 1);
        const w = positive(pad.width_mm, 'pad width'), h = positive(pad.height_mm, 'pad height');
        const angle = finite(pad.rotation_deg ?? 0, 'pad angle') * Math.PI / 180;
        const shape = pad.shape ?? 'rect';
        if (!['rect', 'roundrect', 'circle', 'oval'].includes(shape)) throw new RangeError('Unsupported footprint shape');
        if (shape === 'circle' && w !== h) throw new RangeError('Circle width must equal height');
        if (shape === 'roundrect' && pad.corner_radius_mm === undefined
            && Math.abs(Math.sin(2 * angle)) > 1e-9) throw new RangeError('Oblique roundrect requires its corner radius');
        const radius = ['circle', 'oval'].includes(shape) ? Math.min(w, h) / 2
            : shape === 'roundrect' ? pad.corner_radius_mm ?? 0 : 0;
        finite(radius, 'corner radius');
        if (radius < 0 || radius > Math.min(w, h) / 2) throw new RangeError('Invalid corner radius');
        // Minkowski sum of the inner rectangle/line and a radius-r circle.
        const dx = Math.abs(Math.cos(angle)) * (w / 2 - radius) + Math.abs(Math.sin(angle)) * (h / 2 - radius) + radius;
        const dy = Math.abs(Math.sin(angle)) * (w / 2 - radius) + Math.abs(Math.cos(angle)) * (h / 2 - radius) + radius;
        bounds[0] = Math.min(bounds[0], x - dx); bounds[1] = Math.min(bounds[1], y - dy);
        bounds[2] = Math.max(bounds[2], x + dx); bounds[3] = Math.max(bounds[3], y + dy);
    }
    return [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2];
}

// A binding records identity and transform; its existence does not verify fit.
export function validateFootprintBinding(binding, model, footprint) {
    if (!binding || binding.component_id !== model.userData.component_id
        || binding.source_spec_sha256 !== model.userData.source_spec_sha256
        || binding.model_asset_id !== model.userData.model_asset_id
        || binding.model_source_sha256 !== model.userData.model_source_sha256
        || binding.footprint_id !== footprint.id || binding.footprint_sha256 !== footprint.sha256
        || !/^[a-f0-9]{64}$/.test(footprint.sha256)) throw new RangeError('Exact model/footprint revision required');
    footprintFCO(footprint.pads, binding.frame);
    if (!Array.isArray(binding.translation_mm) || binding.translation_mm.length !== 2) throw new RangeError('Explicit translation required');
    binding.translation_mm.forEach(v => finite(v, 'binding translation'));
    finite(binding.rotation_deg, 'binding rotation');
    const mapping = binding.terminal_to_pad;
    if (!mapping || Object.keys(mapping).length !== model.userData.contacts.length) throw new RangeError('Complete terminal mapping required');
    const names = new Set(footprint.pads.map(pad => String(pad.number)));
    for (const contact of model.userData.contacts) {
        if (!Object.hasOwn(mapping, contact.terminal) || !names.has(mapping[contact.terminal])) throw new RangeError('Missing named pad mapping');
    }
    if (new Set(Object.values(mapping)).size !== model.userData.contacts.length) throw new RangeError('Ambiguous terminal mapping');
    return structuredClone(binding);
}

export function tailBottom(board_thickness_mm = 1.6, tail_below_board_top_mm) {
    positive(board_thickness_mm, 'board thickness');
    return -(tail_below_board_top_mm === undefined ? board_thickness_mm + 1 : positive(tail_below_board_top_mm, 'tail override'));
}
