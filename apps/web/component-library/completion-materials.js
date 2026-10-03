import * as THREE from '../vendor/three.module.js';
import { createLibraryMaterials } from './materials.js';

// Approved materials.js entries are reused unchanged. Running completion additions.
export const COMPLETION_MATERIAL_ADDITIONS=Object.freeze({
    MAT_PLASTIC_NATURAL: Object.freeze(['#DCCFB0',.5,0]), // Spec section 7
    MAT_PLASTIC_GREEN_TERM: Object.freeze(['#2E8B3E',.5,0]), // G11 proposal
    MAT_CERAMIC_PKG_TAN: Object.freeze(['#C9C0A8',.6,0]), // G10
    MAT_RESONATOR_COAT_BLUE: Object.freeze(['#5F86B4',.5,0]), // G10
    MAT_CERAMIC_CORE_BEIGE: Object.freeze(['#D9CBA8',.7,0]), // G04
    MAT_MOLDED_COMPOSITE_DARK: Object.freeze(['#26272A',.6,0]),
    MAT_WIRE_ENAMEL_COPPER: Object.freeze(['#B8733A',.35,.6]), // Section17.5 color overrides G04
    MAT_HEATSHRINK_BLACK: Object.freeze(['#17171A',.5,0]),
    MAT_TAPE_POLYESTER_YELLOW: Object.freeze(['#D9B73A',.4,0]),
    MAT_PLASTIC_BLUE: Object.freeze(['#1E5AA8',.45,0]), // G02
    MAT_BRASS: Object.freeze(['#C9A24A',.35,1]),
    MAT_LED_FACE_GRAY: Object.freeze(['#6B6B6B',.6,0]), // G10
    MAT_LED_SEGMENT_WHITE: Object.freeze(['#EDEDE8',.4,0]),
    MAT_LCD_POLARIZER_GRAY: Object.freeze(['#7F8C7C',.3,0]),
    MAT_OLED_PANEL_BLACK: Object.freeze(['#08080A',.15,0]),
    MAT_FR4_GREEN: Object.freeze(['#2F4F3A',.5,0]), // Section7 variable; provisional hue borrowed from BGA substrate
    MAT_FR4_BLUE: Object.freeze(['#1E5AA8',.5,0]), // Section7 variable; provisional hue borrowed from plastic blue
    MAT_GLASS: Object.freeze(['#CFE0E8',.05,0]), // Section7
});
export function createCompletionMaterials(){
    const materials=createLibraryMaterials();
    for(const [token,[color,roughness,metalness]] of Object.entries(COMPLETION_MATERIAL_ADDITIONS)){
        const m=new THREE.MeshStandardMaterial({name:token,color,roughness,metalness});m.userData={token,appearanceBasis:'SPEC_VISUAL_DEFAULT'};materials[token]=m;
        if(token==='MAT_GLASS'||token==='MAT_LED_SEGMENT_WHITE'){m.transparent=true;m.opacity=token==='MAT_GLASS'?.2:.85;m.depthWrite=false;}
    }
    return materials;
}
