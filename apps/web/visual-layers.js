import * as THREE from './vendor/three.module.js';
import { markingGeometry } from './visual-assets.js';

export function contour(width, height, shape = 'rect', x = 0, y = 0, rotation = 0) {
    const radius = shape === 'circle' || shape === 'oval' ? Math.min(width, height) / 2
        : shape === 'roundrect' ? Math.min(width, height) * 0.2 : 0;
    const points = [], angle = rotation * Math.PI / 180;
    for (const [sx, sy, start] of [[1, 1, 0], [-1, 1, 90], [-1, -1, 180], [1, -1, 270]]) {
        for (let step = 0; step <= 8; step++) {
            const a = (start + step * 90 / 8) * Math.PI / 180;
            const px = sx * (width / 2 - radius) + Math.cos(a) * radius;
            const py = sy * (height / 2 - radius) + Math.sin(a) * radius;
            points.push(new THREE.Vector2(x + px * Math.cos(angle) - py * Math.sin(angle),
                y + px * Math.sin(angle) + py * Math.cos(angle)));
        }
    }
    return points;
}

function appendGeometry(buckets, key, geometry, matrix = null, membership = null) {
    const g = geometry.index ? geometry.toNonIndexed() : geometry;
    if (g !== geometry) geometry.dispose();
    if (matrix) g.applyMatrix4(matrix);
    const list = buckets.get(key) ?? []; list.push({ geometry: g, membership }); buckets.set(key, list);
}

function joinedGeometry(list) {
    const positions = [], normals = [], ranges = [];
    for (const { geometry, membership } of list) {
        const start = positions.length / 3, count = geometry.attributes.position.count;
        positions.push(...geometry.attributes.position.array);
        normals.push(...geometry.attributes.normal.array); geometry.dispose();
        if (membership) ranges.push({ start, count, ...membership });
    }
    const merged = new THREE.BufferGeometry();
    merged.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    merged.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    merged.userData.sourceRanges = ranges;
    return merged;
}

/** Update existing vertex colors only when appearance or exact membership changes. */
export function updateLayerAppearance(layers, options = {}) {
    const { refs = [], nets = [], systems = [] } = options.highlight ?? {};
    const refSet = new Set(refs), netSet = new Set(nets), systemSet = new Set(systems);
    const signature = JSON.stringify([refs, nets, systems, options.showMask !== false]);
    const highlight = new THREE.Color('#8cecff');
    for (const [key, mesh] of Object.entries(layers)) {
        if (key === 'silk') { mesh.visible = options.showSilk !== false; continue; }
        const copper = key === 'frontCopper' || key === 'backCopper';
        if (copper) mesh.visible = options.showCopper !== false;
        if (mesh.userData.appearanceSignature === signature) continue;
        mesh.userData.appearanceSignature = signature;
        const base = copper ? new THREE.Color(options.showMask === false ? '#b58a45' : '#477d4d') : mesh.userData.baseColor;
        if (copper) mesh.material.metalness = options.showMask === false ? 1 : 0;
        const colors = mesh.geometry.attributes.color;
        for (let i = 0; i < colors.count; i++) colors.setXYZ(i, base.r, base.g, base.b);
        let highlightedVertices = 0;
        for (const range of mesh.geometry.userData.sourceRanges) {
            const matches = (range.net !== null && netSet.has(range.net))
                || (range.ref !== null && refSet.has(range.ref))
                || (range.system !== null && systemSet.has(range.system));
            if (!matches) continue;
            for (let i = range.start; i < range.start + range.count; i++) colors.setXYZ(i, highlight.r, highlight.g, highlight.b);
            highlightedVertices += range.count;
        }
        mesh.userData.highlightedVertices = highlightedVertices;
        colors.needsUpdate = true;
    }
}

