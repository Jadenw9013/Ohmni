import * as THREE from '../vendor/three.module.js';
import { freeze, LODS } from './validate.js';
import { createCompletionMaterials } from './completion-materials.js';
import { generateHeaderConnector, HEADER_CONNECTOR_FAMILIES } from './generators/header-connectors.js';
import { VISUAL_SOURCE_HASH } from '../visual-version.js';

export function completionContacts(p){
    return Array.from({length:p.N*p.rows},(_,i)=>{
        const row=Math.floor(i/p.rows),column=i%p.rows,x=p.kind==='sh'?p.pin_x:(column-(p.rows-1)/2)*p.pitch;
        return {terminal:String(i+1),center_mm:[x,((p.N-1)/2-row)*p.pitch,0],column,row,side:'contact',type:p.kind==='sh'?'smd':'tht'};
    });
}
export function createCompletionLibrary(data){
    const d=structuredClone(data),records=Object.create(null);
    if(d.schema_version!==1||!/^[a-f0-9]{64}$/.test(d.source_spec_sha256))throw new RangeError('Invalid completion data');
    for(const r of d.components){
        const p=d.profiles[r.profile_id];if(Object.hasOwn(records,r.id)||!p||!HEADER_CONNECTOR_FAMILIES.includes(p.family)||r.status==='research_required')throw new RangeError('Invalid/unimplemented record');
        if(!LODS.every(l=>r.lod_supported.includes(l)))throw new RangeError('Missing explicit LOD');
        records[r.id]=r;
    }
    return freeze({...d,records});
}
export async function loadCompletionLibrary(group='a',fetcher=globalThis.fetch){const r=await fetcher(new URL(`./data/completion-${group}.json`,import.meta.url));if(!r.ok)throw new Error('Completion library unavailable');return createCompletionLibrary(await r.json());}
export function createCompletionComponent(library,id,options={},materials=createCompletionMaterials()){
    const r=library.records[id];if(!r)throw new RangeError('Unknown component');const p=structuredClone(library.profiles[r.profile_id]);
    const allowed=['lod','N','rows','plating','pin_above','tail_below','base_height','body_height','mating_length','rear_offset','entry_direction','ramp','assembled','header_orientation'];
    if(Object.keys(options).some(k=>!allowed.includes(k)))throw new RangeError('Unsupported completion parameter');
    for(const [key,value] of Object.entries(options)){
        if(key==='lod')continue;
        if(!p.source_parameters.includes(key))throw new RangeError('Parameter not enabled by entry');
        if(key==='N'){if(!Number.isInteger(value)||value<p.n_range[0]||value>p.n_range[1])throw new RangeError('N outside supported range');p.N=value;}
        else if(key==='rows'){if(![1,2].includes(value))throw new RangeError('rows must be 1 or 2');p.rows=value;if(!p.right_angle)p.width=value*p.pitch;else p.height=value*p.pitch;}
        else if(key==='plating'){if(!['MAT_GOLD','MAT_TIN_BRIGHT'].includes(value))throw new RangeError('Unsupported plating');p.lead_material=value;}
        else if(key==='header_orientation'){if(value!=='right-angle')throw new RangeError('Vertical plug assembly coordinates are unspecified');}
        else if(key==='entry_direction'){
            if(p.kind!=='sh'||!['top','side'].includes(value))throw new RangeError('Entry variant not dimensioned');
            if(value==='top')Object.assign(p,p.top_variant);p.entry_direction=value;
        }else if(['ramp','assembled'].includes(key)){if(typeof value!=='boolean')throw new RangeError('Boolean option required');p[key]=value;}
        else {if(typeof value!=='number'||!Number.isFinite(value)||value<=0)throw new RangeError('Positive dimension required');p[({pin_above:'above',mating_length:'above',tail_below:'tail',base_height:'height',body_height:'height',rear_offset:'rear_offset'})[key]]=value;}
    }
    const lod=options.lod??'LOD1';if(!LODS.includes(lod))throw new RangeError('Invalid explicit LOD');
    const cs=completionContacts(p),g=generateHeaderConnector(p,lod,cs,materials);
    g.updateMatrixWorld(true);const b=new THREE.Box3().setFromObject(g),size=b.getSize(new THREE.Vector3());
    if([...b.min.toArray(),...b.max.toArray()].some(v=>!Number.isFinite(v)))throw new RangeError('Nonfinite bounds');
    const metadata=structuredClone(r.library_metadata);if(Object.keys(options).some(k=>k!=='lod'))metadata.uncertain_values.push('Caller parameter variant; no independent source verification.');
    g.name=id;g.userData={component_id:id,owner:id,package_family:r.package_family,package_member:r.package_member,generator:r.generator,lod,units:'mm',up_axis:'Z',origin:'FCO',contact_plane_mm:0,status:r.status,library_metadata:metadata,source:r.source,confidence:r.confidence,parameters:p,contacts:cs,terminal_count:cs.length,mating_direction:p.mating,expected_bounds_mm:{min:b.min.toArray(),max:b.max.toArray(),size:size.toArray()},expected_dimensions_mm:size.toArray(),source_spec_sha256:library.source_spec_sha256,model_source_sha256:VISUAL_SOURCE_HASH,electrical_authority:false,footprint_binding:null,implementation_status:'IMPLEMENTED'};
    g.traverse(m=>{if(m.isMesh)m.userData.component_id=id;});return g;
}
