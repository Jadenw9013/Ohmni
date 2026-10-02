import { freeze, LODS } from './validate.js';
import { createLibraryMaterials } from './materials.js';
import { validateLeaded, terminalLayout } from './leaded-validation.js';
import { generateDualGullwing } from './generators/dual-gullwing.js';
import { generateDip } from './generators/dip.js';
import { VISUAL_SOURCE_HASH } from '../visual-version.js';

export function createLeadedLibrary(data) {
    const snapshot = structuredClone(data);
    if (snapshot.schema_version !== 1 || snapshot.stage !== 2 || !/^[a-f0-9]{64}$/.test(snapshot.source_spec_sha256)) throw new RangeError('Unsupported Stage 2 library');
    const records = Object.create(null);
    for (const record of snapshot.components) {
        const p = snapshot.profiles[record.profile_id];
        if (!p || Object.hasOwn(records, record.id) || p.pin_count !== record.terminals.count) throw new RangeError('Missing/duplicate profile or pin-count mismatch');
        validateLeaded(record, p);
        if (p.pin1_xy.some((x, i) => Math.abs(x - record.terminals.pin1_xy_mm[i]) > 1e-8)) throw new RangeError('Source pin1 mismatch');
        for (const variant of Object.values(p.variants)) validateLeaded(record, { ...p, ...variant });
        records[record.id] = record;
    }
    return freeze({ ...snapshot, records });
}

export async function loadLeadedLibrary(url = new URL('./data/leaded.json', import.meta.url), fetcher = globalThis.fetch) {
    const response = await fetcher(url);
    if (!response.ok) throw new Error('Stage 2 library unavailable');
    return createLeadedLibrary(await response.json());
}

export function createLeadedComponent(library, id, options = {}, materials = createLibraryMaterials()) {
    const record = library.records[id];
    if (!record) throw new RangeError('Unknown component');
    let p = structuredClone(library.profiles[record.profile_id]);
    const policy = p.parameter_policy;
    const allowed = new Set(['lod','variant','marking_text','configuration','exposed_pad',
        ...policy.numeric, ...policy.boolean, ...Object.keys(policy.variant_selectors)]);
    if (Object.keys(options).some(k => !allowed.has(k))) throw new RangeError('Unsupported option');
    let variant = options.variant ?? 'default';
    for (const [key, values] of Object.entries(policy.variant_selectors)) {
        if (options[key] === undefined) continue;
        if (!Object.hasOwn(values, String(options[key]))) throw new RangeError(`Unsupported ${key}`);
        const selected = values[String(options[key])];
        if (options.variant !== undefined && variant !== selected) throw new RangeError('Conflicting variant selectors');
        variant = selected;
    }
    if (variant !== 'default') {
        if (!Object.hasOwn(p.variants, variant)) throw new RangeError('Unsupported variant');
        p = { ...p, ...p.variants[variant] };
    }
    if (options.exposed_pad !== undefined && options.exposed_pad !== false) throw new RangeError('Exposed pad is unresearched; no geometry inferred');
    const variantKeys = new Set(['variant','lod','marking_text','configuration','exposed_pad',...Object.keys(policy.variant_selectors)]);
    let custom = false;
    for (const [key, value] of Object.entries(options)) {
        if (variantKeys.has(key)) continue;
        if (policy.enum[key] && !policy.enum[key].includes(value)) throw new RangeError(`Unsupported ${key}`);
        if (policy.boolean.includes(key)) {
            if (typeof value !== 'boolean') throw new RangeError('Boolean parameter required');
        } else if (!Number.isFinite(value) || value <= 0) throw new RangeError('Positive numeric parameter required');
        if (key !== 'body_thickness') p[key] = value;
        custom = true;
    }
    if (options.body_thickness !== undefined) p.overall_height = p.standoff + options.body_thickness;
    if (options.pin_count !== undefined && p.kind === 'sot23') {
        if (!policy.pin_count_masks?.[p.pin_count]) throw new RangeError('Unsupported SOT23 pin-count variant');
        p.lead_mask = structuredClone(policy.pin_count_masks[p.pin_count]);
    }
    if (custom) p.pin1_xy = terminalLayout(p)[0].center_mm.slice(0,2);
    const lod = options.lod ?? 'LOD1', marking = options.marking_text ?? '';
    if (!LODS.includes(lod) || typeof marking !== 'string' || !/^[A-Z0-9]{0,12}$/.test(marking)) throw new RangeError('Invalid LOD/marking');
    const configuration = options.configuration ?? policy.configuration_default;
    if (configuration !== null && !policy.configuration_values.includes(configuration)) throw new RangeError('Invalid diode configuration');
    validateLeaded(record, p);
    const { group, contacts } = (p.kind === 'dip' ? generateDip : generateDualGullwing)(record, p, { lod, marking }, materials);
    const dimensions = p.kind === 'dip' ? [p.row_spacing + p.lead_thickness, p.body_length, p.overall_height + p.tail_length]
        : p.kind === 'sot23' ? [p.body_length, p.lead_span, p.overall_height] : [p.lead_span, p.body_length, p.overall_height];
    const metadata = structuredClone(record.library_metadata);
    if (p.kind === 'sot23') {
        metadata.source_conflicts = structuredClone(metadata.conflicts);
        const center = (p.lead_span - p.foot_length) / 2;
        metadata.conflicts[0] = { ...metadata.conflicts[0], spec_contact_abs_mm: p.contact_y,
            geometric_foot_center_abs_mm: +center.toFixed(6), delta_mm: +(center - p.contact_y).toFixed(6) };
    }
    if (custom) { metadata.provisional = true; metadata.uncertain_values.push('Caller parameter override: geometry validated; altered dimensions are not source-verified.'); }
    const optionIdentity = encodeURIComponent(JSON.stringify(Object.fromEntries(Object.entries(options).filter(([k]) => k !== 'lod').sort(([a],[b])=>a.localeCompare(b)))));
    group.userData = { component_id: id, package_family: record.package_family, package_member: record.package_member,
        generator: record.generator, lod, status: record.status, library_metadata: metadata,
        units: 'mm', up_axis: 'Z', origin: 'FCO', contact_plane_mm: 0, expected_dimensions_mm: dimensions,
        contacts, parameters: p, variant, configuration, confidence: record.confidence, source: record.source,
        source_spec_sha256: library.source_spec_sha256, model_source_sha256: VISUAL_SOURCE_HASH,
        model_asset_id: `ohmni-component-library/${id}@leaded-v1/${variant}/${optionIdentity}`, electrical_authority: false,
        simplifications: ['No pads or solder; footprint bindings remain explicit and unbound',
            'Pin-1 dimple rendered as separate orientation decal per Stage 2 approval',
            'LOD0 dual gull-wing rows use merged foot bars; terminal metadata retains each numbered contact'] };
    if (configuration) {
        const functions = { common_cathode:['A1','A2','K_COMMON'], common_anode:['K1','K2','A_COMMON'], series:['A1','K2','K1_A2'] }[configuration];
        contacts.forEach((c,i) => { c.pin_function = functions[i]; });
    }
    return group;
}
