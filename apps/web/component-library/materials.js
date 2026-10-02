import * as THREE from '../vendor/three.module.js';

// Specification §7 and G02. All colors are authored sRGB appearance defaults.
export const MATERIAL_TOKENS = Object.freeze(Object.fromEntries(Object.entries({
    MAT_CERAMIC_ALUMINA_WHITE: ['#E9E6DC', 0.7, 0],
    MAT_RESISTOR_COAT_BLACK: ['#17171A', 0.4, 0],
    MAT_MLCC_BROWN: ['#8C6A45', 0.6, 0],
    MAT_MLCC_GRAY: ['#8F8F88', 0.6, 0],
    MAT_TIN_MATTE: ['#A9ACAF', 0.5, 1],
    MAT_TIN_BRIGHT: ['#BFC1C4', 0.35, 1],
    MAT_EPOXY_BLACK: ['#1B1B1D', 0.55, 0],
    MAT_FERRITE_DARK: ['#2B2B2D', 0.6, 0],
    MAT_SILKSCREEN_WHITE: ['#F2F2F0', 0.7, 0],
    MAT_ALLOY_MANGANIN: ['#8A6F55', 0.4, 1],
}).map(([name, values]) => [name, Object.freeze(values)])));

// Owned by one scene. Do not cache these globally or mutate per instance.
export function createLibraryMaterials() {
    return Object.fromEntries(Object.entries(MATERIAL_TOKENS).map(([name, [color, roughness, metalness]]) => {
        const material = new THREE.MeshStandardMaterial({ name, color, roughness, metalness });
        material.userData = { token: name, appearanceBasis: 'OHMNI_DEFAULT',
            provisional: name === 'MAT_ALLOY_MANGANIN' };
        return [name, material];
    }));
}
