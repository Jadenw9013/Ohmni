// Rendering-only GPU boundary. Millimetres, z-up; source electrical data is never mutated.
import * as THREE from './vendor/three.module.js';
import { createAsset, createMaterials } from './visual-assets.js';
import { addLayers, contour, updateLayerAppearance } from './visual-layers.js';

export function boardShape(width, depth, holes = []) {
    const shape = new THREE.Shape();
    shape.moveTo(-width / 2, -depth / 2); shape.lineTo(width / 2, -depth / 2);
    shape.lineTo(width / 2, depth / 2); shape.lineTo(-width / 2, depth / 2); shape.closePath();
    for (const hole of holes) {
        const path = new THREE.Path();
        if (hole.width) path.setFromPoints(contour(hole.width, hole.depth, hole.shape, hole.x, hole.y, hole.rotation).reverse());
        else path.absellipse(hole.x, hole.y, hole.rx ?? hole.radius, hole.ry ?? hole.radius, 0, Math.PI * 2, true);
        shape.holes.push(path);
    }
    return shape;
}

export function createSlab(width, depth, thickness, holes, materials) {
    const geometry = new THREE.ExtrudeGeometry(boardShape(width, depth, holes), {
        depth: thickness, bevelEnabled: false, curveSegments: 20,
    });
    geometry.translate(0, 0, -thickness / 2);
    const slab = new THREE.Mesh(geometry, [materials.mask, materials.edge]);
    slab.receiveShadow = true; slab.castShadow = true;
    slab.userData.visualProvenance = 'ARTIFACT_DERIVED';
    return slab;
}

export function disposeTree(root) {
    const geometries = new Set(), materials = new Set(), textures = new Set();
    root?.traverse(node => {
        if (node.geometry) geometries.add(node.geometry);
        for (const material of [node.material].flat().filter(Boolean)) {
            materials.add(material);
            for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
        }
    });
    for (const value of [...geometries, ...textures, ...materials]) value.dispose();
}

function environment(renderer) {
    // Original procedural studio, no third-party HDRI, image, or network dependency.
    const room = new THREE.Scene();
    room.background = new THREE.Color('#697782');
    const shell = new THREE.Mesh(new THREE.BoxGeometry(30, 30, 30),
        new THREE.MeshBasicMaterial({ color: '#68727a', side: THREE.BackSide }));
    room.add(shell);
    for (const [position, size, color, intensity] of [
        [[-8, -5, 10], [8, 12, 0.2], '#fff5e6', 4],
        [[8, 3, 7], [4, 11, 0.2], '#d6e7ff', 2.4],
        [[0, 8, 10], [10, 3, 0.2], '#ffffff', 2],
    ]) {
        const material = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(intensity) });
        const panel = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
        panel.position.set(...position); room.add(panel);
    }
    const generator = new THREE.PMREMGenerator(renderer);
    const target = generator.fromScene(room, 0.06); generator.dispose(); disposeTree(room);
    return target;
}

