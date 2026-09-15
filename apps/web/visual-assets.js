// Reusable package illustrations. Dimensions/counts are explicit drawing inputs,
// never facts recovered from a picture, electrical evidence, or PCB geometry.
// Millimetres, z up, contact plane z=0. The caller assigns selection ownership
// to the returned Group; ray hits on any descendant resolve through that group.
import * as THREE from "./vendor/three.module.js";

export const ASSET_VERSION = "reference-packages-v1";
export const ASSET_FAMILIES = Object.freeze(["qfp", "header", "aluminum_can", "axial_resistor",
    "small_outline", "few_terminal", "leadless_block", "white_connector", "shielded_connector",
    "rear_metal_block", "electrolytic_can", "wound_inductor", "coated_radial", "gold_post",
    "coated_axial", "ceramic_chip", "coated_red", "unresolved_patch", "esp32_module", "usb_c",
    "pin_header", "switch", "led", "sensor", "regulator", "chip_resistor"]);
export const ASSET_SOURCE = Object.freeze({ kind: "ORIGINAL_PROCEDURAL_SOURCE",
    source: "apps/web/visual-assets.js", license: "Repository license unspecified",
    thirdPartyGeometry: false, electricalAuthority: false });
const SOURCE_PAD_FAMILIES = new Set(["esp32_module", "usb_c", "pin_header", "switch",
    "led", "sensor", "regulator", "chip_resistor"]);
export const ASSET_REGISTRY = Object.freeze(Object.fromEntries(ASSET_FAMILIES.map((family) => [family,
    Object.freeze({ family, modelAssetId: `ohmni-procedural/${family}@${ASSET_VERSION}`,
        source: ASSET_SOURCE, units: "mm", upAxis: "z", contactPlane: 0,
        appearanceOnly: true, contactBasis: SOURCE_PAD_FAMILIES.has(family) ? "source-pads" : "illustration-parameters" })])));

export function createMaterials() {
    const material = (name, color, metalness, roughness) => {
        const value = new THREE.MeshStandardMaterial({ name, color, metalness, roughness });
        value.userData.appearanceOnly = true;
        return value;
    };
    return {
        mask: material("green solder mask", "#28633b", 0, 0.46),
        trace: material("mask over copper", "#477d4d", 0, 0.46),
        edge: material("laminate edge", "#5b5332", 0, 0.84),
        resin: material("IC resin", "#25282a", 0, 0.68),
        plastic: material("connector housing", "#171b1b", 0, 0.58),
        whitePlastic: material("off-white housing", "#dfe3dc", 0, 0.56),
        aluminum: material("aluminum", "#bcc4c8", 1, 0.32),
        shield: material("sheet metal", "#aeb8bd", 1, 0.28),
        lead: material("lead metal", "#b8c0c3", 1, 0.32),
        solder: material("solder", "#b8c0c3", 1, 0.38),
        gold: material("gold contacts", "#bca25a", 1, 0.29),
        sleeve: material("navy sleeve", "#211d55", 0, 0.42),
        blue: material("blue coating", "#5b9ec1", 0, 0.57),
        tan: material("ceramic coating", "#cba77b", 0, 0.65),
        orange: material("orange coating", "#d88a19", 0, 0.54),
        red: material("red coating", "#903b39", 0, 0.52),
        winding: material("winding coating", "#92502e", 0, 0.4),
        silk: material("printed ink", "#e0e8d7", 0, 0.84),
        marking: material("restrained package print", "#929993", 0, 0.9),
        darkMark: material("mold mark", "#111616", 0, 0.78),
    };
}

function positive(value, fallback, label) {
    const result = value ?? fallback;
    if (typeof result !== "number" || !Number.isFinite(result) || result <= 0 || result > 500) {
        throw new RangeError(`${label} must be a finite positive millimetre dimension up to 500`);
    }
    return result;
}

function count(value, fallback, multiple, label) {
    const result = value ?? fallback;
    if (!Number.isInteger(result) || result < multiple || result > 256 || result % multiple) {
        throw new RangeError(`${label} must be a positive multiple of ${multiple}, up to 256`);
    }
    return result;
}

function mesh(group, name, geometry, material, position = [0, 0, 0]) {
    const object = new THREE.Mesh(geometry, material);
    object.name = name;
    object.position.set(...position);
    object.castShadow = true;
    object.receiveShadow = true;
    group.add(object);
    return object;
}

function instances(group, name, geometry, material, transforms) {
    const object = new THREE.InstancedMesh(geometry, material, transforms.length);
    object.name = name;
    const transform = new THREE.Object3D();
    transforms.forEach(({ x = 0, y = 0, z = 0, angle = 0, scale = [1, 1, 1] }, index) => {
        transform.position.set(x, y, z);
        transform.rotation.set(0, 0, angle);
        transform.scale.set(...scale);
        transform.updateMatrix();
        object.setMatrixAt(index, transform.matrix);
    });
    object.instanceMatrix.needsUpdate = true;
    object.castShadow = true;
    object.receiveShadow = true;
    object.computeBoundingBox();
    object.computeBoundingSphere();
    group.add(object);
    return object;
}

/** Bevels stay inside the requested body box; no addon utility dependency. */
export function beveledBoxGeometry(width, depth, height, bevel = 0.1) {
    const edge = Math.min(bevel, width / 5, depth / 5, height / 3);
    const x = width / 2 - edge, y = depth / 2 - edge;
    const shape = new THREE.Shape();
    shape.moveTo(-x, -y); shape.lineTo(x, -y); shape.lineTo(x, y); shape.lineTo(-x, y); shape.closePath();
    const geometry = new THREE.ExtrudeGeometry(shape, { depth: height - edge * 2,
        bevelEnabled: true, bevelThickness: edge, bevelSize: edge, bevelSegments: 2, steps: 1, curveSegments: 1 });
    geometry.translate(0, 0, edge);
    return geometry;
}

