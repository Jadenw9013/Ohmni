// Small, local WebGL consumer of the display mesh. No library, CDN, textures,
// model inference or network path. Buffers are uploaded only when scene/view
// options change; orbiting only updates the camera uniforms and three draws.

import { VERTEX_STRIDE } from "./board-renderer-geometry.js";

const VERTEX = `
precision highp float;
attribute vec3 aPosition;
attribute vec3 aNormal;
attribute vec3 aColor;
attribute vec3 aMaterial;
uniform vec4 uCamera;
uniform vec4 uViewport;
uniform vec2 uPan;
varying vec3 vPosition;
varying vec3 vNormal;
varying vec3 vColor;
varying vec3 vMaterial;
varying float vPixelScale;
void main() {
    float cy = cos(uCamera.x), sy = sin(uCamera.x);
    float cp = cos(uCamera.y), sp = sin(uCamera.y);
    float x = aPosition.x * cy - aPosition.y * sy;
    float y = aPosition.x * sy + aPosition.y * cy;
    float up = y * sp + aPosition.z * cp;
    float toward = -y * cp + aPosition.z * sp;
    float depth = max(uCamera.w - toward, 0.001);
    // The same perspective convention used by board-view.project and picking.
    vec2 scale = 2.0 * uCamera.z / uViewport.xy;
    gl_Position = vec4(x * scale.x + uPan.x * depth,
        up * scale.y - uPan.y * depth,
        1.002002 * depth - 2.002002, depth);
    vPosition = aPosition;
    vNormal = aNormal;
    vColor = aColor;
    vMaterial = aMaterial;
    vPixelScale = uCamera.z / depth;
}`;

const FRAGMENT = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform vec3 uEye;
varying vec3 vPosition;
varying vec3 vNormal;
varying vec3 vColor;
varying vec3 vMaterial;
varying float vPixelScale;
const float PI = 3.14159265;

vec3 fresnel(float cosine, vec3 f0) {
    return f0 + (1.0 - f0) * pow(1.0 - cosine, 5.0);
}

// Energy-conscious diffuse + GGX specular makes metal, polymer and solder mask
// respond differently as the camera moves. All coefficients are display-only.
vec3 illuminate(vec3 n, vec3 v, vec3 l, vec3 radiance, vec3 albedo,
        vec3 f0, float rough, float metal, float specularStrength) {
    vec3 h = normalize(v + l);
    float nv = max(dot(n, v), 0.001);
    float nl = max(dot(n, l), 0.0);
    float nh = max(dot(n, h), 0.0);
    float vh = max(dot(v, h), 0.0);
    float a = rough * rough;
    float a2 = a * a;
    float denominator = nh * nh * (a2 - 1.0) + 1.0;
    float distribution = a2 / max(PI * denominator * denominator, 0.0001);
    float k = (rough + 1.0) * (rough + 1.0) / 8.0;
    float geometry = nv / (nv * (1.0 - k) + k)
        * nl / max(nl * (1.0 - k) + k, 0.0001);
    vec3 f = fresnel(vh, f0);
    vec3 specular = distribution * geometry * f / max(4.0 * nv * nl, 0.0001);
    vec3 diffuse = (1.0 - f) * (1.0 - metal) * albedo / PI;
    return (diffuse + specular * specularStrength) * radiance * nl;
}

vec3 studioReflection(vec3 direction, float rough) {
    // Procedural studio softboxes: no environment map, asset or network fetch.
    vec3 environment = mix(vec3(0.025, 0.035, 0.045), vec3(0.34, 0.43, 0.5),
        smoothstep(-0.6, 0.9, direction.z));
    float broad = pow(max(dot(direction, normalize(vec3(-0.5, 0.4, 0.8))), 0.0), mix(38.0, 5.0, rough));
    float strip = pow(max(dot(direction, normalize(vec3(0.85, -0.25, 0.38))), 0.0), mix(105.0, 12.0, rough));
    return environment + vec3(1.7, 1.65, 1.5) * broad + vec3(0.65, 1.0, 1.3) * strip;
}

