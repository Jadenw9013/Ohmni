import assert from "node:assert/strict";
import test from "node:test";

import { readable, scopeHtml, scopeSvg } from "../scope-view.js";

const rc = (samples = 101) => {
    const time_s = [];
    const rail = [];
    const supply = [];
    for (let index = 0; index < samples; index += 1) {
        const t = index * 1e-05;
        time_s.push(t);
        rail.push(5 * (1 - Math.exp(-t / 1e-04)));
        supply.push(5);
    }
    return {
        analysis: ".tran 10us 1ms",
        time_s,
        sample_count: samples,
        decimated_from: null,
        series: [
            { name: "v(vbus)", unit: "V", values: supply },
            { name: "v(3v3)", unit: "V", values: rail },
        ],
    };
};

const simulation = (values = {}) => ({
    status: "OK",
    analysis: "op",
    model_fidelity: "ideal_components",
    detail: "2 signal(s) over 101 sample(s)",
    limitation: "Simulated from the exported netlist with ideal components.",
    transient: rc(),
    ...values,
});

test("a transient becomes a plot with a trace and a key per signal", () => {
    const svg = scopeSvg(rc());
    assert.match(svg, /<svg[^>]+viewBox="0 0 620 260"/);
    assert.equal((svg.match(/<polyline/g) || []).length, 2);
    assert.match(svg, /data-signal="v\(vbus\)"/);
    assert.match(svg, /data-signal="v\(3v3\)"/);
    assert.match(svg, /class="scope-key"/);
    // The axis is labelled with the range it actually mapped.
    assert.match(svg, /1\.00 ms/);
    assert.match(svg, /aria-label="Simulated v\(vbus\), v\(3v3\) from 0 s to 1\.00 ms"/);
});

test("every coordinate is a finite number", () => {
    // A NaN reaches the DOM as a silently broken path rather than an error.
    const svg = scopeSvg(rc());
    assert.doesNotMatch(svg, /NaN|Infinity|undefined|null/);
    const points = [...svg.matchAll(/points="([^"]+)"/g)].flatMap(([, value]) => value.split(" "));
    assert.ok(points.length > 0);
    for (const point of points) {
        const [x, y] = point.split(",").map(Number);
        assert.ok(Number.isFinite(x) && Number.isFinite(y), point);
        assert.ok(x >= 0 && x <= 620 && y >= 0 && y <= 260, point);
    }
});

test("the curve is drawn in the order the samples arrived", () => {
    const svg = scopeSvg(rc());
    const rail = svg.match(/data-signal="v\(3v3\)" points="([^"]+)"/)[1].split(" ");
    const xs = rail.map((point) => Number(point.split(",")[0]));
    const ys = rail.map((point) => Number(point.split(",")[1]));
    assert.deepEqual(xs, [...xs].sort((a, b) => a - b));
    // Charging up means the trace descends in SVG coordinates.
    assert.ok(ys[0] > ys[ys.length - 1]);
});

test("nothing honest to draw returns null rather than an empty frame", () => {
    // An empty plot frame reads as "this circuit did nothing", which is a
    // claim about the design rather than about the simulation.
    assert.equal(scopeSvg(null), null);
    assert.equal(scopeSvg(undefined), null);
    assert.equal(scopeSvg({}), null);
    assert.equal(scopeSvg({ time_s: [0], series: [] }), null);
    assert.equal(scopeSvg({ time_s: [0, 1], series: [] }), null);
    assert.equal(scopeSvg({ time_s: [0, 0], series: [{ name: "a", unit: "V", values: [1, 2] }] }), null);
});

test("a series whose length does not match the time axis is not plotted", () => {
    const broken = { ...rc(), series: [{ name: "v(a)", unit: "V", values: [1, 2] }] };
    assert.equal(scopeSvg(broken), null);
});

test("a flat trace still gets a readable scale", () => {
    const flat = {
        analysis: ".tran 10us 1ms", sample_count: 3, time_s: [0, 1e-05, 2e-05],
        series: [{ name: "v(gnd)", unit: "V", values: [0, 0, 0] }],
    };
    const svg = scopeSvg(flat);
    assert.match(svg, /<polyline/);
    assert.doesNotMatch(svg, /NaN/);
});

test("amperes are not drawn against a volt scale", () => {
    const mixed = {
        ...rc(3),
        series: [
            { name: "v(a)", unit: "V", values: [0, 1, 2] },
            { name: "i(v1)", unit: "A", values: [0, -0.001, -0.002] },
        ],
        time_s: [0, 1e-05, 2e-05],
    };
    const svg = scopeSvg(mixed);
    assert.equal((svg.match(/<polyline/g) || []).length, 1);
    assert.match(svg, /data-signal="v\(a\)"/);
    assert.match(svg, /1 signal\(s\) in a different unit are not plotted/);
});

test("a long series is thinned but keeps its first and last sample", () => {
    const long = rc(5000);
    const svg = scopeSvg(long);
    const points = svg.match(/data-signal="v\(3v3\)" points="([^"]+)"/)[1].split(" ");
    assert.ok(points.length <= 601, `${points.length} points`);
    const lastValue = long.series[1].values[long.series[1].values.length - 1];
    const lastY = Number(points[points.length - 1].split(",")[1]);
    // The final sample is the settled value, which is the whole point of the plot.
    assert.ok(Math.abs(lastValue - 5) < 0.01);
    assert.ok(lastY < 40);
});

test("signal names are escaped, never injected", () => {
    const hostile = {
        analysis: ".tran", sample_count: 2, time_s: [0, 1],
        series: [{ name: '<script>alert("x")</script>', unit: "V", values: [0, 1] }],
    };
    const svg = scopeSvg(hostile);
    assert.doesNotMatch(svg, /<script>/);
    assert.match(svg, /&lt;script&gt;/);
});

test("the report section explains a missing curve instead of drawing one", () => {
    const unavailable = scopeHtml(simulation({ status: "UNAVAILABLE", transient: null,
        detail: "ngspice was not found" }));
    assert.match(unavailable, /UNAVAILABLE/);
    assert.match(unavailable, /ngspice was not found/);
    assert.match(unavailable, /not a passed one/);
    assert.doesNotMatch(unavailable, /<svg/);

    const absent = scopeHtml(undefined);
    assert.match(absent, /No simulation was attempted/);
    assert.doesNotMatch(absent, /<svg/);
});

test("the limitation travels with the curve", () => {
    const html = scopeHtml(simulation());
    assert.match(html, /<svg/);
    assert.match(html, /ideal components/);
    assert.match(html, /\.tran 10us 1ms/);
    assert.match(html, /101 samples/);
});

test("a thinned result says how many steps it came from", () => {
    const html = scopeHtml(simulation({ transient: { ...rc(), decimated_from: 5000 } }));
    assert.match(html, /Thinned from 5000 simulator steps/);
});

test("engineering notation keeps a millisecond axis readable", () => {
    assert.equal(readable(0, "s"), "0 s");
    assert.equal(readable(1e-3, "s"), "1.00 ms");
    assert.equal(readable(2.5e-5, "s"), "25.0 µs");
    assert.equal(readable(3.3, "V"), "3.30 V");
    assert.equal(readable(-0.0012, "A"), "-1.20 mA");
    assert.equal(readable(Number.NaN, "V"), "");
});
