import * as THREE from '../../vendor/three.module.js';
import { VisualRenderer, disposeTree } from '../../visual-renderer.js';

// Reuse the existing renderer, lighting, environment and disposal boundary.
// Component inspection uses an orthographic camera so scale comparisons are honest.
export class ModelPreview extends VisualRenderer {
    constructor(canvas) {
        super(canvas);
        this.scene.background = new THREE.Color('#17232e');
        this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 1000);
        this.renderer.shadowMap.enabled = false;
    }
    setModel(root) {
        if (this.root) { this.scene.remove(this.root); disposeTree(this.root); }
        this.root = root; this.scene.add(root); root.updateMatrixWorld(true);
    }
    renderView(view = 'three-quarter', { width = 800, height = 480, span, sideAxis = 'Y', sideSign = -1 } = {}) {
        const bounds = new THREE.Box3().setFromObject(this.root);
        const center = bounds.getCenter(new THREE.Vector3()), size = bounds.getSize(new THREE.Vector3());
        const extent = Math.max(size.x, size.y, size.z);
        const direction = { top: [0, 0, 1], underside: [0, 0, -1], side: sideAxis === 'X' ? [-1, 0, 0] : [0, sideSign, 0],
            'three-quarter': [0.8, sideSign*1.3, 0.9] }[view];
        if (!direction) throw new RangeError('Unknown view');
        const verticalSpan = span ?? extent * 1.45;
        this.renderer.setPixelRatio(1); this.renderer.setSize(width, height, false);
        this.camera.left = -verticalSpan * width / height / 2;
        this.camera.right = -this.camera.left; this.camera.top = verticalSpan / 2;
        this.camera.bottom = -this.camera.top;
        this.camera.position.copy(center).add(new THREE.Vector3(...direction).normalize().multiplyScalar(extent * 4 + 10));
        this.camera.up.set(0, view === 'top' || view === 'underside' ? 1 : 0,
            view === 'top' || view === 'underside' ? 0 : 1);
        this.camera.lookAt(center); this.camera.updateProjectionMatrix();
        this.renderer.render(this.scene, this.camera);
        this.canvas.dataset.triangles = String(this.renderer.info.render.triangles);
        this.canvas.dataset.drawCalls = String(this.renderer.info.render.calls);
        return { view, vertical_span_mm: verticalSpan, triangles: this.renderer.info.render.triangles,
            draw_calls: this.renderer.info.render.calls };
    }
}
