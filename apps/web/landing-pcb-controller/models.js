// Real package generators; exact component/footprint identities remain in the input.
// The display adapter has already converted the complete board to Y-up.
// These bindings target those normalized footprint coordinates.
import * as THREE from '../vendor/three.module.js';
import { createAsset } from '../visual-assets.js';
import { createLibrary, createComponent } from '../component-library/registry.js';
import { createLeadedLibrary, createLeadedComponent } from '../component-library/leaded-registry.js';
import { createQuadGridLibrary } from '../component-library/quad-grid-registry.js';
import { perimeterLayout } from '../component-library/quad-grid-layout.js';
import { generateQuadGrid } from '../component-library/generators/quad-grid.js';
import { createLedPassiveLibrary } from '../component-library/led-passive-registry.js';
import { ledPassiveContacts } from '../component-library/led-passive-layout.js';
import { generateLedPassive } from '../component-library/generators/led-passive.js';
import { createCompletionLibrary, createCompletionComponent } from '../component-library/completion-registry.js';

const DATASETS = ['chip2t', 'leaded', 'quad-grid', 'led-passive', 'completion-a'];
export function createControllerLibraries(data) {
    return { chip: createLibrary(data.chip2t), leaded: createLeadedLibrary(data.leaded),
        quad: createQuadGridLibrary(data['quad-grid']), led: createLedPassiveLibrary(data['led-passive']),
        header: createCompletionLibrary(data['completion-a']) };
}
export async function loadControllerLibraries(fetcher = globalThis.fetch) {
    const data = await Promise.all(DATASETS.map(async name => {
        const response = await fetcher(new URL(`../component-library/data/${name}.json`, import.meta.url));
        if (!response.ok) throw new Error(`Package data unavailable: ${name}`);
        return [name, await response.json()];
    }));
    return createControllerLibraries(Object.fromEntries(data));
}

export const STM32_PACKAGE = Object.freeze({
    body_x: 14, body_y: 14, body_thickness: 1.4, height: 1.5, source_height: 1.6,
    standoff: .1, lead_span: 16, pitch: .5, lead_width: .22, lead_thickness: .145, foot_length: .6,
    source: 'ST DS5319 Rev20 Table56, printed page88: https://www.st.com/resource/en/datasheet/stm32f103vb.pdf',
    uncertainty: 'Standoff 0.1 and lead thickness 0.145 are explicit range midpoints; dimple, draft and finish remain cosmetic.',
});

function qfp(libraries, materials, lod) {
    const record = libraries.quad.records['OHM-125'];
    const p = { ...structuredClone(libraries.quad.profiles[record.profile_id]), ...STM32_PACKAGE };
    const contacts = perimeterLayout(p);
    const group = generateQuadGrid(record, p, lod, 'STM32F103', contacts, materials);
    group.userData = { component_id: 'STM32F103VBT6', lod, contacts, terminal_count: contacts.length,
        model_asset_id: 'ohmni/controller-stm32f103vbt6-lqfp100@1', parameters: p,
        source: STM32_PACKAGE.source, library_generator: 'GEN-QUAD_GULLWING',
        geometryClaim: 'Manufacturer nominal LQFP100 envelope; cosmetic details provisional',
        library_metadata: { provisional: true, uncertain_values: [STM32_PACKAGE.uncertainty] } };
    return group;
}

function indicator(libraries, materials, lod) {
    const p = structuredClone(libraries.led.profiles['OHM-078']);
    // Kingbright APT1608SGC is 0.75 mm high, unlike OHM-078's 0.55 mm default.
    // Reuse the chip terminal-band generator with a separate source-backed body.
    p.body_h = .75; p.lens = 'clear'; p.led_color = '#70bc69';
    const contacts = ledPassiveContacts(p);
    const group = generateLedPassive(p, lod, '', contacts, materials, libraries.led.profiles);
    group.userData = { component_id: 'APT1608SGC', lod, contacts, terminal_count: 2,
        parameters: p, model_asset_id: 'ohmni/controller-apt1608sgc@1',
        source: 'Kingbright APT1608SGC mechanical drawing, page1',
        geometryClaim: 'Manufacturer 1.6 × 0.8 × 0.75 mm envelope; lens inset and contact band cosmetic',
        library_metadata: { provisional: true, uncertain_values: ['Lens inset, internal emitter and terminal band use the library appearance defaults.'] } };
    return group;
}

