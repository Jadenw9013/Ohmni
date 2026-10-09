// Controller study owns its finish. Library MAT_* definitions are unchanged.
import { createLandingMaterials } from '../landing-pcb-presentation.js';
import { createCompletionMaterials } from '../component-library/completion-materials.js';

export const CONTROLLER_PRESENTATION = Object.freeze({
    background: '#080d0c', exposure: .92, environmentIntensity: .42,
    keyColor: '#fff7e7', keyIntensity: 2.3, keyPosition: [-45, 90, 140],
    fillIntensity: .9, fillPosition: [65, -50, 95], hemisphereIntensity: .5,
    undersideIntensity: .12, undersideInspectionIntensity: 3.5,
    shadowMapSize: 2048, shadowExtent: 75, pixelRatioCap: 1.5, staticShadows: true,
    maskedCopperColor: '#607c39',
    studio: { background: '#535b58', panels: [
        [[-6, -4, 10], [3, 10, .2], '#fff7e6', 4],
        [[8, 5, 0], [.2, 15, 15], '#e5efef', 1.8],
        [[-8, 14, -5], [12, .2, 15], '#eef2e9', 1.8],
        [[0, 9, 10], [12, 2, .2], '#ffffff', 2.4],
    ] },
});

export const CONTROLLER_POSE = Object.freeze({ yaw: -14 * Math.PI / 180, pitch: 59 * Math.PI / 180 });

export function createControllerMaterials({ finish = true } = {}) {
    const materials = { ...createLandingMaterials({ finish }), ...createCompletionMaterials() };
    materials.mask.color.set('#073f22'); materials.mask.roughness = .8;
    materials.edge.color.set('#737050');
    materials.gold.color.set('#cbb579'); materials.gold.roughness = .36;
    materials.MAT_EPOXY_BLACK.color.set('#111416');
    materials.MAT_EPOXY_BLACK.roughness = .8;
    if(finish) {
        materials.MAT_EPOXY_BLACK.roughnessMap=materials.mask.roughnessMap;
        materials.MAT_EPOXY_BLACK.bumpMap=materials.mask.bumpMap;
        materials.MAT_EPOXY_BLACK.bumpScale=.004;
    }
    materials.MAT_TIN_MATTE.color.set('#bbc0be');
    materials.MAT_TIN_MATTE.roughness = .35;
    for (const name of ['mask','edge','gold','MAT_EPOXY_BLACK','MAT_TIN_MATTE'])
        materials[name].userData={...materials[name].userData,presentation:'controller-studio-v1',appearanceBasis:'SCENE_APPEARANCE_OVERRIDE'};
    return materials;
}
