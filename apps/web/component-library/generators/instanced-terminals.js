import * as THREE from '../../vendor/three.module.js';

export function instances(group,name,geometry,material,placements) {
    const mesh=new THREE.InstancedMesh(geometry,material,placements.length);
    mesh.name=name;
    const matrix=new THREE.Matrix4(),rotation=new THREE.Quaternion(),scale=new THREE.Vector3(1,1,1);
    placements.forEach((p,i)=>{
        rotation.setFromAxisAngle(new THREE.Vector3(0,0,1),p.angle??0);
        matrix.compose(new THREE.Vector3(...p.position),rotation,scale);mesh.setMatrixAt(i,matrix);
    });
    mesh.instanceMatrix.needsUpdate=true;mesh.computeBoundingBox();mesh.computeBoundingSphere();
    mesh.userData={material_token:material.name,instance_terminals:placements.map(p=>p.terminal??null),
        instance_sides:placements.map(p=>p.side??null)};
    group.add(mesh);return mesh;
}

export function leadPlacements(contacts) {
    return contacts.map(c=>({terminal:c.terminal,side:c.side,
        angle:[Math.PI,-Math.PI/2,0,Math.PI/2][c.side_index],
        position:c.side_index%2?[c.center_mm[0],0,0]:[0,c.center_mm[1],0]}));
}