/** A stamped gullwing cross-section, with shoulder, knee and flat solder foot. */
export function gullwingLeadGeometry(width = 0.25, shoulderHeight = 0.85, reach = 1.55) {
    const thickness = Math.min(0.13, shoulderHeight * 0.2);
    const foot = thickness / 2 + 0.045;
    const half = thickness / 2;
    const profile = new THREE.Shape();
    profile.moveTo(-0.09, shoulderHeight - half);
    profile.lineTo(reach * 0.18, shoulderHeight - half);
    profile.quadraticCurveTo(reach * 0.26, shoulderHeight - half, reach * 0.30, shoulderHeight - thickness * 1.2);
    profile.lineTo(reach * 0.55, foot + thickness * 0.4);
    profile.quadraticCurveTo(reach * 0.59, foot, reach * 0.67, foot);
    profile.lineTo(reach, foot);
    profile.lineTo(reach, foot + thickness);
    profile.lineTo(reach * 0.67, foot + thickness);
    profile.quadraticCurveTo(reach * 0.64, foot + thickness, reach * 0.61, foot + thickness * 1.4);
    profile.lineTo(reach * 0.37, shoulderHeight);
    profile.quadraticCurveTo(reach * 0.29, shoulderHeight + half, reach * 0.18, shoulderHeight + half);
    profile.lineTo(-0.09, shoulderHeight + half);
    profile.closePath();
    const geometry = new THREE.ExtrudeGeometry(profile, { depth: width,
        bevelEnabled: false, steps: 1, curveSegments: 4 });
    geometry.rotateX(Math.PI / 2);
    geometry.translate(0, width / 2, 0);
    return geometry;
}

const GLYPHS = Object.freeze({
    A: [14,17,17,31,17,17,17], B: [30,17,17,30,17,17,30], C: [14,17,16,16,16,17,14],
    D: [30,17,17,17,17,17,30], E: [31,16,16,30,16,16,31], F: [31,16,16,30,16,16,16],
    G: [14,17,16,23,17,17,15], H: [17,17,17,31,17,17,17], I: [14,4,4,4,4,4,14],
    J: [7,2,2,2,18,18,12], K: [17,18,20,24,20,18,17], L: [16,16,16,16,16,16,31],
    M: [17,27,21,21,17,17,17], N: [17,25,25,21,19,19,17], O: [14,17,17,17,17,17,14],
    P: [30,17,17,30,16,16,16], Q: [14,17,17,17,21,18,13], R: [30,17,17,30,20,18,17],
    S: [15,16,16,14,1,1,30], T: [31,4,4,4,4,4,4], U: [17,17,17,17,17,17,14],
    V: [17,17,17,17,17,10,4], W: [17,17,17,21,21,21,10], X: [17,17,10,4,10,17,17],
    Y: [17,17,10,4,4,4,4], Z: [31,1,2,4,8,16,31],
    0: [14,17,19,21,25,17,14], 1: [4,12,4,4,4,4,14], 2: [14,17,1,2,4,8,31],
    3: [30,1,1,14,1,1,30], 4: [2,6,10,18,31,2,2], 5: [31,16,16,30,1,1,30],
    6: [14,16,16,30,17,17,14], 7: [31,1,2,4,8,8,8], 8: [14,17,17,14,17,17,14],
    9: [14,17,17,15,1,1,14], "-": [0,0,0,31,0,0,0],
});

/** Single planar mesh for restrained authored labels. No canvas/font download. */
export function markingGeometry(label, width, letterHeight = 0.8) {
    const lines = String(label).toUpperCase().slice(0, 80).split("\n").slice(0, 3);
    const longest = Math.max(1, ...lines.map((line) => line.length));
    const dot = Math.min(letterHeight / 7, width / (longest * 6));
    const vertices = [], normals = [];
    lines.forEach((line, row) => [...line].forEach((character, column) => {
        (GLYPHS[character] || []).forEach((bits, y) => {
            for (let x = 0; x < 5; x += 1) {
                if (!(bits & (1 << (4 - x)))) continue;
                const left = (column * 6 + x - (line.length * 6 - 1) / 2) * dot;
                const top = ((lines.length * 10 - 3) / 2 - row * 10 - y) * dot;
                const right = left + dot * 0.82, bottom = top - dot * 0.82;
                vertices.push(left,bottom,0, right,bottom,0, right,top,0, left,bottom,0, right,top,0, left,top,0);
                for (let index = 0; index < 6; index += 1) normals.push(0, 0, 1);
            }
        });
    }));
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
    return geometry;
}

function qfp(group, options, materials) {
    const width = positive(options.width, 14, "width"), depth = positive(options.depth, 14, "depth");
    const height = positive(options.height, 1.5, "height"), leadCount = count(options.leadCount, 64, 4, "leadCount");
    const perSide = leadCount / 4, reach = Math.min(width, depth) * 0.11;
    const clearance = Math.min(0.32, height * 0.2), shoulder = clearance + height * 0.4;
    const pitch = (Math.min(width, depth) - 0.8) / (perSide + 1);
    if (pitch < 0.15) throw new RangeError("The selected lead count does not fit this package illustration");
    const leadWidth = Math.min(0.32, pitch * 0.48);
    mesh(group, "beveled resin body", beveledBoxGeometry(width, depth, height, 0.19), materials.resin, [0, 0, clearance]);
    const leads = [], feet = [];
    for (let side = 0; side < 4; side += 1) {
        const angle = side * Math.PI / 2;
        const radius = (side % 2 ? depth : width) / 2;
        for (let pin = 0; pin < perSide; pin += 1) {
            const along = (pin - (perSide - 1) / 2) * pitch;
            const x = Math.cos(angle) * radius - Math.sin(angle) * along;
            const y = Math.sin(angle) * radius + Math.cos(angle) * along;
            leads.push({ x, y, angle });
            feet.push({ x: x + Math.cos(angle) * reach * 0.85,
                y: y + Math.sin(angle) * reach * 0.85, angle });
        }
    }
    instances(group, "individual gullwing leads", gullwingLeadGeometry(leadWidth, shoulder, reach), materials.lead, leads);
    if (options.includeSolder !== false) instances(group, "illustrative solder feet",
        beveledBoxGeometry(reach * 0.56, leadWidth * 1.8, 0.12, 0.04), materials.solder, feet);
    mesh(group, "generic orientation mold dot", new THREE.CircleGeometry(Math.min(width, depth) * 0.029, 24),
        materials.darkMark, [-width * 0.36, -depth * 0.36, clearance + height + 0.003]);
    if (options.label !== false) mesh(group, "authored sample marking",
        markingGeometry(options.label ?? "OHMNI\nSAMPLE", width * 0.63, Math.min(0.85, depth * 0.065)),
        materials.marking, [0, 0, clearance + height + 0.005]);
    group.userData.dimensions = { width, depth, height: height + clearance, leadReach: reach };
    group.userData.leadCount = leadCount;
}

