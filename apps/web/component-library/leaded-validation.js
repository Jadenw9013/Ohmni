import { positive, finite, validateMetadata, LODS } from './validate.js';

export function terminalLayout(p) {
    if (p.kind === 'sot23') return p.lead_mask.map(([x, y], i) => ({ terminal: String(i + 1),
        center_mm: [x * p.pitch, y * p.contact_y, 0], side: y,
        geometric_center_mm: [x * p.pitch, y * (p.lead_span - p.foot_length) / 2, 0] }));
    const half = p.pin_count / 2, first = (half - 1) * p.pitch / 2;
    const x = p.kind === 'dip' ? p.row_spacing / 2 : (p.lead_span - p.foot_length) / 2;
    return Array.from({ length: p.pin_count }, (_, i) => ({ terminal: String(i + 1),
        center_mm: i < half ? [-x, first - i * p.pitch, 0] : [x, -first + (i - half) * p.pitch, 0],
        side: i < half ? -1 : 1 }));
}

export function validateLeaded(record, p) {
    validateMetadata(record);
    const generators = { dip: 'GEN-DIP', dual_gullwing: 'GEN-DUAL_GULLWING', sot23: 'GEN-SMD_POWER' };
    const families = { dip: ['PKG-DIP'], dual_gullwing: ['PKG-SOIC','PKG-TSSOP','PKG-SSOP','PKG-MSOP'], sot23: ['PKG-SOT23'] };
    if (record.generator !== generators[p.kind] || !/^OHM-\d{3}$/.test(record.id)
        || !families[p.kind]?.includes(record.package_family) || record.mounting !== (p.kind === 'dip' ? 'tht' : 'smd')
        || !record.lod_supported.every(x => LODS.includes(x))) throw new RangeError('Unsupported leaded record');
    for (const key of ['body_length', 'body_width', 'overall_height', 'standoff', 'pitch', 'lead_width', 'lead_thickness', 'dimple_diameter']) positive(p[key], key);
    if (!Number.isInteger(p.pin_count) || p.pin_count < 3 || p.pin_count > 64
        || (p.kind !== 'sot23' && p.pin_count % 2)) throw new RangeError('Invalid pin count');
    if (p.standoff >= p.overall_height || p.lead_width >= p.pitch) throw new RangeError('Invalid standoff or pitch');
    if (p.exposed_pad || record.pcb_interface.thermal_pad) throw new RangeError('No researched exposed pad in Stage 2');
    if (p.kind === 'sot23') {
        if (![3, 5, 6].includes(p.pin_count) || p.lead_mask.length !== p.pin_count) throw new RangeError('Invalid SOT23 lead mask');
        const expected = p.pin_count === 3 ? [[-1,-1],[1,-1],[0,1]] : p.pin_count === 5
            ? [[-1,-1],[0,-1],[1,-1],[1,1],[-1,1]] : [[-1,-1],[0,-1],[1,-1],[1,1],[0,1],[-1,1]];
        if (JSON.stringify(p.lead_mask) !== JSON.stringify(expected)) throw new RangeError('SOT23 numbering/mask conflict');
        if (2 * p.pitch + p.lead_width > p.body_length + 1e-9) throw new RangeError('Pin span exceeds body length');
    } else if ((p.pin_count / 2 - 1) * p.pitch + (p.kind === 'dip' ? p.shoulder_width : p.lead_width) > p.body_length + 1e-9) {
        throw new RangeError('Pin span plus lead width exceeds body length');
    }
    if (p.kind === 'dip') {
        for (const key of ['row_spacing', 'shoulder_width', 'tail_length']) positive(p[key], key);
        if (p.body_width >= p.row_spacing - p.lead_thickness || p.shoulder_width >= p.pitch
            || p.shoulder_width < p.lead_width) throw new RangeError('DIP body/shoulder/row conflict');
        if (p.overall_height - p.standoff <= p.notch_depth || p.notch_radius * 2 >= p.body_width) throw new RangeError('Notch consumes body');
    } else {
        positive(p.lead_span, 'lead_span'); positive(p.foot_length, 'foot_length');
        if (p.lead_span / 2 - p.foot_length <= p.body_width / 2) throw new RangeError('Lead span cannot accommodate body and foot');
        if (p.kind === 'sot23' && (p.contact_y < p.lead_span / 2 - p.foot_length || p.contact_y > p.lead_span / 2)) throw new RangeError('SOT23 contact reference misses physical foot');
    }
    const pin = terminalLayout(p)[0].center_mm;
    if (!p.pin1_xy?.every(Number.isFinite) || p.pin1_xy.length !== 2
        || p.pin1_xy.some((x, i) => Math.abs(x - pin[i]) > 1e-8)) throw new RangeError('Pin 1 position conflicts with numbering');
    for (const key of ['draft_degrees','parting_step','bend_radius']) {
        finite(p[key], key); if (p[key] < 0) throw new RangeError('Negative modeling parameter');
    }
    return record;
}
