import { freeze, LODS } from './validate.js';
import { createLibraryMaterials } from './materials.js';
import { validateLedPassive, ledPassiveContacts, ledPassiveBounds } from './led-passive-layout.js';
import { generateLedPassive } from './generators/led-passive.js';
import { VISUAL_SOURCE_HASH } from '../visual-version.js';

export function createLedPassiveLibrary(data) {
    const d=structuredClone(data),records=Object.create(null);
    if(d.schema_version!==1||d.stage!==5||!/^[a-f0-9]{64}$/.test(d.source_spec_sha256))throw new RangeError('Invalid Stage 5 data');
    for(const r of d.components){if(Object.hasOwn(records,r.id)||!d.profiles[r.profile_id])throw new RangeError('Duplicate/missing profile');validateLedPassive(r,d.profiles[r.profile_id]);records[r.id]=r;}
    return freeze({...d,records});
}
export async function loadLedPassiveLibrary(url=new URL('./data/led-passive.json',import.meta.url),fetcher=globalThis.fetch){const r=await fetcher(url);if(!r.ok)throw new Error('Stage 5 library unavailable');return createLedPassiveLibrary(await r.json());}
export function createLedPassiveComponent(library,id,options={},materials=createLibraryMaterials()) {
    const r=library.records[id];if(!r)throw new RangeError('Unknown component');const p=structuredClone(library.profiles[r.profile_id]);
    const allowed=['lod','marking_text','led_color','lens','band_colors','pitch','tail_length','anode_extra'];
    if(Object.keys(options).some(k=>!allowed.includes(k)))throw new RangeError('Unsupported Stage 5 parameter');
    for(const k of ['led_color','lens','anode_extra'])if(options[k]!==undefined){if(!p.kind.startsWith('led')||k==='anode_extra'&&!['led_tht','led_rect'].includes(p.kind))throw new RangeError('Not an LED parameter');p[k]=options[k];}
    for(const [k,key] of [['pitch','pitch'],['tail_length','tail']])if(options[k]!==undefined){if(!p[key]||typeof options[k]!=='number'||!Number.isFinite(options[k])||options[k]<=0||k==='pitch'&&!['axial','can','disc','film','mica'].includes(p.kind))throw new RangeError('Invalid length variant');p[key]=options[k];}
    if(options.band_colors!==undefined){if(!p.band_count||!Array.isArray(options.band_colors))throw new RangeError('Not a banded component');p.band_colors=[...options.band_colors];}
    if(p.anode_extra!==undefined&&(typeof p.anode_extra!=='number'||!Number.isFinite(p.anode_extra)||p.anode_extra<0||p.anode_extra>20))throw new RangeError('Invalid lead difference');
    const lod=options.lod??'LOD1',marking=options.marking_text??'';
    if(!LODS.includes(lod)||typeof marking!=='string'||!/^[A-Z0-9]{0,12}$/.test(marking))throw new RangeError('Invalid LOD/marking');
    validateLedPassive(r,p);const contacts=ledPassiveContacts(p),bounds=ledPassiveBounds(p,lod),model=generateLedPassive(p,lod,marking,contacts,materials,library.profiles);
    const metadata=structuredClone(r.library_metadata);if(Object.keys(options).some(k=>!['lod','marking_text'].includes(k))){metadata.provisional=true;metadata.uncertain_values.push('Caller parameter variant; geometry/appearance is not independently source-verified.');}
    const identity=encodeURIComponent(JSON.stringify(Object.fromEntries(Object.entries(options).filter(([k])=>k!=='lod').sort(([a],[b])=>a.localeCompare(b)))));
    model.name=id;model.userData={component_id:id,owner:id,package_family:r.package_family,package_member:r.package_member,generator:r.generator,lod,units:'mm',up_axis:'Z',origin:'FCO',contact_plane_mm:p.kind==='led_star'?p.board_thickness+p.lead_thickness:0,status:r.status,library_metadata:metadata,source:r.source,confidence:r.confidence,parameters:p,contacts,terminal_count:contacts.length,expected_bounds_mm:bounds,expected_dimensions_mm:bounds.size,height_above_board_mm:bounds.max[2],tail_below_board_top_mm:-bounds.min[2],source_spec_sha256:library.source_spec_sha256,model_source_sha256:VISUAL_SOURCE_HASH,model_asset_id:`ohmni-component-library/${id}@led-passive-v1/${identity}`,electrical_authority:false,footprint_binding:null};
    model.traverse(n=>{if(n.isMesh)n.userData.component_id=id;});
    return model;
}