function header(group, options, materials) {
    const width = positive(options.width, 30, "width"), depth = positive(options.depth, 5.2, "depth");
    const height = positive(options.height, 6, "height"), contactCount = count(options.contactCount, 24, 1, "contactCount");
    const rows = options.rows ?? (contactCount % 2 === 0 ? 2 : 1);
    if (![1, 2].includes(rows) || contactCount % rows) throw new RangeError("Header rows must divide the explicit contact count");
    const columns = contactCount / rows, wall = Math.min(0.65, depth * 0.13, height * 0.13);
    const floor = Math.min(0.65, height * 0.16), pitch = (width - wall * 2) / (columns + 1);
    const pinWidth = Math.min(0.45, pitch * 0.28, depth * 0.1);
    mesh(group, "recess floor", beveledBoxGeometry(width, depth, floor, 0.10), materials.plastic);
    for (const side of [-1, 1]) {
        mesh(group, `long cavity wall ${side}`, beveledBoxGeometry(width, wall, height - floor, 0.09),
            materials.plastic, [0, side * (depth - wall) / 2, floor]);
        mesh(group, `end cavity wall ${side}`, beveledBoxGeometry(wall, depth - 2 * wall, height - floor, 0.09),
            materials.plastic, [side * (width - wall) / 2, 0, floor]);
    }
    const contacts = [], tails = [], solder = [];
    for (let row = 0; row < rows; row += 1) {
        const side = row === 0 ? -1 : 1;
        const y = rows === 1 ? 0 : side * depth * 0.22;
        for (let column = 0; column < columns; column += 1) {
            const x = (column - (columns - 1) / 2) * pitch;
            contacts.push({ x, y, z: floor * 0.7 });
            const end = side * (depth / 2 + 0.55);
            tails.push({ x, y: (y + end) / 2 });
            solder.push({ x, y: end });
        }
    }
    instances(group, "individual recessed gold contacts", beveledBoxGeometry(pinWidth, pinWidth,
        height * 0.78 - floor * 0.7, 0.055), materials.gold, contacts);
    const tailLength = depth / 2 + 0.55 - (rows === 1 ? 0 : depth * 0.22);
    instances(group, "contact solder tails", beveledBoxGeometry(pinWidth, tailLength, 0.19, 0.04), materials.lead, tails);
    if (options.includeSolder !== false) instances(group, "illustrative contact solder",
        beveledBoxGeometry(pinWidth * 1.7, 0.8, 0.12, 0.035), materials.solder, solder);
    group.userData.dimensions = { width, depth, height };
    group.userData.contactCount = contactCount;
    group.userData.rows = rows;
    group.userData.cavity = { width: width - 2 * wall, depth: depth - 2 * wall, floor, top: height };
}

function latheGeometry(points, segments = 40) {
    const geometry = new THREE.LatheGeometry(points.map(([radius, z]) => new THREE.Vector2(radius, z)), segments);
    geometry.rotateX(Math.PI / 2);
    return geometry;
}

function aluminumCan(group, options, materials) {
    const width = positive(options.width, 6, "width"), depth = positive(options.depth, width, "depth");
    const height = positive(options.height, 7, "height"), radius = width / 2;
    const base = Math.min(0.42, height * 0.1), lip = Math.min(0.12, radius * 0.07, height * 0.035);
    mesh(group, "can insulator base", beveledBoxGeometry(width * 1.07, depth * 1.07, base, 0.12), materials.plastic);
    const body = mesh(group, "formed aluminum can wall", latheGeometry([
        [radius * 0.85, base * 0.8], [radius * 0.95, base], [radius, base + lip * 2],
        [radius, height - lip * 3], [radius * 0.97, height - lip], [radius * 0.90, height - lip * 0.4],
    ]), materials.aluminum);
    body.scale.y = depth / width;
    const top = mesh(group, "inset aluminum lid", new THREE.CircleGeometry(radius * 0.92, 40), materials.aluminum,
        [0, 0, height - lip * 0.5]);
    top.scale.y = depth / width;
    const rim = mesh(group, "rolled can rim", new THREE.TorusGeometry(radius * 0.95, lip, 8, 40), materials.shield,
        [0, 0, height - lip]);
    rim.scale.y = depth / width;
    const skirt = mesh(group, "lower rolled bead", new THREE.TorusGeometry(radius * 0.98, lip * 0.65, 8, 40), materials.aluminum,
        [0, 0, base + lip * 2]);
    skirt.scale.y = depth / width;
    if (options.includeSolder !== false) instances(group, "illustrative can solder tabs",
        beveledBoxGeometry(width * 0.24, depth * 0.28, 0.14, 0.04), materials.solder,
        [{ x: -width * 0.48 }, { x: width * 0.48 }]);
    if (options.label !== false) mesh(group, "authored can marking",
        markingGeometry(options.label ?? "SAMPLE", width * 0.7, Math.min(0.65, width * 0.10)),
        materials.marking, [0, 0, height - lip * 0.5 + 0.004]);
    group.userData.dimensions = { width, depth, height };
}

