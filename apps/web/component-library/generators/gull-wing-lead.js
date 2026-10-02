import * as THREE from '../../vendor/three.module.js';

// Local radial axis +X, lead-width axis Y, height Z. The caller rotates this
// helper to any package edge, including future quad packages. No package data.
export function extrudedLeadProfile(points, width, curveSegments = 1) {
    const shape = new THREE.Shape();
    shape.moveTo(...points[0]);
    for (const point of points.slice(1)) {
        if (point.length === 4) shape.quadraticCurveTo(...point);
        else shape.lineTo(...point);
    }
    shape.closePath();
    const geometry = new THREE.ExtrudeGeometry(shape, { depth: width, bevelEnabled: false, steps: 1, curveSegments });
    geometry.rotateX(Math.PI / 2); geometry.translate(0, width / 2, 0);
    geometry.computeBoundingBox(); geometry.computeBoundingSphere();
    return geometry;
}

export function gullWingLead({ bodyEdge, exitHeight, tip, footLength, width, thickness, radius = 0 }) {
    const inner = tip - footLength, run = inner - bodyEdge;
    if (run <= 0 || exitHeight <= thickness) throw new RangeError('Lead span cannot accommodate body and foot');
    const stub = bodyEdge + run * 0.25;
    const slope = -(exitHeight - thickness / 2) / (inner - stub);
    // Offset the sloped face by stock thickness normal to that face, then
    // intersect with the horizontal upper surfaces. A vertical offset alone
    // would incorrectly thin the steep section of a narrow SOIC lead.
    const shift = thickness * (Math.sqrt(1 + slope * slope) - 1) / -slope;
    if (inner + shift >= tip) throw new RangeError('Lead stock thickness consumes the flat foot');
    // Fillets are limited to available run and height, without moving the toe
    // or the flat underside [tip-footLength, tip] at Z=0.
    const r = Math.min(radius, run / 4, (exitHeight - thickness) / 4);
    const bottom = [[bodyEdge, exitHeight - thickness / 2], [stub, exitHeight - thickness / 2]];
    const top = [[tip, thickness], [inner + shift, thickness]];
    if (r) {
        bottom.push([inner - r, r], [inner - r / 2, 0, inner, 0]);
        top.push([inner + shift - r, thickness, inner + shift - r, thickness + r],
            [stub + shift + r, exitHeight + thickness / 2 - r],
            [stub + shift, exitHeight + thickness / 2, stub + shift - r / 2, exitHeight + thickness / 2]);
    } else { bottom.push([inner, 0]); top.push([stub + shift, exitHeight + thickness / 2]); }
    return extrudedLeadProfile([...bottom, [tip, 0], ...top, [bodyEdge, exitHeight + thickness / 2]], width, r ? 5 : 1);
}
