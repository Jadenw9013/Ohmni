import { freeze, LODS } from './validate.js';
import { createLibraryMaterials } from './materials.js';
import { validateQuadGrid, perimeterLayout, gridLayout } from './quad-grid-layout.js';
import { generateQuadGrid } from './generators/quad-grid.js';
import { VISUAL_SOURCE_HASH } from '../visual-version.js';

const isGrid=p=>['bga','wlcsp'].includes(p.kind);
export function createQuadGridLibrary(data) {
    const snapshot=structuredClone(data),records=Object.create(null);
    if(snapshot.schema_version!==1||snapshot.stage!==3||!/^[a-f0-9]{64}$/.test(snapshot.source_spec_sha256))throw new RangeError('Unsupported Stage 3 library');
    for(const record of snapshot.components) {
        const p=snapshot.profiles[record.profile_id];
        if(!p||Object.hasOwn(records,record.id)||p.pin_count!==record.terminals.count)throw new RangeError('Missing/duplicate profile or wrong pin count');
        validateQuadGrid(record,p);
        const contacts=isGrid(p)?gridLayout(p):perimeterLayout(p);
        if(contacts.length!==record.terminals.count||contacts[0].center_mm.slice(0,2).some((v,i)=>Math.abs(v-record.terminals.pin1_xy_mm[i])>1e-8))throw new RangeError('Source pin1/count disagrees with geometry');
        records[record.id]=record;
    }
    return freeze({...snapshot,records});
}
export async function loadQuadGridLibrary(url=new URL('./data/quad-grid.json',import.meta.url),fetcher=globalThis.fetch) {
    const response=await fetcher(url);if(!response.ok)throw new Error('Stage 3 library unavailable');
    return createQuadGridLibrary(await response.json());
}

export function createQuadGridComponent(library,id,options={},materials=createLibraryMaterials()) {
    const record=library.records[id];if(!record)throw new RangeError('Unknown component');
    const p=structuredClone(library.profiles[record.profile_id]);
    const controls=p.parameter_controls;
    let custom=false;
    for(const [key,value] of Object.entries(options)) {
        if(['lod','marking_text'].includes(key))continue;
        if(!Object.hasOwn(controls,key))throw new RangeError(`Unsupported option ${key}`);
        const target=controls[key];
        if(['pin1_mode','row_letters'].includes(target)) {if(typeof value!=='string')throw new RangeError('String parameter required');}
        else if(target==='array_offset') {if(!Array.isArray(value)||value.length!==2||!value.every(Number.isFinite))throw new RangeError('Finite XY offset required');}
        else if(target==='depopulate') {if(!value||typeof value!=='object'||Array.isArray(value))throw new RangeError('Depopulation record required');}
        else if(typeof value!=='number'||!Number.isFinite(value)||value<0)throw new RangeError('Finite nonnegative parameter required');
        if(target==='body_size')p.body_x=p.body_y=value;
        else if(target==='ep_size')p.ep_x=p.ep_y=value;
        else p[target]=structuredClone(value);
        custom=true;
    }
    if(options.pin_count!==undefined) {
        const populated=p.side_counts.filter(n=>n>0).length;
        if(!Number.isInteger(p.pin_count)||p.pin_count%populated)throw new RangeError('Pin count must divide among populated sides');
        p.side_counts=p.side_counts.map(n=>n?p.pin_count/populated:0);
    }
    if('body_thickness' in p)p.height=p.standoff+p.body_thickness;
    const lod=options.lod??'LOD1',marking=options.marking_text??'';
    if(!LODS.includes(lod)||typeof marking!=='string'||!/^[A-Z0-9]{0,12}$/.test(marking))throw new RangeError('Invalid LOD/marking');
    validateQuadGrid(record,p);
    const contacts=isGrid(p)?gridLayout(p):perimeterLayout(p);
    const group=generateQuadGrid(record,p,lod,marking,contacts,materials);
    const metadata=structuredClone(record.library_metadata);
    if(custom){metadata.provisional=true;metadata.uncertain_values.push('Explicit parameter variant; geometry checks passed but altered dimensions/map are not independently source-verified.');}
    if(p.pullback>0)metadata.conflicts.push({code:'EXPLICIT_PULLBACK_VARIANT',value_mm:p.pullback,
        policy:'Variant changes radial terminal centers and EP clearance. Default source is flush; footprint binding remains unassigned.'});
    const size=['qfp','plcc'].includes(p.kind)?[p.lead_span,p.lead_span,p.height]:[p.body_x,p.body_y,p.height];
    const identity=encodeURIComponent(JSON.stringify(Object.fromEntries(Object.entries(options).filter(([k])=>k!=='lod').sort(([a],[b])=>a.localeCompare(b)))));
    group.userData={component_id:id,package_family:record.package_family,package_member:record.package_member,
        generator:record.generator,lod,status:record.status,library_metadata:metadata,units:'mm',up_axis:'Z',origin:'FCO',contact_plane_mm:0,
        expected_dimensions_mm:size,contacts,terminal_count:contacts.length,side_counts:p.side_counts??null,
        exposed_pad:p.ep_x?{size_mm:[p.ep_x,p.ep_y],center_mm:[0,0,0],numbered:false}:null,
        parameters:p,source:record.source,confidence:record.confidence,source_spec_sha256:library.source_spec_sha256,
        model_source_sha256:VISUAL_SOURCE_HASH,model_asset_id:`ohmni-component-library/${id}@quad-grid-v1/${identity}`,
        electrical_authority:false,simplifications:['No footprint pads, solder fillets, or electrical admission.',
            'LOD0 bands/slab are visual proxies; discrete numbered contacts remain in metadata.',
            'LOD0 ball-layer texture preserves populated grid and depopulation recognition.',
            'Pin1/A1 index uses a separate decal; manufacturer marking details remain uncertain.',
            'Optional unsourced ejector marks, tie bars, wettable flanks and mask openings omitted.']};
    return group;
}
