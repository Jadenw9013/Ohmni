import * as THREE from '../../vendor/three.module.js';
import { loadLibrary, createComponent } from '../registry.js';
import { ModelPreview } from './model-preview.js';
import { createLibraryMaterials } from '../materials.js';

const $ = id => document.getElementById(id);
try {
    const library = await loadLibrary();
    const preview = new ModelPreview($('model'));
    const scratch = new ModelPreview(document.createElement('canvas'));
    const ids = Object.keys(library.records);
    for (const id of ids) {
        const option = document.createElement('option'); option.value = id;
        option.textContent = `${id} · ${library.records[id].canonical_name}`; $('component').append(option);
    }
    function show(id = $('component').value, lod = $('lod').value, view = $('view').value) {
        const record = library.records[id];
        // A supplied value code demonstrates decal support, not an electrical claim.
        const model = createComponent(library, id, { lod, ...(id === 'OHM-004' ? { marking_text: '100' } : {}) });
        preview.setModel(model);
        const stats = preview.renderView(view, { width: 1000, height: 500 });
        $('component').value = id; $('lod').value = lod; $('view').value = view;
        $('name').textContent = `${id} · ${record.canonical_name}`;
        $('dimensions').textContent = `${model.userData.expected_dimensions_mm.join(' × ')} mm · ${lod} · ${view} · ${stats.triangles} triangles`;
        $('status').textContent = `${record.library_metadata.provisional ? 'PROVISIONAL · ' : ''}Source status: ${record.status}. Appearance: OHMNI defaults, confidence ${record.confidence.materials_appearance}. No exact footprint bound.${id === 'OHM-004' ? ' “100” is demonstration text only.' : ''}`;
        $('notes').textContent = [record.source.document, `Entry line ${record.source.line}`, ...record.library_metadata.uncertain_values,
            record.source.sections.Sources].join('\n\n');
        return { ...stats, component_id: id, bounds_mm: model.userData.expected_dimensions_mm,
            source_status: record.status, provisional: record.library_metadata.provisional };
    }
    const comparison = new THREE.Group(), materials = createLibraryMaterials();
    for (const [i, id] of ['OHM-004', 'OHM-023', 'OHM-041'].entries()) {
        const model = createComponent(library, id, { lod: 'LOD1', ...(i === 0 ? { marking_text: '100' } : {}) }, materials);
        model.position.x = (i - 1) * 2.5; comparison.add(model);
    }
    scratch.setModel(comparison); scratch.renderView('three-quarter', { width: 1200, height: 420, span: 4.4 });
    $('comparison-image').src = scratch.canvas.toDataURL('image/png');
    const sheetStats = [];
    for (const id of ids) {
        const model = createComponent(library, id, { lod: 'LOD1' }); scratch.setModel(model);
        sheetStats.push({ id, ...scratch.renderView('three-quarter', { width: 500, height: 300 }) });
        const record = library.records[id], tile = document.createElement('article'); tile.className = 'tile';
        tile.tabIndex = 0; tile.setAttribute('role', 'button'); tile.setAttribute('aria-label', `Inspect ${id}`);
        const img = new Image(); img.src = scratch.canvas.toDataURL('image/png'); img.alt = `${id} LOD1`;
        const title = document.createElement('h3'); title.textContent = `${id} · ${record.canonical_name}`;
        const dimensions = document.createElement('p'); dimensions.textContent = `${model.userData.expected_dimensions_mm.join(' × ')} mm`;
        const status = document.createElement('p'); status.textContent = record.library_metadata.provisional ? 'PROVISIONAL · source: partial' : 'Source: complete · appearance: L';
        if (record.library_metadata.provisional) status.className = 'badge';
        tile.append(img, title, dimensions, status); tile.onclick = () => show(id);
        tile.onkeydown = e => { if (['Enter', ' '].includes(e.key)) { e.preventDefault(); show(id); } };
        $('tiles').append(tile);
    }
    scratch.dispose();
    for (const id of ['component', 'lod', 'view']) $(id).addEventListener('change', () => show());
    show('OHM-004', 'LOD1', 'three-quarter');
    window.componentLibraryPreview = { show, sheetStats, source_spec_sha256: library.source_spec_sha256,
        model_source_sha256: preview.root.userData.model_source_sha256 };
    document.body.dataset.ready = 'true';
    window.addEventListener('pagehide', () => preview.dispose(), { once: true });
} catch (error) {
    $('status').textContent = `Preview unavailable: ${error.message}`;
    document.body.dataset.error = 'true'; throw error;
}
