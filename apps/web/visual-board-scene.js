// Pure display projection: preserve identities and source coordinates, keep package appearance separate.
import { VISUAL_SOURCE_HASH } from './visual-version.js';
const cache = new WeakMap();
export function packageBinding(component) {
    const id = component.part_id, packageName = component.package ?? '';
    if (id === 'ESP32-WROOM-32E') return 'esp32_module';
    if (id === 'USB_C_RECEPTACLE_16P') return 'usb_c';
    if (id === 'HEADER_1X6_254') return 'pin_header';
    if (id === 'GENERIC_MOMENTARY_BUTTON') return 'switch';
    if (id.startsWith('GENERIC_LED')) return 'led';
    if (id === 'GENERIC_RESISTOR') return 'chip_resistor';
    if (id === 'GENERIC_CAPACITOR') return 'ceramic_chip';
    if (id === 'BME280' || id === 'TMP102') return 'sensor';
    if (packageName === 'SOT-23-5') return 'regulator';
    return 'missing_model';
}

export function actualSceneManifest(board) {
    if (board.kind === 'illustrative_sample' || board.visual_manifest) throw new Error('Educational scenes are not engineering artifacts');
    if (!board.artifact_fingerprint) throw new Error('Source artifact identity is required');
    if (cache.has(board)) return cache.get(board);
    const holes = [], pads = [], instances = [], cx = board.width_mm / 2, cy = board.height_mm / 2;
    for (const [order, component] of board.components.entries()) {
        const family = packageBinding(component), angle = component.rotation_deg * Math.PI / 180;
        const sourcePads = component.pads.map(pad => ({ ...pad, drill: pad.drill ? { ...pad.drill } : null }));
        for (const pad of sourcePads) {
            const x = component.x_mm - cx + pad.x_mm * Math.cos(angle) - pad.y_mm * Math.sin(angle);
            const y = component.y_mm - cy + pad.x_mm * Math.sin(angle) + pad.y_mm * Math.cos(angle);
            pads.push({ ...pad, x, y, rotation: component.rotation_deg, side: component.side, owner: component.ref });
            if (pad.drill) holes.push({ x, y, width: pad.drill.width_mm, depth: pad.drill.height_mm,
                shape: pad.drill.shape, rotation: component.rotation_deg, owner: component.ref });
        }
        const height = { esp32_module: 3.1, usb_c: 3.2, pin_header: 6.2, switch: 4.5,
            sensor: 0.9, regulator: 1.1, ceramic_chip: 0.85, chip_resistor: 0.5, led: 0.8 }[family] ?? 1;
        instances.push({ id: component.ref, sourceComponentId: component.ref, sourceFootprintId: component.footprint_id,
            modelAssetId: `ohmni-procedural/${family}@reference-packages-v1`, visualProvenance: 'PACKAGE_APPROXIMATION',
            dimensionalSource: null, roleEvidenceId: null, name: component.part_id, family, order,
            x: component.x_mm - cx, y: component.y_mm - cy, rotation: component.rotation_deg,
            side: component.side, region: component.system, selectable: true,
            options: { width: component.width_mm, depth: component.height_mm, height, pads: sourcePads,
                includeSolder: false, label: false, actual: true },
            transform: { position: [component.x_mm - cx, component.y_mm - cy,
                (component.side === 'B.Cu' ? -1 : 1) * board.display_thickness_mm / 2], quaternion: [0, 0, Math.sin(angle / 2), Math.cos(angle / 2)] },
        });
    }
    for (const via of board.vias) holes.push({ x: via.x_mm - cx, y: via.y_mm - cy, radius: via.drill_mm / 2 });
    const manifest = { id: `actual:${board.artifact_fingerprint}:${VISUAL_SOURCE_HASH}`, provenance: 'ARTIFACT_DERIVED',
        modelSourceHash: VISUAL_SOURCE_HASH,
        sourceArtifactFingerprint: board.artifact_fingerprint, sourceRoutingFingerprint: board.routing_plan_fingerprint,
        width: board.width_mm, depth: board.height_mm, thickness: board.display_thickness_mm,
        thicknessNote: board.thickness_note, holes, instances, pads,
        tracks: board.tracks.map(track => ({ ...track, x1: track.start_x_mm - cx, y1: track.start_y_mm - cy,
            x2: track.end_x_mm - cx, y2: track.end_y_mm - cy })),
        vias: board.vias.map(via => ({ ...via, x: via.x_mm - cx, y: via.y_mm - cy })),
        silkscreen: [], silkNote: 'No silkscreen primitives are available in this saved projection. Labels are a viewer overlay.',
    };
    cache.set(board, manifest); return manifest;
}
