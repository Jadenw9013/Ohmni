import { freeze, LODS } from './validate.js';
import { createLibraryMaterials, MATERIAL_TOKENS } from './materials.js';
import { validateDiscrete, discreteContacts, discreteBounds, UPRIGHT } from './discrete-layout.js';
import { generateDiscrete } from './generators/discrete.js';
import { VISUAL_SOURCE_HASH } from '../visual-version.js';

export function createDiscreteLibrary(data) {
    const d=structuredClone(data),records=Object.create(null);
    if(d.schema_version!==1||d.stage!==4||!/^[a-f0-9]{64}$/.test(d.source_spec_sha256))throw new RangeError('Invalid discrete library');
    for(const r of d.components){const p=d.profiles[r.profile_id];if(!p||Object.hasOwn(records,r.id))throw new RangeError('Missing/duplicate package profile');validateDiscrete(r,p);records[r.id]=r;}
    return freeze({...d,records});
}
export async function loadDiscreteLibrary(url=new URL('./data/discrete.json',import.meta.url),fetcher=globalThis.fetch) {
    const r=await fetcher(url);if(!r.ok)throw new Error('Discrete library unavailable');return createDiscreteLibrary(await r.json());
}
export function createDiscreteComponent(library,id,options={},materials=createLibraryMaterials()) {
    const record=library.records[id];if(!record)throw new RangeError('Unknown component');
    const profileId=options.package_member===undefined?record.profile_id:record.package_options?.[options.package_member];
    if(!profileId)throw new RangeError('Unsupported package member');
    const p=structuredClone(library.profiles[profileId]);Object.assign(p,record.appearance_overrides??{});
    const allowed=['lod','marking_text','package_member','outline','bidirectional','standoff','tail_length','band_width','body_type','pitch','stub_length','body_material','band_material'];
    if(Object.keys(options).some(k=>!allowed.includes(k)))throw new RangeError('Unsupported option');
    if(options.outline!==undefined){if(!p.outlines||!Object.hasOwn(p.outlines,options.outline))throw new RangeError('Unsupported outline');Object.assign(p,p.outlines[options.outline]);p.outline=options.outline;}
    if(options.bidirectional!==undefined){if(id!=='OHM-069'||typeof options.bidirectional!=='boolean')throw new RangeError('TVS boolean required');p.bidirectional=options.bidirectional;}
    for(const [key,target] of [['standoff','standoff'],['tail_length','tail'],['band_width','band_width'],['pitch','pitch'],['stub_length','stub_length']])if(options[key]!==undefined) {
        if(typeof options[key]!=='number'||!Number.isFinite(options[key]))throw new RangeError('Finite parameter required');
        if(key==='tail_length'&&!p.tail||key==='band_width'&&!p.band_width||key==='stub_length'&&p.stub_max===undefined||key==='pitch'&&p.pitch===undefined)throw new RangeError('Parameter not applicable');
        if(key==='standoff'&&['axial','melf'].includes(p.kind))throw new RangeError('Cylindrical seating is fixed');
        if(key==='standoff'&&p.body_height)p.height+=options[key]-p.standoff;
        p[target]=options[key];
    }
    if(options.body_type!==undefined) {
        if(p.kind!=='axial'||!['glass','molded'].includes(options.body_type))throw new RangeError('Invalid axial body type');
        p.body_material=options.body_type==='glass'?'MAT_DIODE_GLASS_AMBER':'MAT_EPOXY_BLACK';p.band_material=options.body_type==='glass'?'MAT_DIODE_BAND_BLACK':'MAT_DIODE_BAND_SILVER';
    }
    for(const key of ['body_material','band_material'])if(options[key]!==undefined){if(!Object.hasOwn(MATERIAL_TOKENS,options[key]))throw new RangeError('Unknown material token');p[key]=options[key];}
    const lod=options.lod??'LOD1',marking=options.marking_text??'';
    if(!LODS.includes(lod)||typeof marking!=='string'||!/^[A-Z0-9]{0,12}$/.test(marking))throw new RangeError('Invalid LOD or marking');
    const geometryRecord=library.records[profileId];
    validateDiscrete(geometryRecord,p);const contacts=discreteContacts(p),bounds=discreteBounds(p),model=generateDiscrete(p,lod,marking,contacts,materials);
    const metadata=structuredClone(record.library_metadata);
    if(Object.keys(options).some(k=>!['lod','marking_text'].includes(k))){metadata.provisional=true;metadata.uncertain_values.push('Explicit parameter variant; not independently source-verified.');}
    const identity=encodeURIComponent(JSON.stringify(Object.fromEntries(Object.entries(options).filter(([k])=>k!=='lod').sort(([a],[b])=>a.localeCompare(b)))));
    model.name=id;model.userData={component_id:id,package_family:geometryRecord.package_family,package_member:geometryRecord.package_member,generator:geometryRecord.generator,
        geometry_source_id:profileId,lod,units:'mm',up_axis:'Z',origin:'FCO',contact_plane_mm:0,status:record.status,library_metadata:metadata,source:record.source,confidence:record.confidence,
        parameters:p,contacts,terminal_count:new Set(contacts.map(c=>c.terminal)).size,contact_surface_count:contacts.length,source_lead_count:record.terminals.count,
        expected_dimensions_mm:bounds.size,expected_bounds_mm:bounds,height_above_board_mm:bounds.max[2],tail_below_board_top_mm:p.tail,
        fco_reference:{kind:'terminal-pattern',origin_mm:[0,0,0],mounting_holes:[],body_holes_excluded:true},
        body_holes:UPRIGHT.includes(p.kind)&&p.hole?[{diameter_mm:p.hole_diameter,center_mm:[0,0,p.standoff+p.height-p.hole_from_top],axis:'Y',fco_member:false}]:[],
        source_spec_sha256:library.source_spec_sha256,model_source_sha256:VISUAL_SOURCE_HASH,model_asset_id:`ohmni-component-library/${id}@discrete-v1/${identity}`,electrical_authority:false,
        simplifications:['No footprint binding or electrical admission. Raw source status is not independent verification.','Recognition bands, exposed tabs/holes and distinct leads are retained at every LOD, overriding lower-LOD omission suggestions.','Unsourced SMX polarity chamfers, ejector marks, glass internals and hidden leadframe interiors omitted.','Bridge function symbols are visual placeholders; actual per-pin function remains UNKNOWN.']};
    return model;
}
