import * as THREE from '../vendor/three.module.js';
import { createLibraryMaterials } from './materials.js';

// Approved materials.js entries are reused unchanged. Running completion additions.
export const COMPLETION_MATERIAL_ADDITIONS=Object.freeze({
    MAT_PLASTIC_NATURAL: Object.freeze(['#DCCFB0',.5,0]), // Spec section 7
    MAT_PLASTIC_GREEN_TERM: Object.freeze(['#2E8B3E',.5,0]), // G11 proposal
});
export function createCompletionMaterials(){
    const materials=createLibraryMaterials();
    for(const [token,[color,roughness,metalness]] of Object.entries(COMPLETION_MATERIAL_ADDITIONS)){
        const m=new THREE.MeshStandardMaterial({name:token,color,roughness,metalness});m.userData={token,appearanceBasis:'SPEC_VISUAL_DEFAULT'};materials[token]=m;
    }
    return materials;
}