export class VisualRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        const context = canvas.getContext('webgl2', { antialias: true, alpha: false });
        if (!context) throw new Error('WebGL2 is unavailable; use compatibility view');
        this.renderer = new THREE.WebGLRenderer({ canvas, context, antialias: true, alpha: false });
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 0.96;
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.scene = new THREE.Scene(); this.scene.background = new THREE.Color('#3f464b');
        this.environment = environment(this.renderer); this.scene.environment = this.environment.texture;
        this.scene.environmentIntensity = 0.55;
        this.scene.add(new THREE.HemisphereLight('#e4f0ff', '#595340', 0.7));
        this.key = new THREE.DirectionalLight('#fff4e6', 2.6);
        this.key.position.set(-70, -90, 140); this.key.castShadow = true;
        this.key.shadow.mapSize.set(2048, 2048);
        Object.assign(this.key.shadow.camera, { left: -110, right: 110, top: 110, bottom: -110, near: 1, far: 400 });
        this.key.shadow.bias = -0.00012; this.key.shadow.normalBias = 0.04;
        this.key.shadow.radius = 3; this.scene.add(this.key);
        const fill = new THREE.DirectionalLight('#d5e6ff', 1.2); fill.position.set(60, 65, 80); this.scene.add(fill);
        const underside = new THREE.DirectionalLight('#e2e9ed', 1.7); underside.position.set(0, -30, -100); this.scene.add(underside);
        this.camera = new THREE.PerspectiveCamera(40, 1, 1, 1200);
        this.raycaster = new THREE.Raycaster(); this.owners = new Map(); this.frameTimes = [];
    }

    setScene(manifest) {
        if (this.manifest === manifest) return;
        if (this.root) { this.scene.remove(this.root); disposeTree(this.root); }
        this.manifest = manifest; this.root = new THREE.Group(); this.scene.add(this.root);
        this.materials = createMaterials();
        this.materials.mask ??= new THREE.MeshStandardMaterial({ color: '#28633b', roughness: 0.48 });
        this.materials.edge ??= new THREE.MeshStandardMaterial({ color: '#5b5332', roughness: 0.85 });
        this.owners.clear();
        const { width, depth, thickness = 1.6, holes = [], instances = [] } = manifest;
        const surfaceHoles = manifest.provenance === 'ILLUSTRATIVE_ONLY' ? manifest.illustrativeSurfaceFeatures?.items ?? [] : [];
        this.slab = createSlab(width, depth, thickness, [...holes, ...surfaceHoles], this.materials);
        this.slab.userData.visualProvenance = manifest.provenance;
        this.root.add(this.slab);
        this.layers = addLayers(this.root, manifest, this.materials);
        for (const entry of instances) {
            let group;
            try { group = createAsset(entry.family, entry.options, this.materials); }
            catch (error) {
                if (manifest.provenance !== 'ARTIFACT_DERIVED') throw error;
                group = new THREE.Group();
                const box = new THREE.Mesh(new THREE.BoxGeometry(entry.options.width, entry.options.depth, 1),
                    new THREE.MeshBasicMaterial({ color: '#c88737', wireframe: true }));
                box.position.z = .5; group.add(box); group.userData.missingModel = true;
            }
            group.position.set(entry.x, entry.y, (entry.side === 'B.Cu' ? -1 : 1) * thickness / 2);
            if (entry.side === 'B.Cu') group.scale.z = -1;
            group.rotation.z = (entry.rotation ?? 0) * Math.PI / 180;
            group.userData.owner = entry.id; group.userData.basePosition = group.position.clone();
            group.userData.entry = entry;
            this.owners.set(entry.id, group); this.root.add(group);
        }
        for (const entry of manifest.microdetailPatches ?? []) {
            const group = createAsset(entry.family, entry.options, this.materials);
            group.position.set(entry.x, entry.y, thickness / 2 + .035);
            group.rotation.z = (entry.rotation ?? 0) * Math.PI / 180;
            group.userData.visualProvenance = 'ILLUSTRATIVE_ONLY'; this.root.add(group);
        }
        const gold = this.materials.gold ?? new THREE.MeshStandardMaterial({ color: '#bca25a', metalness: 1, roughness: 0.3 });
        for (const hole of holes.filter(h => h.annulus)) {
            for (const side of [-1, 1]) {
                const ring = new THREE.Mesh(new THREE.RingGeometry(hole.radius, hole.annulus, 48), gold);
                ring.position.set(hole.x, hole.y, side * (thickness / 2 + 0.03));
                if (side < 0) ring.rotation.x = Math.PI;
                this.root.add(ring);
            }
        }
        this.scene.updateMatrixWorld(true);
    }

    boundingParts(sourceScene, options) {
        const result = [];
        for (const part of sourceScene.parts) {
            const object = this.owners.get(part.ref); if (!object) continue;
            // The same assembly transform drives visible meshes, labels and picking.
            object.position.set(part.centre.x, part.centre.y, part.centre.z);
            if (this.manifest.provenance === 'ILLUSTRATIVE_ONLY') object.position.z += (options.explode ?? 0) * 12;
            object.userData.displayPosition = object.position.clone();
            object.updateWorldMatrix(true, true);
            const bounds = new THREE.Box3().setFromObject(object), { min, max } = bounds;
            const centre = bounds.getCenter(new THREE.Vector3());
            const face = z => [{x:min.x,y:min.y,z},{x:max.x,y:min.y,z},{x:max.x,y:max.y,z},{x:min.x,y:max.y,z}];
            result.push({ ...part, top: face(max.z), bottom: face(min.z), centre,
                labelPoint: { x: centre.x, y: centre.y, z: max.z }, displayKind: part.partId?.startsWith('ESP32') ? 'module' : part.displayKind });
        }
        return result;
    }

    render(camera, viewport, options = {}) {
        if (this.renderer.getContext().isContextLost()) return;
        const start = performance.now();
        const { width, height, ratio = 1 } = viewport;
        this.renderer.setPixelRatio(Math.min(ratio, options.quality === 'low' ? 1 : 2));
        this.renderer.setSize(width, height, false);
        this.renderer.shadowMap.enabled = options.quality !== 'low';
        const { yaw, pitch, distance, focal, zoom, panX, panY } = camera;
        this.camera.fov = 2 * Math.atan(height / (2 * focal * zoom)) * 180 / Math.PI;
        this.camera.aspect = width / height;
        this.camera.position.set(-Math.sin(yaw) * Math.cos(pitch) * distance,
            -Math.cos(yaw) * Math.cos(pitch) * distance, Math.sin(pitch) * distance);
        this.camera.up.set(Math.sin(yaw) * Math.sin(pitch), Math.cos(yaw) * Math.sin(pitch), Math.cos(pitch));
        this.camera.lookAt(0, 0, 0); this.camera.updateProjectionMatrix();
        this.camera.projectionMatrix.elements[8] = -2 * panX / width;
        this.camera.projectionMatrix.elements[9] = 2 * panY / height;
        this.camera.projectionMatrixInverse.copy(this.camera.projectionMatrix).invert();
        this.camera.updateMatrixWorld();
        this.slab.visible = !options.hideBoard;
        this.slab.material[0].transparent = Boolean(options.xray);
        this.slab.material[0].opacity = options.xray ? 0.16 : 1;
        this.slab.material[0].depthWrite = !options.xray;
        updateLayerAppearance(this.layers, options);
        for (const [id, object] of this.owners) {
            object.visible = options.showComponents !== false && (!options.isolate || options.isolate === id);
            object.position.copy(object.userData.displayPosition ?? object.userData.basePosition);
        }
        this.renderer.render(this.scene, this.camera);
        this.frameTimes.push(performance.now() - start); if (this.frameTimes.length > 120) this.frameTimes.shift();
        this.canvas.dataset.triangles = String(this.renderer.info.render.triangles);
        this.canvas.dataset.drawCalls = String(this.renderer.info.render.calls);
    }

    pick(event) {
        const rect = this.canvas.getBoundingClientRect();
        this.raycaster.setFromCamera(new THREE.Vector2(2 * (event.clientX - rect.left) / rect.width - 1,
            1 - 2 * (event.clientY - rect.top) / rect.height), this.camera);
        for (const hit of this.raycaster.intersectObjects(this.root.children, true)) {
            let object = hit.object;
            if (!object.visible) continue;
            while (object && !object.userData.owner) object = object.parent;
            if (object?.visible) return { ref: object.userData.owner, distance: hit.distance };
            if (hit.object === this.slab && this.slab.material[0].opacity === 1) return null;
        }
        return null;
    }

    dispose() {
        disposeTree(this.root); this.environment.dispose(); this.renderer.dispose(); this.owners.clear();
    }
}