function resetSwitch(pads, materials) {
    const g=new THREE.Group();
    const box=(name,w,d,h,x,y,z,material)=>{
        const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,d,h),material);
        mesh.name=name;mesh.position.set(x,y,z);g.add(mesh);return mesh;
    };
    box('B3F-1000 6 mm body',6,6,3.25,0,0,1.625,materials.MAT_PLASTIC_BLACK);
    // Omron page4 gives the 3.4 mm platform and 4.3 mm overall height.
    box('switch cover',5.6,5.6,.15,0,0,3.325,materials.MAT_STEEL_STAINLESS);
    const actuator=new THREE.Mesh(new THREE.CylinderGeometry(1.75,1.75,.9,32),materials.MAT_PLASTIC_NATURAL);
    actuator.name='3.5 mm ivory actuator';actuator.rotation.x=Math.PI/2;actuator.position.z=3.85;g.add(actuator);
    for(const pad of pads.filter(p=>p.kind==='thru_hole')) {
        box('source-position switch tail',.3,.7,4.5,pad.x_mm,pad.y_mm,-1.25,materials.MAT_TIN_MATTE);
        const x=Math.sign(pad.x_mm)*2.8,span=Math.abs(pad.x_mm-x)+.3;
        box('switch lead shoulder',span,.7,.3,(pad.x_mm+x)/2,pad.y_mm,1,materials.MAT_TIN_MATTE);
    }
    g.userData={model_asset_id:'ohmni/controller-b3f1000@1',source:'Omron B3F datasheet, pages1 and4',
        sourceContacts:pads.filter(p=>p.kind==='thru_hole').map(p=>({number:p.number,x_mm:p.x_mm,y_mm:p.y_mm})),
        geometryClaim:'Sourced 6 × 6 × 4.3 mm envelope, 3.5 mm actuator and .7 × .3 mm leads; source-position tails',
        library_metadata:{provisional:true,uncertain_values:['5.6 mm inset cover and internal shoulder transition are cosmetic.']}};
    return g;
}

/** Explicit identities only. An unfamiliar component fails closed. */
export function controllerBinding(part) {
    const id = part.part_id, footprint = part.footprint_id;
    const common = { rotation_deg: 0, mirror_x: false, mirror_y: false, translation_mm: [0, 0, 0] };
    if (id === 'STM32F103VBT6') return { ...common, kind: 'stm32' };
    if (id === 'SN74HC595D') return { ...common, kind: 'leaded', library_id: 'OHM-112', marking: '74HC595' };
    if (id === '25LC256-I/SN') return { ...common, kind: 'leaded', library_id: 'OHM-110', marking: '25LC256' };
    if (id === 'AP2112K-3.3TRG1') return { ...common, kind: 'leaded', library_id: 'OHM-120', rotation_deg: -90 };
    if (id === 'APT1608SGC') return { ...common, kind: 'led' };
    if (/R_0805/.test(footprint)) return { ...common, kind: 'chip', library_id: 'OHM-005' };
    if (/R_0603/.test(footprint)) return { ...common, kind: 'chip', library_id: 'OHM-004' };
    if (/C_0805/.test(footprint)) return { ...common, kind: 'chip', library_id: 'OHM-024' };
    if (/C_0603/.test(footprint)) return { ...common, kind: 'chip', library_id: 'OHM-023' };
    if (/TSW-120-07-G-D/.test(id) || /PinHeader_2x20/.test(footprint))
        return { ...common, kind: 'header', library_id: 'OHM-151', options: { N: 20, pin_above:5.84,tail_below:2.54,base_height:2.54 },
            source:'Samtec TSW catalog page1, straight-pin -07: https://suddendocs.samtec.com/catalog_english/tsw_th.pdf' };
    if (/HEADER_1X6|TSW-106/.test(id) || /PinHeader_1x06/.test(footprint))
        return { ...common, kind: 'header', library_id: 'OHM-150', options: { N: 6, pin_above:5.84,tail_below:2.54,base_height:2.54 },
            source:'Samtec TSW catalog page1, straight-pin -07: https://suddendocs.samtec.com/catalog_english/tsw_th.pdf' };
    if (id === 'USB_C_RECEPTACLE_16P' || id === 'TYPE-C-31-M-12') return { ...common, kind: 'source-pad-package', family: 'usb_c', rotation_deg:180 };
    if (id === 'B3F-1000') return { ...common, kind: 'b3f1000' };
    if (id === 'GENERIC_MOMENTARY_BUTTON') return { ...common, kind: 'source-pad-package', family: 'switch' };
    throw new Error(`No declared controller package binding: ${id} (${footprint})`);
}

export function transformContact(contact, binding) {
    const angle = binding.rotation_deg * Math.PI / 180;
    const x = contact[0] * (binding.mirror_x ? -1 : 1), y = contact[1] * (binding.mirror_y ? -1 : 1);
    return [x * Math.cos(angle) - y * Math.sin(angle) + binding.translation_mm[0],
        x * Math.sin(angle) + y * Math.cos(angle) + binding.translation_mm[1], contact[2] + binding.translation_mm[2]];
}

function contactProjection(contact,binding) {
    const projected={...contact,terminal:binding.terminal_to_pad?.[contact.terminal]??contact.terminal,
        center_mm:transformContact(contact.center_mm,binding)};
    if(contact.size_mm){
        const a=binding.rotation_deg*Math.PI/180,[w,h]=contact.size_mm;
        projected.canonical_size_mm=[w,h];
        projected.size_mm=[Math.abs(Math.cos(a))*w+Math.abs(Math.sin(a))*h,
            Math.abs(Math.sin(a))*w+Math.abs(Math.cos(a))*h];
    }
    return projected;
}