function axialResistor(group, options, materials) {
    const width = positive(options.width, 6, "width"), depth = positive(options.depth, 2.2, "depth");
    const height = positive(options.height, 3, "height"), radius = depth / 2;
    if (height <= depth) throw new RangeError("Axial height must leave clearance below its body");
    const z = height - radius, wireRadius = Math.min(0.15, radius * 0.16);
    const profile = [[0, -width / 2], [radius * 0.45, -width / 2], [radius * 0.85, -width * 0.46],
        [radius, -width * 0.36], [radius, width * 0.36], [radius * 0.85, width * 0.46],
        [radius * 0.45, width / 2], [0, width / 2]];
    const body = mesh(group, "rounded blue axial body", latheGeometry(profile, 24), materials.blue, [0, 0, z]);
    body.rotation.y = Math.PI / 2;
    const bands = options.bandColors ?? ["#293541", "#3c4350", "#313a50", "#8b794e"];
    if (!Array.isArray(bands) || bands.length > 6) throw new RangeError("At most six illustrative bands are supported");
    bands.forEach((color, index) => {
        const bandMaterial = materials.blue.clone();
        bandMaterial.color.set(color); bandMaterial.name = "illustrative resistor band";
        const band = mesh(group, `illustrative band ${index + 1}`,
            new THREE.CylinderGeometry(radius + 0.014, radius + 0.014, width * 0.044, 24, 1, true), bandMaterial,
            [(index - (bands.length - 1) / 2) * width * 0.17, 0, z]);
        band.rotation.z = Math.PI / 2;
    });
    const reach = Math.max(1.5, depth * 0.95), start = width / 2;
    const path = new THREE.CurvePath();
    const v = (x, h) => new THREE.Vector3(x, 0, h);
    path.add(new THREE.LineCurve3(v(start - 0.12, z), v(start + reach * 0.26, z)));
    path.add(new THREE.QuadraticBezierCurve3(v(start + reach * 0.26, z),
        v(start + reach * 0.65, z), v(start + reach * 0.65, z - Math.min(0.65, z * 0.35))));
    path.add(new THREE.LineCurve3(path.curves.at(-1).v2, v(start + reach * 0.65, wireRadius + 0.38)));
    path.add(new THREE.QuadraticBezierCurve3(v(start + reach * 0.65, wireRadius + 0.38),
        v(start + reach * 0.65, wireRadius), v(start + reach * 0.87, wireRadius)));
    path.add(new THREE.LineCurve3(v(start + reach * 0.87, wireRadius), v(start + reach, wireRadius)));
    instances(group, "two bent axial leads", new THREE.TubeGeometry(path, 24, wireRadius, 8, false), materials.lead,
        [{}, { angle: Math.PI }]);
    if (options.includeSolder !== false) instances(group, "illustrative axial solder feet",
        beveledBoxGeometry(reach * 0.5, wireRadius * 4.5, 0.13, 0.045), materials.solder,
        [{ x: start + reach * 0.86 }, { x: -start - reach * 0.86 }]);
    group.userData.dimensions = { width, depth, height, leadReach: reach };
    group.userData.bandsAreIllustrative = true;
}

function dimensionSet(options, defaults) {
    return Object.fromEntries(["width", "depth", "height"].map((key, index) =>
        [key, positive(options[key], defaults[index], key)]));
}

function printOn(group, label, width, height, material, z, position = [0, 0]) {
    if (label === false || label === "") return;
    mesh(group, "authored package marking", markingGeometry(label, width, height), material, [...position, z]);
}

function smallOutline(group, options, materials, few = false) {
    const { width, depth, height } = dimensionSet(options, few ? [3.2, 1.8, 1.15] : [8, 4, 1.4]);
    const leadCount = count(options.leadCount, few ? 3 : 16, few ? 1 : 2, "leadCount");
    const clearance = Math.min(0.25, height * 0.18), reach = Math.min(1.45, depth * 0.38);
    const largestRow = Math.ceil(leadCount / 2), pitch = width / (largestRow + 1);
    const leadWidth = Math.min(0.48, pitch * 0.43);
    mesh(group, "small-outline molded body", beveledBoxGeometry(width, depth, height, 0.14), materials.resin, [0, 0, clearance]);
    const leads = [], feet = [];
    for (let row = 0; row < 2; row += 1) {
        const side = row === 0 ? -1 : 1, number = row === 0 ? largestRow : leadCount - largestRow;
        for (let index = 0; index < number; index += 1) {
            const x = (index - (number - 1) / 2) * pitch;
            leads.push({ x, y: side * depth / 2, angle: side * Math.PI / 2 });
            feet.push({ x, y: side * (depth / 2 + reach * 0.84), angle: side * Math.PI / 2 });
        }
    }
    instances(group, "individual small-outline leads", gullwingLeadGeometry(leadWidth, clearance + height * 0.38, reach), materials.lead, leads);
    if (options.includeSolder !== false) instances(group, "illustrative small-outline solder",
        beveledBoxGeometry(reach * 0.55, leadWidth * 1.6, 0.11, 0.035), materials.solder, feet);
    mesh(group, "generic mold orientation dot", new THREE.CircleGeometry(Math.min(width, depth) * 0.08, 16),
        materials.darkMark, [-width * 0.35, -depth * 0.25, clearance + height + 0.003]);
    printOn(group, options.label ?? (few ? "" : "OHMNI"), width * 0.7,
        Math.min(0.6, depth * 0.2), materials.marking, clearance + height + 0.005);
    group.userData.dimensions = { width, depth, height: height + clearance, leadReach: reach };
    group.userData.leadCount = leadCount;
}

/** Source pads are local footprint coordinates, not a guessed pitch/count. */
function validSourcePads(options) {
    if (options.pads === undefined) return [];
    if (!Array.isArray(options.pads) || options.pads.length > 256) throw new RangeError("pads must be a bounded source-pad array");
    return options.pads.filter((pad) => {
        if (!pad || ![pad.x_mm, pad.y_mm, pad.width_mm, pad.height_mm].every(Number.isFinite)
                || pad.width_mm <= 0 || pad.height_mm <= 0) throw new RangeError("Source pads need finite coordinates and positive dimensions");
        return pad.kind !== "np_thru_hole";
    });
}

