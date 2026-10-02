import { MATERIAL_TOKENS } from './materials.js';

export const LODS = Object.freeze(['LOD0', 'LOD1', 'LOD2']);
export function finite(value, label) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new RangeError(`${label}: finite number required`);
    return value;
}
export function positive(value, label) {
    finite(value, label);
    if (value <= 0 || value > 500) throw new RangeError(`${label}: expected 0 < mm <= 500`);
    return value;
}
export function freeze(value) {
    if (value && typeof value === 'object') {
        Object.values(value).forEach(freeze); Object.freeze(value);
    }
    return value;
}
export function chipDimensions(record) {
    const d = record.dimensions_mm;
    return { L: d.overall_length.default, W: d.overall_width.default, H: d.overall_height.default,
        top: (d.terminal_band_top ?? d.terminal_band ?? d.terminal_length).default,
        bottom: (d.terminal_band_bottom ?? d.terminal_band ?? d.terminal_length).default };
}
export function validateRecord(record) {
    if (!/^OHM-\d{3}$/.test(record.id) || record.generator !== 'GEN-CHIP_2T'
        || record.package_family !== 'PKG-CHIP2T' || record.mounting !== 'smd') throw new RangeError('Unsupported component contract');
    if (!['complete', 'partial'].includes(record.status)) throw new RangeError('Unresolved research placeholder');
    if (record.library_metadata.provisional !== (record.status === 'partial')
        || !Array.isArray(record.library_metadata.uncertain_values)
        || (record.status === 'partial' && !record.library_metadata.uncertain_values.length)) throw new RangeError('Missing provisional metadata');
    if (record.orientation.origin !== 'FCO' || record.orientation.pcb_plane !== 'XY'
        || record.orientation.height_axis !== 'Z' || record.polarity !== 'none') throw new RangeError('Unsupported coordinate or polarity convention');
    if (!['R', 'C', 'L', 'CURRENT_SENSE'].includes(record.function)) throw new RangeError('Unsupported CHIP2T profile');
    for (const [key, d] of Object.entries(record.dimensions_mm)) {
        positive(d.default, key);
        if (!['H', 'M', 'L'].includes(d.confidence)
            || !['STANDARD', 'MFR_DRAWING', 'MFR_DATASHEET', 'CONSENSUS', 'DERIVED', 'UNCERTAIN'].includes(d.basis)) throw new RangeError('Missing dimension provenance');
        if (d.basis === 'UNCERTAIN' && d.confidence !== 'L') throw new RangeError('Uncertainty must retain confidence L');
        if (d.min !== undefined && positive(d.min, key) > d.default) throw new RangeError('Default below minimum');
        if (d.max !== undefined && positive(d.max, key) < d.default) throw new RangeError('Default above maximum');
    }
    const { L, W, H, top, bottom } = chipDimensions(record);
    if (2 * Math.max(top, bottom) >= L || (record.function === 'CURRENT_SENSE' && L - 2 * bottom < 0.3)) throw new RangeError('Terminal bands consume center window');
    if (record.terminals.count !== 2 || record.terminals.type !== 'flat_pad'
        || Math.abs(record.terminals.width_mm - W) > 1e-9
        || Math.abs(record.terminals.length_mm - bottom) > 1e-9) throw new RangeError('Terminal contract disagrees with dimensions');
    const pin = record.terminals.pin1_xy_mm;
    if (!Array.isArray(pin) || pin.length !== 2 || !pin.every(Number.isFinite)
        || Math.abs(pin[0] + (L - bottom) / 2) > 1e-9 || pin[1] !== 0) throw new RangeError('Pin 1 contact center disagrees with spec');
    if (record.pcb_interface.standoff_mm !== 0 || record.pcb_interface.body_offset_mm?.some(v => v !== 0)) throw new RangeError('Unsupported CHIP2T seating');
    for (const token of [record.body.material, record.terminals.material]) {
        if (!Object.hasOwn(MATERIAL_TOKENS, token)) throw new RangeError(`Undefined material: ${token}`);
    }
    if (H < 0.05 || !record.lod_supported.every(lod => LODS.includes(lod))) throw new RangeError('Invalid height/LOD');
    return record;
}