export function createControllerModelResolver(source, libraries) {
    const parts = new Map(source.board.components.map(part => [part.ref, part]));
    return (instance, materials) => {
        const part = parts.get(instance.id);
        if (!part || part.footprint_id !== instance.sourceFootprintId)
            throw new Error(`Model/source identity mismatch: ${instance.id}`);
        const binding = { ...controllerBinding(part), ...(source.model_bindings?.[part.ref] ?? {}) };
        const lod = binding.options?.lod ?? 'LOD2';
        let model;
        if (binding.kind === 'stm32') model = qfp(libraries, materials, lod);
        else if (binding.kind === 'led') model = indicator(libraries, materials, lod);
        else if (binding.kind === 'chip') model = createComponent(libraries.chip, binding.library_id, { lod, ...binding.options }, materials);
        else if (binding.kind === 'leaded') model = createLeadedComponent(libraries.leaded, binding.library_id,
            { lod, marking_text: binding.marking ?? '', ...binding.options }, materials);
        else if (binding.kind === 'header') model = createCompletionComponent(libraries.header, binding.library_id,
            { lod, ...binding.options }, materials);
        else if (binding.kind === 'b3f1000') model = resetSwitch(part.pads,materials);
        else if (binding.kind === 'source-pad-package') {
            const dimensions=binding.family==='usb_c'?{width:8.94,depth:7.35,height:3.16}:{};
            // The USB factory's opening is +Y; the normalized south-edge port
            // opens −Y. Rotate its shell, while inverse-transforming the source
            // contacts so their final position stays exactly on the source pads.
            const pads=binding.family==='usb_c'?part.pads.map(pad=>({...pad,x_mm:-pad.x_mm,y_mm:-pad.y_mm})):part.pads;
            model = createAsset(binding.family, { ...instance.options, ...dimensions, pads, label: false }, materials);
            model.userData.geometryClaim = 'Source-pad-derived package approximation; exact body fit is not established';
            if(binding.family==='usb_c') {
                model.userData.geometryClaim='HRO sourced 8.94 × 7.35 × 3.16 mm envelope; source pad positions; centered shell datum corroborated by KiCad F.Fab';
                model.userData.library_metadata={provisional:true,uncertain_values:[
                    'Shell walls, tongue and window details are cosmetic approximations.',
                    'HRO nominal shell length 7.35 mm differs from the installed KiCad F.Fab length 7.30 mm by 0.05 mm; the nominal envelope is centered, giving a 0.025 mm difference at each end.',
                    'Centered shell datum uses installed KiCad10 F.Fab secondary geometry (SHA256 8d292db4e16dbd391bfc6c79366047ce1799e687d970810736a41426e88619b3), not a manufacturer datum drawing. Plug mating clearance remains unverified.',
                ]};
            }
            model.userData.model_asset_id = `ohmni/controller-source-pad/${binding.family}@1`;
        } else throw new Error(`Unsupported controller binding: ${binding.kind}`);
        if(part.part_id==='GRM21BR71A106KE51L') {
            const metadata=model.userData.library_metadata??{};
            model.userData.library_metadata={...metadata,provisional:true,uncertain_values:[
                ...(metadata.uncertain_values??[]),
                'Exact Murata nominal body height was not established. The generic 0805 library height is an appearance approximation, not a sourced nominal dimension for this MPN.',
            ]};
        }
        // A handedness conversion belongs to contacts and package features. Do
        // not accidentally turn the separate, cosmetic identity decal into
        // mirrored lettering when converting the KiCad footprint frame.
        if (binding.mirror_x !== binding.mirror_y) model.traverse(node => {
            if (node.userData.content) node.scale.x *= -1;
        });
        model.position.set(...binding.translation_mm);
        model.rotation.z = binding.rotation_deg * Math.PI / 180;
        model.scale.set(binding.mirror_x ? -1 : 1, binding.mirror_y ? -1 : 1, 1);
        // Library previews own models by OHM ID. In a PCB the selectable owner
        // must be the unique circuit reference assigned by VisualRenderer.
        model.traverse(node => {
            if (node.userData.owner) { node.userData.library_owner = node.userData.owner; delete node.userData.owner; }
        });
        const wrapper = new THREE.Group(); wrapper.add(model);
        wrapper.userData = { sourceComponent: part.ref, lod, package_binding: binding, model_asset_id: model.userData.model_asset_id,
            geometryClaim: model.userData.geometryClaim ?? 'Library package geometry with explicit footprint transform; no manufacturing-fit claim',
            contacts: (model.userData.contacts ?? []).map(contact => contactProjection(contact,binding)),
            source_pad_contacts:(model.userData.sourceContacts??[]).map(c=>({number:c.number,
                center_mm:transformContact([c.x_mm,c.y_mm,0],binding),basis:'SOURCE_PAD_DERIVED_VISUAL_CONTACT'})),
            terminal_count: model.userData.terminal_count ?? null, model_metadata: model.userData };
        wrapper.traverse(node => { if (node.isMesh) { node.castShadow = true; node.receiveShadow = true; } });
        return wrapper;
    };
}