function sourceContacts(group, options, materials, { width, depth, height, leaded = false }) {
    const pads = validSourcePads(options), feet = [], leads = [], identities = [];
    const renderedPads = new Set();
    for (const pad of pads) {
        identities.push({ number: pad.number ?? null, x_mm: pad.x_mm, y_mm: pad.y_mm });
        // KiCad can give one physical land multiple electrical identities (for
        // example USB-C A/B contacts). Preserve every identity but draw that
        // identical land once, avoiding coplanar duplicate metal surfaces.
        const geometryKey = JSON.stringify([pad.x_mm, pad.y_mm, pad.width_mm, pad.height_mm, pad.kind]);
        if (renderedPads.has(geometryKey)) continue;
        renderedPads.add(geometryKey);
        const endX = pad.x_mm, endY = pad.y_mm;
        const x = Math.max(-width / 2, Math.min(width / 2, endX));
        const y = Math.max(-depth / 2, Math.min(depth / 2, endY));
        const reach = Math.hypot(endX - x, endY - y);
        const leadWidth = Math.min(pad.width_mm, pad.height_mm) * 0.52;
        if (leaded && reach > 0.04) {
            leads.push({ x, y, angle: Math.atan2(endY - y, endX - x),
                scale: [reach, leadWidth, Math.max(0.24, height * 0.4)] });
        } else {
            feet.push({ x: endX, y: endY, z: 0.10,
                scale: [pad.width_mm * 0.65, pad.height_mm * 0.65, 0.14] });
        }
    }
    if (leads.length) instances(group, "source-pad-derived bent terminals",
        gullwingLeadGeometry(1, 1, 1), materials.lead, leads);
    if (feet.length) instances(group, "source-pad-derived terminations", new THREE.BoxGeometry(1, 1, 1), materials.lead, feet);
    group.userData.contactBasis = "source-pads";
    group.userData.sourceContacts = identities;
    group.userData.renderedSourceTerminalCount = renderedPads.size;
}

function leadlessBlock(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [3.6, 3, 0.7]);
    mesh(group, "flat leadless resin body", beveledBoxGeometry(width, depth, height, 0.09), materials.resin, [0, 0, 0.1]);
    const number = options.leadCount === 0 ? 0 : count(options.leadCount, 8, 1, "leadCount");
    const terminals = [];
    for (let index = 0; index < number; index += 1) {
        const side = index % 2 ? 1 : -1, row = Math.floor(index / 2), rowSize = Math.ceil(number / 2);
        terminals.push({ x: (row - (rowSize - 1) / 2) * width / (rowSize + 1), y: side * depth * 0.47,
            z: 0.11, scale: [Math.min(0.42, width / (rowSize * 2)), depth * 0.16, 0.16] });
    }
    if (terminals.length) instances(group, "leadless edge terminations", new THREE.BoxGeometry(1, 1, 1), materials.lead, terminals);
    printOn(group, options.label ?? "", width * 0.74, Math.min(0.6, depth * 0.2), materials.marking, height + 0.106);
    group.userData.dimensions = { width, depth, height: height + 0.1 };
    group.userData.leadCount = number;
}

function whiteConnector(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [11, 7, 6]);
    const contactCount = count(options.contactCount, 6, 1, "contactCount");
    const wall = Math.min(0.65, depth * 0.15, width * 0.12), floor = height * 0.15;
    mesh(group, "connector insulated floor", beveledBoxGeometry(width, depth, floor, 0.13), materials.whitePlastic);
    mesh(group, "connector rear wall", beveledBoxGeometry(width, wall, height - floor, 0.12), materials.whitePlastic,
        [0, -depth / 2 + wall / 2, floor]);
    for (const side of [-1, 1]) {
        mesh(group, "connector keyed side wall", beveledBoxGeometry(wall, depth, height - floor, 0.12), materials.whitePlastic,
            [side * (width - wall) / 2, 0, floor]);
    }
    mesh(group, "front retention lip", beveledBoxGeometry(width - 2 * wall, wall, height * 0.23, 0.08), materials.whitePlastic,
        [0, depth / 2 - wall / 2, floor]);
    mesh(group, "raised rear latch", beveledBoxGeometry(width * 0.32, wall * 1.7, height * 0.12, 0.07), materials.whitePlastic,
        [0, -depth / 2, height * 0.65]);
    const contacts = [], solder = [];
    for (let index = 0; index < contactCount; index += 1) {
        const x = (index - (contactCount - 1) / 2) * (width - wall * 2) / (contactCount + 1);
        contacts.push({ x, y: -depth * 0.15, z: floor + 0.06 });
        solder.push({ x, y: -depth * 0.48 });
    }
    instances(group, "individual interior connector contacts", beveledBoxGeometry(Math.min(0.42, width / (contactCount * 2)),
        depth * 0.40, height * 0.12, 0.035), materials.gold, contacts);
    if (options.includeSolder !== false) instances(group, "illustrative connector solder tails",
        beveledBoxGeometry(Math.min(0.7, width / (contactCount * 1.5)), depth * 0.26, 0.13, 0.035), materials.solder, solder);
    group.userData.dimensions = { width, depth, height };
    group.userData.contactCount = contactCount;
    group.userData.cavity = { width: width - 2 * wall, depth: depth - 2 * wall, floor, top: height };
}

function rectangleWithRoundCorners(width, height, radius, x = -width / 2, y = 0) {
    const shape = new THREE.Shape(), right = x + width, top = y + height;
    shape.moveTo(x + radius, y); shape.lineTo(right - radius, y);
    shape.quadraticCurveTo(right, y, right, y + radius); shape.lineTo(right, top - radius);
    shape.quadraticCurveTo(right, top, right - radius, top); shape.lineTo(x + radius, top);
    shape.quadraticCurveTo(x, top, x, top - radius); shape.lineTo(x, y + radius);
    shape.quadraticCurveTo(x, y, x + radius, y); shape.closePath();
    return shape;
}

