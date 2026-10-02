import * as THREE from '../../vendor/three.module.js';
import { loadLibrary, createComponent } from '../registry.js';
import { ModelPreview } from './model-preview.js';
import { createLibraryMaterials } from '../materials.js';
import { loadLeadedLibrary, createLeadedComponent } from '../leaded-registry.js';
import { loadDiscreteLibrary, createDiscreteComponent } from '../discrete-registry.js';
import { loadQuadGridLibrary, createQuadGridComponent } from '../quad-grid-registry.js';

const $ = id => document.getElementById(id);
try {
    const stage2 = new URL(location.href).searchParams.get('stage') === '2';
    const stage4 = new URL(location.href).searchParams.get('stage') === '4';
    const stage3 = new URL(location.href).searchParams.get('stage') === '3';
    const library = await (stage4 ? loadDiscreteLibrary() : stage3 ? loadQuadGridLibrary() : stage2 ? loadLeadedLibrary() : loadLibrary());
    const build = stage4 ? createDiscreteComponent : stage3 ? createQuadGridComponent : stage2 ? createLeadedComponent : createComponent;
    const reviewIds = stage4 ? ['OHM-057','OHM-059','OHM-061','OHM-065','OHM-093','OHM-098','OHM-100','OHM-096','OHM-071'] : stage3 ? ['OHM-123','OHM-130','OHM-133','OHM-135','OHM-137','OHM-140'] : stage2 ? ['OHM-104','OHM-110','OHM-116','OHM-119','OHM-094','OHM-120'] : ['OHM-004','OHM-023','OHM-041'];
    if (stage2) {
        document.title = 'Ohmni · Component library / Stage 2';
        document.querySelector('header > p').textContent = 'COMPONENT LIBRARY · STAGE 2';
        document.querySelector('h1').textContent = 'Six families. Twenty-one entries.';
        document.querySelector('#comparison h2').textContent = 'Stage 2 review set · same scale';
        document.querySelector('#comparison .caption p').textContent = 'DIP-8 · SOIC-8 · TSSOP-16 · MSOP-8 · SOT-23-3 · SOT-23-5 / LOD1';
        document.querySelector('#comparison > p').textContent = 'Left to right in the order above. All six models share one orthographic camera and millimetre scale.';
        $('comparison-image').alt = 'Six review models at the same physical scale';
        document.querySelector('#sheet h2').textContent = 'Stage 2 · all 21 specified entries';
        document.querySelector('footer').textContent = 'GEN-DUAL_GULLWING · GEN-SMD_POWER / SOT23 · GEN-DIP · mm · FCO · Z up · no pads or solder';
    }
    if (stage3) {
        document.title = 'Ohmni · Component library / Stage 3';
        document.querySelector('header > p').textContent = 'COMPONENT LIBRARY · STAGE 3';
        document.querySelector('h1').textContent = 'Six families. Nineteen entries.';
        document.querySelector('#comparison h2').textContent = 'Stage 3 review set · same scale';
        document.querySelector('#comparison .caption p').textContent = 'TQFP-44 · QFN-32 · DFN-8 · PLCC-28 · BGA-100 · WLCSP-16 / LOD1';
        document.querySelector('#comparison > p').textContent = 'Left to right in the order above. All six models share one orthographic camera and millimetre scale.';
        $('comparison-image').alt = 'Six Stage 3 review models at the same physical scale';
        document.querySelector('#sheet h2').textContent = 'Stage 3 · all 19 specified entries';
        document.querySelector('footer').textContent = 'QUAD GULL-WING · LEADLESS · J-LEAD · BALL GRID · mm · FCO · Z up · no footprint binding';
    }
    if (stage4) {
        document.title = 'Ohmni · Component library / Stage 4';
        document.querySelector('header > p').textContent = 'COMPONENT LIBRARY · STAGE 4';
        document.querySelector('h1').textContent = 'Diodes and power. Twenty-five entries.';
        document.querySelector('#comparison h2').textContent = 'Stage 4 review set · same scale';
        document.querySelector('#comparison .caption p').textContent = 'DO-41 · MiniMELF · SOD-123 · SMB · TO-92 · TO-220 · DPAK · SOT-223 · DIP bridge / LOD1';
        document.querySelector('#comparison > p').textContent = 'Left to right in the order above. All nine models share one orthographic camera and millimetre scale. THT bounds include tails below Z=0.';
        $('comparison-image').alt = 'Nine Stage 4 review models at the same physical scale';
        document.querySelector('#sheet h2').textContent = 'Stage 4 · all 25 specified entries';
        document.querySelector('footer').textContent = 'AXIAL · MELF · SOD / SMX · BRIDGES · TRANSISTORS / POWER · mm · FCO · Z up · no footprint binding';
    }
    const preview = new ModelPreview($('model'));
    const scratch = new ModelPreview(document.createElement('canvas'));
    const ids = Object.keys(library.records);
    for (const id of ids) {
        const option = document.createElement('option'); option.value = id;
        option.textContent = `${id} · ${library.records[id].canonical_name}`; $('component').append(option);
    }
    function show(id = $('component').value, lod = $('lod').value, view = $('view').value, options = {}) {
        const record = library.records[id];
        // A supplied value code demonstrates decal support, not an electrical claim.
        const model = build(library, id, { ...options, lod, ...((stage2 || stage3 || stage4) ? { marking_text: id.replace('-','') } : id === 'OHM-004' ? { marking_text: '100' } : {}) });
        preview.setModel(model);
        const stats = preview.renderView(view, { width: 1000, height: 500, sideAxis: record.package_family === 'PKG-SOT23' ? 'X' : 'Y' });
        $('component').value = id; $('lod').value = lod; $('view').value = view;
        $('name').textContent = `${id} · ${record.canonical_name}${options.terminal_pullback ? ' · DEMO: 0.05 mm pullback' : options.outline ? ' · outline '+options.outline : options.bidirectional ? ' · bidirectional (no band)' : ''}`;
        $('dimensions').textContent = `${model.userData.expected_dimensions_mm.map(n => +n.toFixed(4)).join(' × ')} mm · ${lod} · ${view} · ${stats.triangles} triangles`;
        $('status').textContent = `${record.library_metadata.provisional ? 'PROVISIONAL · ' : ''}Source status: ${record.status}. Appearance: OHMNI defaults, confidence ${record.confidence.materials_appearance}. No exact footprint bound.${id === 'OHM-004' ? ' “100” is demonstration text only.' : ''}`;
        if (stage2 || stage3 || stage4) $('status').textContent += ` ${record.library_metadata.conflicts.length ? 'Spec conflicts recorded below. ' : ''}OHM text is a library ID decal, not a manufacturer marking.`;
        if (options.terminal_pullback) $('status').textContent += ' PROVISIONAL PARAMETER DEMONSTRATION: source defaults remain flush (0 mm pullback).';
        if (stage4 && record.package_family.startsWith('PKG-BRIDGE')) $('status').textContent += ' Bridge symbols are unverified visual placeholders; pin functions remain UNKNOWN.';
        $('notes').textContent = [record.source.document, `Entry line ${record.source.line}`, ...record.library_metadata.uncertain_values,
            ...(record.library_metadata.conflicts ?? []).map(c => JSON.stringify(c, null, 2)),
            record.source.sections.Sources].join('\n\n');
        return { ...stats, component_id: id, bounds_mm: model.userData.expected_dimensions_mm,
            source_status: record.status, provisional: model.userData.library_metadata.provisional, parameters: options };
    }
    const comparison = new THREE.Group(), materials = createLibraryMaterials();
    for (const [i, id] of reviewIds.entries()) {
        const model = build(library, id, { lod: 'LOD1', ...((stage2 || stage3 || stage4) ? {marking_text:id.replace('-','')} : i === 0 ? { marking_text: '100' } : {}) }, materials);
        model.position.x = (i - (reviewIds.length - 1) / 2) * (stage4 ? 15 : stage3 ? 15 : stage2 ? 9 : 2.5); comparison.add(model);
    }
    scratch.setModel(comparison); scratch.renderView('three-quarter', { width: 1200, height: 420, span: stage4 ? 58 : stage3 ? 38 : stage2 ? 25 : 4.4 });
    $('comparison-image').src = scratch.canvas.toDataURL('image/png');
    const sheetStats = [];
    for (const id of ids) {
        const model = build(library, id, { lod: 'LOD1' }); scratch.setModel(model);
        sheetStats.push({ id, ...scratch.renderView('three-quarter', { width: 500, height: 300 }) });
        const record = library.records[id], tile = document.createElement('article'); tile.className = 'tile';
        tile.tabIndex = 0; tile.setAttribute('role', 'button'); tile.setAttribute('aria-label', `Inspect ${id}`);
        const img = new Image(); img.src = scratch.canvas.toDataURL('image/png'); img.alt = `${id} LOD1`;
        const title = document.createElement('h3'); title.textContent = `${id} · ${record.canonical_name}`;
        const dimensions = document.createElement('p'); dimensions.textContent = `${model.userData.expected_dimensions_mm.map(n => +n.toFixed(4)).join(' × ')} mm`;
        const status = document.createElement('p'); status.textContent = `${record.library_metadata.provisional ? 'PROVISIONAL · ' : ''}Source: ${record.status} · appearance: ${record.confidence.materials_appearance}${record.library_metadata.conflicts?.length ? ' · spec conflict' : ''}`;
        if (record.library_metadata.provisional) status.className = 'badge';
        tile.append(img, title, dimensions, status); tile.onclick = () => show(id);
        tile.onkeydown = e => { if (['Enter', ' '].includes(e.key)) { e.preventDefault(); show(id); } };
        $('tiles').append(tile);
    }
    scratch.dispose();
    for (const id of ['component', 'lod', 'view']) $(id).addEventListener('change', () => show());
    show(reviewIds[0], 'LOD1', 'three-quarter');
    window.componentLibraryPreview = { show, sheetStats, source_spec_sha256: library.source_spec_sha256,
        model_source_sha256: preview.root.userData.model_source_sha256 };
    document.body.dataset.ready = 'true';
    window.addEventListener('pagehide', () => preview.dispose(), { once: true });
} catch (error) {
    $('status').textContent = `Preview unavailable: ${error.message}`;
    document.body.dataset.error = 'true'; throw error;
}
