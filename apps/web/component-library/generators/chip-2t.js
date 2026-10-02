import * as THREE from '../../vendor/three.module.js';
import { markingGeometry } from '../../visual-assets.js';
import { chipDimensions } from '../validate.js';

const sorted = values => [...new Set(values)].sort((a, b) => a - b);

// A partitioned outer surface: no overlapping slabs, hidden plating thickness,
// coplanar overlays or boolean dependency. Bands may differ on top and bottom.
function surface(group, materials, { L, W, H, xCuts = [], zCuts = [], radius = 0,
    chamfer = false, offset = [0, 0, 0], classify }) {
    const half = [L / 2, W / 2];
    const edgeCuts = size => radius ? [-size / 2 + radius / 2, -size / 2 + radius,
        size / 2 - radius, size / 2 - radius / 2] : [];
    const axes = [sorted([-L / 2, ...edgeCuts(L), ...xCuts, L / 2]),
        sorted([-W / 2, ...edgeCuts(W), W / 2]),
        sorted([0, ...zCuts, ...(radius ? [H - radius, H - radius / 2] : []), H])];
    const buckets = new Map();
    const add = (key, token, vertices, normal) => {
        if (!buckets.has(key)) buckets.set(key, { token, positions: [], normals: [] });
        const b = buckets.get(key);
        for (const index of [0, 1, 2, 0, 2, 3]) {
            const p = [...vertices[index]], n = [...normal];
            // Round only the upper outer edges. The complete flat underside
            // remains at z=0, preserving specified PCB contact centers/areas.
            if (radius && p[2] > H - radius) {
                const c = [Math.max(-half[0] + radius, Math.min(half[0] - radius, p[0])),
                    Math.max(-half[1] + radius, Math.min(half[1] - radius, p[1])), H - radius];
                const v = p.map((x, i) => x - c[i]);
                const length = chamfer ? v.reduce((s, x) => s + Math.abs(x), 0) : Math.hypot(...v);
                for (let i = 0; i < 3; i++) p[i] = c[i] + v[i] * radius / length;
                const norm = chamfer ? v.map(x => Math.sign(x)) : v;
                const unit = Math.hypot(...norm);
                for (let i = 0; i < 3; i++) n[i] = norm[i] / unit;
            }
            b.positions.push(...p.map((x, i) => x + offset[i])); b.normals.push(...n);
        }
    };
    // Fixed axis, sign, u, v: u cross v points outwards.
    for (const [axis, sign, u, v, side] of [[2, 1, 0, 1, 'top'], [2, -1, 1, 0, 'bottom'],
        [0, 1, 1, 2, 'end'], [0, -1, 2, 1, 'end'], [1, 1, 2, 0, 'side'], [1, -1, 0, 2, 'side']]) {
        for (let a = 0; a < axes[u].length - 1; a++) for (let b = 0; b < axes[v].length - 1; b++) {
            const vertices = [[a, b], [a + 1, b], [a + 1, b + 1], [a, b + 1]].map(([i, j]) => {
                const p = [0, 0, 0]; p[axis] = sign > 0 ? axes[axis].at(-1) : axes[axis][0];
                p[u] = axes[u][i]; p[v] = axes[v][j]; return p;
            });
            const center = vertices[0].map((_, i) => vertices.reduce((sum, p) => sum + p[i], 0) / 4);
            const [key, token] = classify(center, side);
            const normal = [0, 0, 0]; normal[axis] = sign;
            add(key, token, vertices, normal);
        }
    }
    for (const [key, bucket] of buckets) {
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(bucket.positions, 3));
        geometry.setAttribute('normal', new THREE.Float32BufferAttribute(bucket.normals, 3));
        geometry.computeBoundingBox(); geometry.computeBoundingSphere();
        const mesh = new THREE.Mesh(geometry, materials[bucket.token]);
        mesh.name = key; mesh.castShadow = true; mesh.receiveShadow = true;
        mesh.userData.material_token = bucket.token;
        if (key.startsWith('terminal-')) mesh.userData.terminal = key.slice(9);
        group.add(mesh);
    }
}