function shieldedConnector(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [13, 10, 5.5]);
    const wall = Math.min(0.3, height * 0.09), radius = Math.min(width * 0.095, depth * 0.14);
    const roof = new THREE.Shape();
    roof.moveTo(-width / 2, -depth / 2); roof.lineTo(width / 2, -depth / 2);
    roof.lineTo(width / 2, depth / 2); roof.lineTo(-width / 2, depth / 2); roof.closePath();
    for (const side of [-1, 1]) {
        const hole = new THREE.Path(); hole.absarc(side * width * 0.21, depth * 0.03, radius, 0, Math.PI * 2, true);
        roof.holes.push(hole);
    }
    mesh(group, "sheet metal roof with two open apertures", new THREE.ExtrudeGeometry(roof,
        { depth: wall, bevelEnabled: false, curveSegments: 20 }), materials.shield, [0, 0, height - wall]);
    for (const side of [-1, 1]) {
        mesh(group, "folded shell side", beveledBoxGeometry(wall, depth, height - wall, wall * 0.2), materials.shield,
            [side * (width - wall) / 2, 0, 0]);
        mesh(group, "shell front seam", beveledBoxGeometry(wall * 0.65, depth * 0.2, height * 0.85, wall * 0.1), materials.lead,
            [side * (width * 0.47), depth * 0.43, 0]);
    }
    mesh(group, "shell bottom fold", beveledBoxGeometry(width, depth, wall, 0.06), materials.shield);
    mesh(group, "recessed rear insert", beveledBoxGeometry(width - wall * 2, wall * 2, height * 0.66, 0.08), materials.plastic,
        [0, -depth / 2 + wall, 0.2]);
    mesh(group, "recessed internal tongue", beveledBoxGeometry(width * 0.68, depth * 0.66, height * 0.15, 0.1), materials.plastic,
        [0, -depth * 0.13, height * 0.34]);
    if (options.includeSolder !== false) instances(group, "illustrative shell anchor feet",
        beveledBoxGeometry(width * 0.15, depth * 0.2, 0.16, 0.05), materials.solder,
        [{ x: -width * 0.49, y: -depth * 0.25 }, { x: width * 0.49, y: -depth * 0.25 }]);
    group.userData.dimensions = { width, depth, height };
    group.userData.apertures = [-1, 1].map((side) => ({ x: side * width * 0.21, y: depth * 0.03, radius }));
    group.userData.electricalIdentity = "UNKNOWN";
}

function rearMetalBlock(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [7, 4, 10]);
    mesh(group, "ambiguous metal body", beveledBoxGeometry(width, depth, height, 0.22), materials.shield);
    mesh(group, "inset metal panel", beveledBoxGeometry(width * 0.76, 0.13, height * 0.74, 0.025), materials.aluminum,
        [0, depth / 2 + 0.025, height * 0.1]);
    mesh(group, "panel upper seam", beveledBoxGeometry(width * 0.77, 0.16, height * 0.022, 0.01), materials.darkMark,
        [0, depth / 2 + 0.02, height * 0.84]);
    group.userData.dimensions = { width, depth, height };
    group.userData.electricalIdentity = "UNKNOWN";
}

function electrolyticCan(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [6.5, 6.5, 13]);
    aluminumCan(group, { ...options, width, depth, height, label: false }, materials);
    group.getObjectByName("formed aluminum can wall").material = materials.sleeve;
    // This is generic sample print, not a decoded voltage/capacitance/polarity.
    const marking = mesh(group, "illustrative sleeve print", markingGeometry(options.label === false ? "" : options.label ?? "OHMNI\nSAMPLE",
        width * 0.55, Math.min(0.7, height * 0.045)), materials.marking, [0, -depth / 2 - 0.015, height * 0.48]);
    marking.rotation.x = Math.PI / 2;
    group.userData.sleeveMarkingsAreIllustrative = true;
}

function woundInductor(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [6, 6, 8]);
    const turns = count(options.turnCount, 9, 1, "turnCount"), radius = Math.min(width, depth) * 0.4;
    const wireRadius = Math.min((height - 0.9) / (turns * 2.25), radius * 0.13);
    if (wireRadius <= 0) throw new RangeError("Wound asset height must exceed 0.9 mm");
    mesh(group, "dark winding core", latheGeometry([[0, 0.2], [radius * 0.94, 0.2], [radius * 0.94, height], [0, height]], 32), materials.resin);
    class Helix extends THREE.Curve {
        getPoint(t, target = new THREE.Vector3()) {
            const angle = t * turns * Math.PI * 2;
            return target.set(Math.cos(angle) * radius, Math.sin(angle) * radius * depth / width,
                0.45 + wireRadius + t * (height - 0.85 - wireRadius * 2));
        }
    }
    mesh(group, "continuous helical winding", new THREE.TubeGeometry(new Helix(), turns * 16, wireRadius, 6, false), materials.winding);
    instances(group, "illustrative coil terminal feet", beveledBoxGeometry(width * 0.2, depth * 0.24, 0.2, 0.05), materials.lead,
        [{ x: -width * 0.42 }, { x: width * 0.42 }]);
    group.userData.dimensions = { width, depth, height };
    group.userData.turnCount = turns;
    group.userData.windingIsIllustrative = true;
}

function coatedRadial(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [3, 2.6, 6]);
    const foot = Math.min(0.6, height * 0.15), radius = width / 2;
    const body = mesh(group, "rounded coated radial body", latheGeometry([[0, foot], [radius * 0.55, foot],
        [radius, foot + width * 0.18], [radius, height - width * 0.16], [radius * 0.7, height], [0, height]], 24), materials.orange);
    body.scale.y = depth / width;
    instances(group, "two radial support leads", beveledBoxGeometry(width * 0.1, depth * 0.1, foot + 0.04, 0.025), materials.lead,
        [{ x: -width * 0.23 }, { x: width * 0.23 }]);
    group.userData.dimensions = { width, depth, height };
    group.userData.electricalIdentity = "UNKNOWN";
}