void main() {
    vec3 normal = normalize(vNormal);
    vec3 eye = normalize(uEye - vPosition);
    float rough = fract(vMaterial.x);
    float metal = floor(mod(vMaterial.x, 4.0) / 2.0);
    float finish = floor(vMaterial.x / 4.0);
    float detail = smoothstep(5.0, 18.0, vPixelScale);
    float grain = sin(vPosition.x * 17.0) * sin(vPosition.y * 19.0);
    vec3 albedo = pow(max(vColor, vec3(0.001)), vec3(2.2));
    if (finish > 0.5 && finish < 1.5) {
        // A faint directional grain reads as brushed sheet metal only up close.
        float brush = sin(vPosition.x * 22.0 + sin(vPosition.y * 0.4));
        rough += brush * detail * 0.035;
        albedo *= 1.0 + brush * detail * 0.025;
    } else if (finish > 1.5 && finish < 2.5) {
        normal = normalize(normal + vec3(sin(vPosition.x * 15.0), sin(vPosition.y * 17.0), 0.0) * 0.006 * detail);
        rough += grain * detail * 0.018;
    } else if (finish > 3.5) {
        // Neutral exposed laminate strands; these do not encode copper layers.
        float fibre = sin(vPosition.z * 48.0 + sin(vPosition.x * 2.0 + vPosition.y * 2.0));
        albedo *= 0.88 + fibre * 0.09;
    } else {
        rough += grain * detail * 0.012;
    }
    rough = clamp(rough, 0.09, 0.95);
    bool mask = finish > 1.5 && finish < 2.5;
    float dielectricF0 = mask ? 0.018 : finish > 2.5 && finish < 3.5 ? 0.065 : 0.04;
    vec3 f0 = mix(vec3(dielectricF0), albedo, metal);
    // The broad, rough solder-mask coating has a faint varnish reflection. A
    // metal-strength studio reflection would bleach the whole planar substrate.
    float specularStrength = mask ? 0.14 : metal > 0.5 ? 0.68 : 1.0;
    vec3 color = illuminate(normal, eye, normalize(vec3(-0.45, 0.40, 0.82)),
        vec3(2.1, 2.0, 1.85), albedo, f0, rough, metal, specularStrength);
    color += illuminate(normal, eye, normalize(vec3(0.8, -0.25, 0.45)),
        vec3(0.6, 0.9, 1.2), albedo, f0, rough, metal, specularStrength);
    color += illuminate(normal, eye, normalize(vec3(-0.3, -0.2, -0.9)),
        vec3(0.8, 0.95, 1.1), albedo, f0, rough, metal, specularStrength);
    float nv = max(dot(normal, eye), 0.0);
    vec3 reflected = reflect(-eye, normal);
    color += studioReflection(reflected, rough) * fresnel(nv, f0)
        * (mask ? 0.16 : 0.56 - rough * 0.22);
    color += albedo * vec3(0.2, 0.25, 0.29) * (1.0 - metal);
    color += albedo * vMaterial.y * 1.5;
    // Gentle exposure compression keeps specular glints without whitening the
    // solder mask or clipping the brushed shield to a flat white rectangle.
    color = color / (color + vec3(1.0));
    color = pow(max(color, vec3(0.0)), vec3(1.0 / 2.2));
    gl_FragColor = vec4(color, vMaterial.z);
}`;

function compile(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        const message = gl.getShaderInfoLog(shader);
        gl.deleteShader(shader);
        throw new Error(`Board shader: ${message}`);
    }
    return shader;
}

export class WebGLBoardRenderer {
    constructor(canvas) {
        this.gl = canvas.getContext("webgl", { alpha: true, antialias: true,
            premultipliedAlpha: false, depth: true, stencil: false, preserveDrawingBuffer: false });
        if (!this.gl) throw new Error("WebGL is unavailable");
        const gl = this.gl;
        const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX);
        const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT);
        const program = gl.createProgram();
        gl.attachShader(program, vertex);
        gl.attachShader(program, fragment);
        gl.linkProgram(program);
        gl.deleteShader(vertex);
        gl.deleteShader(fragment);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            const message = gl.getProgramInfoLog(program);
            gl.deleteProgram(program);
            throw new Error(`Board program: ${message}`);
        }
        this.program = program;
        this.attributes = ["aPosition", "aNormal", "aColor", "aMaterial"]
            .map((name) => gl.getAttribLocation(program, name));
        this.uniforms = Object.fromEntries(["uCamera", "uViewport", "uPan", "uEye"]
            .map((name) => [name, gl.getUniformLocation(program, name)]));
        this.buffers = {};
        for (const name of ["substrate", "objects", "shadows"]) {
            this.buffers[name] = { buffer: gl.createBuffer(), count: 0 };
        }
        gl.enable(gl.DEPTH_TEST);
        gl.depthFunc(gl.LEQUAL);
        // Two-sided rendering is intentional: the viewer can rotate below the
        // board. Per-face outward normals preserve the lighting on either side.
        gl.disable(gl.CULL_FACE);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.clearColor(0, 0, 0, 0);
    }

    setGeometry(geometry) {
        const gl = this.gl;
        for (const name of Object.keys(this.buffers)) {
            const entry = this.buffers[name];
            gl.bindBuffer(gl.ARRAY_BUFFER, entry.buffer);
            gl.bufferData(gl.ARRAY_BUFFER, geometry[name], gl.STATIC_DRAW);
            entry.count = geometry[name].length / VERTEX_STRIDE;
        }
    }

    drawBuffer(name) {
        const gl = this.gl;
        const entry = this.buffers[name];
        if (!entry.count) return;
        gl.bindBuffer(gl.ARRAY_BUFFER, entry.buffer);
        for (let i = 0; i < this.attributes.length; i += 1) {
            const location = this.attributes[i];
            gl.enableVertexAttribArray(location);
            gl.vertexAttribPointer(location, 3, gl.FLOAT, false, VERTEX_STRIDE * 4, i * 3 * 4);
        }
        gl.drawArrays(gl.TRIANGLES, 0, entry.count);
    }

    render(camera, viewport, { xray = false } = {}) {
        const gl = this.gl;
        if (gl.isContextLost()) return;
        gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
        gl.depthMask(true);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        gl.useProgram(this.program);
        gl.uniform4f(this.uniforms.uCamera, camera.yaw, camera.pitch,
            camera.focal * camera.zoom, camera.distance);
        gl.uniform4f(this.uniforms.uViewport, viewport.width, viewport.height, 0, 0);
        gl.uniform2f(this.uniforms.uPan, (2 * camera.panX) / viewport.width,
            (2 * camera.panY) / viewport.height);
        const cp = Math.cos(camera.pitch);
        gl.uniform3f(this.uniforms.uEye, -Math.sin(camera.yaw) * cp * camera.distance,
            -Math.cos(camera.yaw) * cp * camera.distance, Math.sin(camera.pitch) * camera.distance);
        gl.depthMask(!xray);
        this.drawBuffer("substrate");
        gl.depthMask(false);
        if (!xray) this.drawBuffer("shadows");
        gl.depthMask(true);
        this.drawBuffer("objects");
    }

    dispose() {
        const gl = this.gl;
        for (const entry of Object.values(this.buffers)) gl.deleteBuffer(entry.buffer);
        gl.deleteProgram(this.program);
        this.buffers = {};
    }
}
