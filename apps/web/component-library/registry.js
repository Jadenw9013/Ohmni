import { freeze, validateRecord, LODS, positive } from './validate.js';
import { createLibraryMaterials } from './materials.js';
import { generateChip2T } from './generators/chip-2t.js';
import { VISUAL_SOURCE_HASH } from '../visual-version.js';

export const LIBRARY_ASSET_VERSION = 'chip2t-v1';

export function createLibrary(data) {
    const snapshot = structuredClone(data);
    if (snapshot.schema_version !== 1 || !/^[a-f0-9]{64}$/.test(snapshot.source_spec_sha256)
        || snapshot.family.id !== 'PKG-CHIP2T' || snapshot.family.generator !== 'GEN-CHIP_2T') throw new RangeError('Unsupported library');
    const records = Object.create(null);
    for (const component of snapshot.components) {
        const profile = snapshot.family.profiles[component.profile_id];
        if (!profile || profile.member !== component.package_member || Object.hasOwn(records, component.id)) throw new RangeError('Missing profile or duplicate component');
        const resolved = { ...component, function: profile.function, dimensions_mm: profile.dimensions_mm };
        records[component.id] = validateRecord(resolved);
    }
    for (const [key, value] of Object.entries(snapshot.modeling_defaults)) {
        if (key.endsWith('_mm') && key !== 'cap_proudness_mm') positive(value, key);
    }
    if (snapshot.modeling_defaults.cap_proudness_mm !== 0) throw new RangeError('This generator omits optional cap proudness');
    for (const record of Object.values(records)) {
        const height = record.dimensions_mm.overall_height.default;
        if ((record.function === 'R' && height < snapshot.modeling_defaults.resistor_coat_mm + 0.05)
            || (record.function === 'CURRENT_SENSE' && height * 0.15 < snapshot.modeling_defaults.current_sense_coat_mm)) throw new RangeError('Coating exceeds the package envelope');
    }
    return freeze({ source_spec_sha256: snapshot.source_spec_sha256,
        family: snapshot.family, records, defaults: snapshot.modeling_defaults });
}

export async function loadLibrary(url = new URL('./data/chip2t.json', import.meta.url), fetcher = globalThis.fetch) {
    const response = await fetcher(url);
    if (!response.ok) throw new Error('Component library unavailable');
    return createLibrary(await response.json());
}

export function createComponent(library, id, options = {}, materials = createLibraryMaterials()) {
    if (!Object.hasOwn(library.records, id)) throw new RangeError(`Unknown component: ${id}`);
    const allowed = new Set(['lod', 'overall_height', 'marking_text', 'body_material']);
    for (const key of Object.keys(options)) if (!allowed.has(key)) throw new RangeError(`Unsupported option: ${key}`);
    const record = structuredClone(library.records[id]);
    const lod = options.lod ?? 'LOD1';
    if (!LODS.includes(lod) || !record.lod_supported.includes(lod)) throw new RangeError('Unsupported LOD');
    if (options.overall_height !== undefined) {
        const dimension = record.dimensions_mm.overall_height;
        if (record.function !== 'C' || dimension.min === undefined || dimension.max === undefined
            || positive(options.overall_height, 'overall_height') < dimension.min || options.overall_height > dimension.max) throw new RangeError('Unsupported thickness variant');
        dimension.default = options.overall_height;
    }
    if (options.body_material !== undefined) {
        if (record.function !== 'C' || !['MAT_MLCC_BROWN', 'MAT_MLCC_GRAY'].includes(options.body_material)) throw new RangeError('Unsupported body material');
        record.body.material = options.body_material;
    }
    const marking = options.marking_text ?? '';
    if (typeof marking !== 'string' || !/^[A-Z0-9]{0,4}$/.test(marking)
        || (marking && !(record.function === 'CURRENT_SENSE'
            || (record.function === 'R' && !['01005I', '0201I', '0402I'].includes(record.package_member))))) throw new RangeError('Unsupported marking');
    validateRecord(record);
    const model = generateChip2T(record, library.defaults, { lod, marking }, materials);
    model.userData.source_spec_sha256 = library.source_spec_sha256;
    model.userData.model_asset_id = `ohmni-component-library/${id}@${LIBRARY_ASSET_VERSION}`;
    model.userData.model_source_sha256 = VISUAL_SOURCE_HASH;
    return model;
}