function goldPost(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [2.4, 2.4, 4.4]);
    const radius = width / 2;
    const post = mesh(group, "gold stem and machined collars", latheGeometry([[0, 0.12], [radius * 0.9, 0.12],
        [radius * 0.9, 0.4], [radius * 0.57, 0.55], [radius * 0.36, 0.65], [radius * 0.36, height * 0.7],
        [radius * 0.48, height * 0.74], [radius * 0.48, height * 0.85], [radius * 0.25, height * 0.9],
        [radius * 0.25, height], [0, height]], 24), materials.gold);
    post.scale.y = depth / width;
    mesh(group, "post insulating foot", beveledBoxGeometry(width, depth, 0.15, 0.055), materials.plastic);
    group.userData.dimensions = { width, depth, height };
    group.userData.electricalIdentity = "UNKNOWN";
}

function chipBody(group, options, materials, material = "tan") {
    const { width, depth, height } = dimensionSet(options, [2.4, 1.4, 0.9]);
    mesh(group, "chip dielectric body", beveledBoxGeometry(width, depth, height, Math.min(0.14, height * 0.18)), materials[material], [0, 0, 0.1]);
    if (options.pads !== undefined || options.actual === true) sourceContacts(group, options, materials, { width, depth, height });
    else {
        instances(group, "two metal chip terminations", beveledBoxGeometry(width * 0.19, depth * 1.02, height * 0.88, 0.055), materials.lead,
            [{ x: -width * 0.43, z: 0.075 }, { x: width * 0.43, z: 0.075 }]);
    }
    group.userData.dimensions = { width, depth, height: height + 0.1 };
}

function ceramicChip(group, options, materials) {
    const shape = options.bodyShape ?? "chip";
    if (!["chip", "axial"].includes(shape)) throw new RangeError("Ceramic bodyShape must be chip or axial");
    if (shape === "axial") {
        if (options.actual === true || options.pads !== undefined) {
            throw new RangeError("The tan axial illustration has no actual-footprint binding");
        }
        axialResistor(group, { ...options, bandColors: [] }, { ...materials, blue: materials.tan });
        group.getObjectByName("rounded blue axial body").name = "rounded tan axial body";
    } else chipBody(group, options, materials);
    group.userData.bodyShape = shape;
}

function unresolvedPatch(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [2, 1, 0.05]);
    // One faint surface patch: never a guessed collection of hidden components.
    mesh(group, "unresolved surface detail", beveledBoxGeometry(width, depth, height, height * 0.2), materials.trace);
    group.userData.dimensions = { width, depth, height };
    group.userData.electricalIdentity = "UNKNOWN";
    group.userData.isComponent = false;
}

function esp32Module(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [19.5, 20.5, 2.8]);
    const base = Math.min(0.5, height * 0.2), shieldDepth = depth * 0.73;
    mesh(group, "module substrate", beveledBoxGeometry(width, depth, base, 0.08), materials.mask);
    mesh(group, "module shield rolled base", beveledBoxGeometry(width * 0.94, shieldDepth, 0.16, 0.05), materials.lead,
        [0, -depth * 0.105, base]);
    mesh(group, "module RF shield", beveledBoxGeometry(width * 0.92, shieldDepth * 0.985, height - base, 0.2), materials.shield,
        [0, -depth * 0.105, base]);
    printOn(group, options.label ?? "ESP32 MODULE", width * 0.75, 0.8, materials.marking, height + 0.004, [0, -depth * 0.105]);
    sourceContacts(group, options, materials, { width, depth, height: base });
    group.userData.dimensions = { width, depth, height };
}

function usbC(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [9.5, 7.5, 3.4]);
    const wall = Math.min(0.25, height * 0.085), shape = rectangleWithRoundCorners(width, height, height * 0.28);
    shape.holes.push(rectangleWithRoundCorners(width - wall * 2, height - wall * 2, height * 0.23,
        -width / 2 + wall, wall));
    const shellGeometry = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false, curveSegments: 12 });
    shellGeometry.rotateX(Math.PI / 2); shellGeometry.translate(0, depth / 2, 0);
    mesh(group, "open oval USB-C metal shell", shellGeometry, materials.shield);
    mesh(group, "USB-C rear insert", beveledBoxGeometry(width * 0.84, depth * 0.18, height * 0.76, 0.11), materials.plastic,
        [0, -depth * 0.38, height * 0.1]);
    mesh(group, "USB-C polymer tongue", beveledBoxGeometry(width * 0.74, depth * 0.75, height * 0.16, 0.1), materials.plastic,
        [0, 0, height * 0.42]);
    sourceContacts(group, options, materials, { width: width * 0.9, depth: depth * 0.86, height, leaded: true });
    group.userData.dimensions = { width, depth, height };
    group.userData.cavity = { width: width - wall * 2, height: height - wall * 2, openingY: depth / 2 };
}

function pinHeader(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [2.54, 15.24, 6]);
    const pads = validSourcePads(options);
    // Individual insulators follow the actual pin locations, including a
    // footprint whose anchor is its first pin rather than its body centre.
    const pins = [], blocks = [];
    const housingHeight = Math.min(1.7, height * 0.34);
    for (const pad of pads) {
        const pinWidth = Math.min(0.55, pad.width_mm * 0.65, pad.height_mm * 0.65);
        pins.push({ x: pad.x_mm, y: pad.y_mm, z: 0.02, scale: [pinWidth, pinWidth, height - 0.02] });
        blocks.push({ x: pad.x_mm, y: pad.y_mm });
    }
    if (pads.length) {
        instances(group, "source-position header insulators", beveledBoxGeometry(Math.min(width, 2.54), Math.min(depth, 2.54), housingHeight, 0.14), materials.plastic, blocks);
        instances(group, "source-position gold header pins", beveledBoxGeometry(1, 1, 1, 0.1), materials.gold, pins);
    } else mesh(group, "header body with unspecified contacts", beveledBoxGeometry(width, depth, housingHeight, 0.1), materials.plastic);
    group.userData.dimensions = { width, depth, height };
    group.userData.contactBasis = "source-pads";
    group.userData.sourceContacts = pads.map((pad) => ({ number: pad.number ?? null, x_mm: pad.x_mm, y_mm: pad.y_mm }));
}

