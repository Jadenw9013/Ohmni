import * as THREE from '../vendor/three.module.js';

// Only tokens needed by Stage 5. Section 17 colors override older group proposals.
// Parametric sleeve/lacquer colors below are explicitly OHMNI appearance defaults.
export const STAGE5_MATERIAL_ADDITIONS = Object.freeze({
    MAT_GOLD: ['#D4A84B', .25, 1],
    MAT_STEEL_STAINLESS: ['#B5B7B9', .3, 1],
    MAT_ALUMINUM_CAN: ['#BEBFC2', .35, 1],
    MAT_PLASTIC_BLACK: ['#151517', .5, 0],
    MAT_PLASTIC_WHITE: ['#EDEDE8', .5, 0],
    MAT_PLASTIC_CLEAR: ['#FFFFFF', .05, 0],
    MAT_PLASTIC_DIFFUSED: ['#FF2A1A', .2, 0],
    MAT_PVC_SLEEVE_BLACK: ['#171719', .45, 0],
    MAT_PVC_SLEEVE_BLUE: ['#214C89', .45, 0],
    MAT_RUBBER_SEAL: ['#1A1A1A', .8, 0],
    MAT_CAP_DISC_COATING: ['#C8782A', .5, 0],
    MAT_FILM_CASE_RED: ['#B3261E', .45, 0],
    MAT_MICA_DIP: ['#B5651D', .55, 0],
    MAT_RESISTOR_PAINT_BEIGE: ['#D8C7A3', .6, 0],
    MAT_RESISTOR_PAINT_BLUE: ['#6FA3C7', .55, 0],
    MAT_RESISTOR_PAINT_GREEN: ['#4F7A4A', .6, 0],
    MAT_COIL_COAT: ['#4F7A4A', .45, 0],
    MAT_MCPCB_MASK_WHITE: ['#EDEDE8', .5, 0],
    ...Object.fromEntries(Object.entries({BLACK:'#111111',BROWN:'#6B3A1E',RED:'#C0281E',ORANGE:'#E8751A',YELLOW:'#E8C81A',GREEN:'#2E8B3E',BLUE:'#2756B8',VIOLET:'#7A3FA0',GRAY:'#8C8C8C',WHITE:'#F2F2F0',GOLD:'#C9A23A',SILVER:'#BFC1C4'}).map(([name,color])=>[`MAT_BAND_${name}`,[color,.5,0]])),
});

// Specification §7 and G02. All colors are authored sRGB appearance defaults.
export const MATERIAL_TOKENS = Object.freeze(Object.fromEntries(Object.entries({
    ...STAGE5_MATERIAL_ADDITIONS,
    MAT_CERAMIC_ALUMINA_WHITE: ['#E9E6DC', 0.7, 0],
    MAT_RESISTOR_COAT_BLACK: ['#17171A', 0.4, 0],
    MAT_MLCC_BROWN: ['#8C6A45', 0.6, 0],
    MAT_MLCC_GRAY: ['#8F8F88', 0.6, 0],
    MAT_TIN_MATTE: ['#A9ACAF', 0.5, 1],
    MAT_TIN_BRIGHT: ['#BFC1C4', 0.35, 1],
    MAT_EPOXY_BLACK: ['#1B1B1D', 0.55, 0],
    MAT_EPOXY_DARKGRAY: ['#2E2F33', 0.55, 0],
    MAT_SOLDER_BALL: ['#B7B9BC', 0.35, 1],
    MAT_COPPER: ['#B87333', 0.4, 1],
    MAT_NICKEL: ['#A8A9AD', 0.3, 1],
    MAT_DIODE_GLASS_AMBER: ['#A5561E', 0.12, 0],
    MAT_DIODE_BAND_SILVER: ['#D2D2CE', 0.5, 0],
    MAT_DIODE_BAND_BLACK: ['#0B0B0C', 0.5, 0],
    MAT_BGA_SUBSTRATE: ['#2F4F3A', 0.5, 0],
    MAT_FERRITE_DARK: ['#2B2B2D', 0.6, 0],
    MAT_SILKSCREEN_WHITE: ['#F2F2F0', 0.7, 0],
    MAT_ALLOY_MANGANIN: ['#8A6F55', 0.4, 1],
}).map(([name, values]) => [name, Object.freeze(values)])));

// Owned by one scene. Do not cache these globally or mutate per instance.
export function createLibraryMaterials() {
    return Object.fromEntries(Object.entries(MATERIAL_TOKENS).map(([name, [color, roughness, metalness]]) => {
        const material = new THREE.MeshStandardMaterial({ name, color, roughness, metalness });
        if (name === 'MAT_DIODE_GLASS_AMBER') { material.transparent = true; material.opacity = 0.85; }
        if (['MAT_PLASTIC_CLEAR','MAT_PLASTIC_DIFFUSED'].includes(name)) {
            material.transparent = true; material.opacity = name === 'MAT_PLASTIC_CLEAR' ? .3 : .78;
            material.depthWrite = false; // Still raycastable: transparency never removes pick geometry.
        }
        material.userData = { token: name, appearanceBasis: 'OHMNI_DEFAULT',
            provisional: ['MAT_ALLOY_MANGANIN','MAT_BGA_SUBSTRATE'].includes(name) };
        return [name, material];
    }));
}