export function generateChip2T(record, defaults, { lod, marking }, materials) {
    const { L, W, H, top, bottom } = chipDimensions(record);
    const group = new THREE.Group(); group.name = record.id;
    const strip = record.function === 'CURRENT_SENSE', resistor = record.function === 'R';
    const coat = strip ? defaults.current_sense_coat_mm : defaults.resistor_coat_mm;
    const radius = lod === 'LOD2' ? Math.min(strip ? defaults.current_sense_chamfer_mm : defaults.edge_radius_mm, H / 4, W / 4) : 0;
    let markingZ = H;
    if (strip && lod !== 'LOD0') {
        const window = L - 2 * bottom;
        for (const side of [-1, 1]) surface(group, materials, { L: bottom, W, H, radius, chamfer: true,
            offset: [side * (L - bottom) / 2, 0, 0],
            classify: () => [`terminal-${side < 0 ? 1 : 2}`, record.terminals.material] });
        const coreHeight = H * 0.7 + coat;
        surface(group, materials, { L: window, W, H: coreHeight, radius: 0,
            offset: [0, 0, H * 0.15], zCuts: [H * 0.7],
            classify: (p, side) => side === 'top' || p[2] > H * 0.7
                ? ['top-coat', 'MAT_RESISTOR_COAT_BLACK'] : ['body', record.body.material] });
        markingZ = H * 0.85 + coat;
    } else {
        const sideBand = Math.min(top, bottom);
        const xCuts = sorted([top, bottom, sideBand].flatMap(band => [-L / 2 + band, L / 2 - band]));
        surface(group, materials, { L, W, H, xCuts,
            zCuts: resistor && lod !== 'LOD0' ? [H - coat] : [], radius,
            classify: (p, side) => {
                const band = side === 'top' ? top : side === 'bottom' ? bottom : sideBand;
                if (Math.abs(p[0]) > L / 2 - band + 1e-10 || side === 'end') {
                    return [`terminal-${p[0] < 0 ? 1 : 2}`, record.terminals.material];
                }
                if ((resistor || strip) && (side === 'top' || (lod !== 'LOD0' && side === 'side' && p[2] > H - coat))) {
                    return ['top-coat', 'MAT_RESISTOR_COAT_BLACK'];
                }
                return ['body', record.body.material];
            } });
    }
    if (lod !== 'LOD0' && marking) {
        const decal = new THREE.Mesh(markingGeometry(marking, (L - 2 * top) * 0.8, W * 0.45), materials.MAT_SILKSCREEN_WHITE);
        decal.name = 'marking-decal'; decal.position.z = markingZ;
        // Rendering offset only; no dimension-changing floating decal geometry.
        decal.material = decal.material.clone(); decal.material.polygonOffset = true;
        decal.material.polygonOffsetFactor = -1; decal.material.polygonOffsetUnits = -1;
        decal.userData = { material_token: 'MAT_SILKSCREEN_WHITE', optional: true, content_basis: 'CALLER_SUPPLIED_VISUAL_TEXT' };
        group.add(decal);
    }
    group.userData = { component_id: record.id, package_family: record.package_family,
        package_member: record.package_member, generator: record.generator, lod,
        status: record.status, library_metadata: structuredClone(record.library_metadata),
        units: 'mm', up_axis: 'Z', origin: 'FCO', contact_plane_mm: 0,
        expected_dimensions_mm: [L, W, H],
        contacts: [-1, 1].map(sign => ({ terminal: sign < 0 ? '1' : '2',
            center_mm: [sign * (L - bottom) / 2, 0, 0], size_mm: [bottom, W], polarity: 'none' })),
        source: record.source, confidence: record.confidence,
        simplifications: ['No solder or footprint pads', 'Optional cap proudness omitted',
            'LOD2 upper-edge rounding preserves full flat contact surfaces'],
        markings: marking || null, electrical_authority: false };
    return group;
}