function tactileSwitch(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [9.5, 7.5, 3.8]);
    const bodyWidth = width * 0.65, bodyDepth = depth * 0.76;
    mesh(group, "switch molded base", beveledBoxGeometry(bodyWidth, bodyDepth, height * 0.49, 0.15), materials.plastic);
    mesh(group, "switch folded metal lid", beveledBoxGeometry(bodyWidth * 0.97, bodyDepth * 0.97, height * 0.13, 0.1), materials.shield,
        [0, 0, height * 0.48]);
    const radius = Math.min(bodyWidth, bodyDepth) * 0.24;
    mesh(group, "switch raised plunger", latheGeometry([[0, height * 0.58], [radius, height * 0.58],
        [radius, height * 0.92], [radius * 0.82, height], [0, height]], 24), materials.resin);
    sourceContacts(group, options, materials, { width: bodyWidth, depth: bodyDepth, height, leaded: true });
    group.userData.dimensions = { width, depth, height };
}

function led(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [2, 1.5, 0.8]);
    mesh(group, "LED molded ceramic base", beveledBoxGeometry(width, depth, height * 0.55, 0.075), materials.whitePlastic);
    const lensMaterial = materials.mask.clone(); lensMaterial.color.set(options.color ?? "#4e9264"); lensMaterial.roughness = 0.27;
    mesh(group, "non-emissive LED lens", beveledBoxGeometry(width * 0.58, depth * 0.63, height * 0.52, 0.09), lensMaterial,
        [0, 0, height * 0.48]);
    sourceContacts(group, options, materials, { width, depth, height });
    group.userData.dimensions = { width, depth, height };
}

function sensor(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [2.5, 2.5, 1.1]);
    mesh(group, "sensor carrier", beveledBoxGeometry(width, depth, height * 0.28, 0.06), materials.resin);
    mesh(group, "sensor metal package", beveledBoxGeometry(width * 0.94, depth * 0.94, height * 0.75, 0.09), materials.aluminum,
        [0, 0, height * 0.25]);
    sourceContacts(group, options, materials, { width, depth, height });
    group.userData.dimensions = { width, depth, height };
}

function regulator(group, options, materials) {
    const { width, depth, height } = dimensionSet(options, [3, 3.2, 1.15]);
    const bodyWidth = width * 0.54, bodyDepth = depth * 0.68;
    mesh(group, "regulator molded body", beveledBoxGeometry(bodyWidth, bodyDepth, height, 0.10), materials.resin, [0, 0, 0.1]);
    sourceContacts(group, options, materials, { width: bodyWidth, depth: bodyDepth, height: height + 0.1, leaded: true });
    group.userData.dimensions = { width, depth, height: height + 0.1 };
}

const FACTORIES = Object.freeze({ qfp, header, aluminum_can: aluminumCan, axial_resistor: axialResistor,
    small_outline: smallOutline, few_terminal: (g, o, m) => smallOutline(g, o, m, true), leadless_block: leadlessBlock,
    white_connector: whiteConnector, shielded_connector: shieldedConnector, rear_metal_block: rearMetalBlock,
    electrolytic_can: electrolyticCan, wound_inductor: woundInductor, coated_radial: coatedRadial, gold_post: goldPost,
    coated_axial: (g, o, m) => axialResistor(g, { ...o, bandColors: [] }, m),
    ceramic_chip: ceramicChip, coated_red: (g, o, m) => chipBody(g, o, m, "red"), unresolved_patch: unresolvedPatch,
    esp32_module: esp32Module, usb_c: usbC, pin_header: pinHeader, switch: tactileSwitch, led, sensor, regulator,
    chip_resistor: (g, o, m) => chipBody(g, { ...o, pads: o.pads ?? [] }, m, "resin") });

const COLOR_MATERIAL = Object.freeze({ qfp: "resin", header: "plastic", aluminum_can: "aluminum", axial_resistor: "blue",
    small_outline: "resin", few_terminal: "resin", leadless_block: "resin", white_connector: "whitePlastic",
    shielded_connector: "shield", rear_metal_block: "shield", electrolytic_can: "sleeve", wound_inductor: "winding",
    coated_radial: "orange", gold_post: "gold", coated_axial: "blue", ceramic_chip: "tan", coated_red: "red",
    unresolved_patch: "trace", esp32_module: "mask", usb_c: "shield", pin_header: "plastic", switch: "plastic",
    led: "mask", sensor: "aluminum", regulator: "resin", chip_resistor: "resin" });

/** Shared materials belong to the caller; all geometries belong to this group. */
export function createAsset(family, options = {}, materials = createMaterials()) {
    if (!Object.hasOwn(FACTORIES, family)) throw new RangeError(`Unknown visual asset family: ${family}`);
    const factory = FACTORIES[family];
    const group = new THREE.Group();
    group.name = `${family} package illustration`;
    group.userData = { assetFamily: family, assetVersion: ASSET_VERSION,
        appearanceOnly: true, dimensionsAreIllustrative: true, source: ASSET_SOURCE, label: options.label ?? null };
    let palette = materials;
    if (options.color !== undefined) {
        const key = COLOR_MATERIAL[family];
        const custom = materials[key].clone(); custom.color.set(options.color);
        palette = { ...materials, [key]: custom };
    }
    factory(group, options, palette);
    return group;
}
