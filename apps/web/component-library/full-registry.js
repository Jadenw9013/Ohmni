import {createLibrary,createComponent} from './registry.js';
import {createLeadedLibrary,createLeadedComponent} from './leaded-registry.js';
import {createQuadGridLibrary,createQuadGridComponent} from './quad-grid-registry.js';
import {createDiscreteLibrary,createDiscreteComponent} from './discrete-registry.js';
import {createLedPassiveLibrary,createLedPassiveComponent} from './led-passive-registry.js';
import {createCompletionLibrary,createCompletionComponent} from './completion-registry.js';
import {createCompletionMaterials} from './completion-materials.js';
import {freeze,LODS} from './validate.js';

const ADAPTERS={chip2t:[createLibrary,createComponent],leaded:[createLeadedLibrary,createLeadedComponent],'quad-grid':[createQuadGridLibrary,createQuadGridComponent],discrete:[createDiscreteLibrary,createDiscreteComponent],'led-passive':[createLedPassiveLibrary,createLedPassiveComponent],...Object.fromEntries(['a','b','c','d','e'].map(g=>['completion-'+g,[createCompletionLibrary,createCompletionComponent]]))};
export const LIBRARY_DATASETS=Object.freeze(Object.keys(ADAPTERS));
export function createFullLibrary(datasets){
    const libraries={},records=Object.create(null),owners={},hashes=new Set();
    for(const key of LIBRARY_DATASETS){if(!datasets[key])throw new RangeError('Missing dataset '+key);const library=ADAPTERS[key][0](datasets[key]);libraries[key]=library;hashes.add(library.source_spec_sha256);
        for(const [id,record] of Object.entries(library.records)){
            if(Object.hasOwn(records,id))throw new RangeError('Duplicate ID '+id);
            if(!record.package_family||!record.package_member||!record.generator||!LODS.every(l=>record.lod_supported.includes(l)))throw new RangeError('Incomplete entry '+id);
            if(record.library_metadata.implementation_status!=='IMPLEMENTED')throw new RangeError('Missing implementation flag '+id);
            records[id]=record;owners[id]=key;
        }
    }
    const expected=Array.from({length:180},(_,i)=>`OHM-${String(i+1).padStart(3,'0')}`);
    if(hashes.size!==1||JSON.stringify(Object.keys(records).sort())!==JSON.stringify(expected))throw new RangeError('Library must cover exactly OHM-001..180 from one spec revision');
    const sorted=Object.fromEntries(expected.map(id=>[id,records[id]]));
    return freeze({libraries,records:sorted,owners,components:Object.values(sorted),source_spec_sha256:[...hashes][0]});
}
export async function loadFullLibrary(fetcher=globalThis.fetch){const entries=await Promise.all(LIBRARY_DATASETS.map(async key=>{const response=await fetcher(new URL(`./data/${key}.json`,import.meta.url));if(!response.ok)throw new Error('Missing '+key);return [key,await response.json()];}));return createFullLibrary(Object.fromEntries(entries));}
export function createFullComponent(library,id,options={},materials=createCompletionMaterials()){
    const owner=library.owners[id];if(!owner)throw new RangeError('Unknown library component');
    const model=ADAPTERS[owner][1](library.libraries[owner],id,options,materials);
    model.userData.implementation_status='IMPLEMENTED';model.userData.library_dataset=owner;
    // Completion models participate in the same revision-bound binding adapter.
    model.userData.model_asset_id??=`ohmni-component-library/${id}@completion-v1`;
    return model;
}
export function libraryCoverage(library){return library.components.map(r=>({entry:r.id,family:r.package_family,member:r.package_member,generator:r.generator,lod:r.lod_supported,source_status:r.status,implementation:r.library_metadata.implementation_status,provisional:r.library_metadata.provisional}));}
