// Scene-owned appearance only. No shared library MAT tokens or source dimensions change.
import { createMaterials } from './visual-assets.js';
import * as THREE from './vendor/three.module.js';

export const LANDING_PRESENTATION = Object.freeze({
    background: '#030810', exposure: 0.95, environmentIntensity: 0.65,
    keyColor: '#fff7ee', keyIntensity: 2.2, keyPosition: Object.freeze([-55, 90, 130]),
    fillIntensity: 0.65, fillPosition: Object.freeze([80, -35, 70]),
    hemisphereIntensity: 0.35, undersideIntensity: 0.15, undersideInspectionIntensity: 3.5,
    shadowMapSize: 1024, shadowExtent: 65, pixelRatioCap: 1.5, staticShadows: true,
    maskedCopperColor: '#3b6146',
    studio: Object.freeze({ background: '#424b54', panels: Object.freeze([
        [[-6, -4, 10], [3, 10, .2], '#fffaf4', 4],
        [[8, 5, 0], [.2, 15, 15], '#e7efff', 1.5],
        [[-8, 14, -5], [12, .2, 15], '#eef2f5', 1.4],
        [[0, 9, 10], [12, 2, .2], '#ffffff', 2],
    ]) }),
});

// +Y faces the saved USB opening. The old scene's default view hid that opening.
export const LANDING_POSE = Object.freeze({ yaw: -150 * Math.PI / 180, pitch: 40 * Math.PI / 180 });

function finishTexture(brushed) {
    const size = 128, pixels = new Uint8Array(size * size * 4);
    let state = 19417;
    const random = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state / 2 ** 32; };
    for (let y = 0; y < size; y++) {
        const row = random();
        for (let x = 0; x < size; x++) {
            const value = Math.round(205 + (brushed ? row * 32 + random() * 12 : random() * 44));
            const index = (y * size + x) * 4;
            pixels.set([value, value, value, 255], index);
        }
    }
    const texture = new THREE.DataTexture(pixels, size, size);
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.minFilter = THREE.LinearMipmapLinearFilter; texture.magFilter = THREE.LinearFilter;
    texture.generateMipmaps = true; texture.needsUpdate = true;
    texture.repeat.set(brushed ? .8 : 1.6, brushed ? .8 : 1.6);
    texture.name = brushed ? 'deterministic illustrative brushed finish' : 'deterministic illustrative mask finish';
    texture.userData.appearanceOnly = true;
    return texture;
}

export function createLandingMaterials({ finish = true } = {}) {
    const materials = createMaterials();
    for (const [key, color, roughness] of [
        ['mask', '#2f4f3a', 0.6], ['trace', '#385c43', 0.58],
        ['edge', '#62563b', 0.86], ['shield', '#a9acaf', 0.28],
        ['aluminum', '#b5b8ba', 0.42], ['lead', '#b9bdc0', 0.33],
        ['resin', '#262727', 0.76], ['plastic', '#151919', 0.64],
        ['tan', '#b39a70', 0.68], ['gold', '#b6a166', 0.36],
    ]) {
        materials[key].color.set(color);
        materials[key].roughness = roughness;
        materials[key].userData.presentation = 'landing-studio-v1';
    }
    if (finish) {
        const metal = finishTexture(true), mask = finishTexture(false);
        materials.shield.roughnessMap = metal; materials.shield.bumpMap = metal; materials.shield.bumpScale = .009;
        materials.mask.roughnessMap = mask; materials.mask.bumpMap = mask; materials.mask.bumpScale = .006;
        // The sensor cap deliberately has no brushed finish; it uses its own roughness.
    }
    return materials;
}