export function addLayers(root, manifest, materials) {
    const buckets = new Map(), t = manifest.thickness / 2;
    const systems = new Map((manifest.instances ?? []).map(entry => [entry.id, entry.region]));
    // Only authoritative projection metadata supplies membership. Illustrative
    // paths and surface features never become selectable electrical nets.
    const membership = (source, kind) => manifest.provenance === 'ARTIFACT_DERIVED' ? {
        kind, net: typeof source.net_name === 'string' && source.net_name ? source.net_name : null,
        ref: source.owner ?? null, system: systems.get(source.owner) ?? null,
    } : null;
    const translate = (x, y, z, bottom = false) => new THREE.Matrix4().compose(new THREE.Vector3(x, y, z),
        new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), bottom ? Math.PI : 0), new THREE.Vector3(1, 1, 1));
    for (const pad of manifest.pads ?? []) {
        if (pad.kind === 'np_thru_hole') continue;
        const shape = new THREE.Shape(contour(pad.width_mm, pad.height_mm, pad.shape));
        if (pad.drill) shape.holes.push(new THREE.Path(contour(pad.drill.width_mm, pad.drill.height_mm, pad.drill.shape).reverse()));
        for (const sign of pad.kind !== 'smd' ? [-1, 1] : [pad.side === 'B.Cu' ? -1 : 1]) {
            const g = new THREE.ShapeGeometry(shape, 16); g.rotateZ(pad.rotation * Math.PI / 180);
            // Reflect normal only; world x/y remain source coordinates on both layers.
            if (sign < 0) { const a = g.index.array; for (let i = 0; i < a.length; i += 3) [a[i], a[i + 2]] = [a[i + 2], a[i]]; g.computeVertexNormals(); }
            appendGeometry(buckets, 'pads', g, new THREE.Matrix4().makeTranslation(pad.x, pad.y, sign * (t + 0.04)), membership(pad, 'pad'));
        }
    }
    for (const via of manifest.vias ?? []) for (const sign of [-1, 1]) {
        appendGeometry(buckets, 'pads', new THREE.RingGeometry(via.drill_mm / 2, via.diameter_mm / 2, 20),
            translate(via.x, via.y, sign * (t + 0.04), sign < 0), membership(via, 'via'));
    }
    const paths = manifest.provenance === 'ILLUSTRATIVE_ONLY' ? manifest.illustrativeGuideGeometry?.paths ?? [] : manifest.tracks ?? [];
    if (manifest.provenance === 'ILLUSTRATIVE_ONLY') {
        for (const feature of manifest.illustrativeSurfaceFeatures?.items ?? []) for (const sign of [-1, 1]) {
            appendGeometry(buckets, 'pads', new THREE.RingGeometry(feature.radius, feature.annulus, 24),
                translate(feature.x, feature.y, sign * (t + .04), sign < 0));
        }
        for (const entry of manifest.instances) {
            const geometry = markingGeometry(entry.id, Math.max(2, Math.min(5, entry.options.width ?? 4)), .65);
            geometry.translate(0, -(entry.options.depth ?? 4) / 2 - 1.1, 0);
            geometry.rotateZ((entry.rotation ?? 0) * Math.PI / 180);
            appendGeometry(buckets, 'silk', geometry, new THREE.Matrix4().makeTranslation(entry.x, entry.y, t + .04));
        }
        appendGeometry(buckets, 'silk', markingGeometry('OHMNI / COMPONENT ATLAS', 28, 1), new THREE.Matrix4().makeTranslation(0, -manifest.depth / 2 + 2, t + .04));
    }
    for (const line of paths) {
        const points = line.points ?? [[line.x1, line.y1], [line.x2, line.y2]];
        const sign = line.layer === 'B.Cu' ? -1 : 1, key = sign > 0 ? 'frontCopper' : 'backCopper';
        const width = line.width_mm ?? line.width ?? 0.24;
        for (let i = 1; i < points.length; i++) {
            const [ax, ay] = points[i - 1], [bx, by] = points[i], dx = bx - ax, dy = by - ay;
            const g = new THREE.PlaneGeometry(Math.hypot(dx, dy), width);
            g.rotateZ(Math.atan2(dy, dx));
            if (sign < 0) { const a = g.index.array; for (let j = 0; j < a.length; j += 3) [a[j], a[j + 2]] = [a[j + 2], a[j]]; g.computeVertexNormals(); }
            appendGeometry(buckets, key, g, new THREE.Matrix4().makeTranslation((ax + bx) / 2, (ay + by) / 2, sign * (t + 0.022)), membership(line, 'track'));
            for (const [x, y] of [[ax, ay], [bx, by]]) appendGeometry(buckets, key, new THREE.CircleGeometry(width / 2, 10),
                translate(x, y, sign * (t + 0.022), sign < 0), membership(line, 'track'));
        }
    }
    const layers = {};
    for (const [key, list] of buckets) {
        const material = (key === 'pads' ? materials.gold : key === 'silk' ? materials.silk : materials.trace).clone();
        const geometry = joinedGeometry(list), mesh = new THREE.Mesh(geometry, material);
        mesh.userData.baseColor = material.color.clone();
        if (key !== 'silk') {
            material.vertexColors = true; material.color.set('#ffffff');
            geometry.setAttribute('color', new THREE.Float32BufferAttribute(new Float32Array(geometry.attributes.position.count * 3), 3));
        }
        mesh.receiveShadow = true; mesh.userData.layer = key; root.add(mesh); layers[key] = mesh;
    }
    updateLayerAppearance(layers);
    return layers;
}
