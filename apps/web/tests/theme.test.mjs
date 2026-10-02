import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Palette-level regression guard; browser layout and complete accessibility
// evaluation remain separate checks. Test actual source values, not a copy.
const css = readFileSync(new URL('../styles.css', import.meta.url), 'utf8');
const tokens = Object.fromEntries([...css.matchAll(/--([\w-]+):\s*(#[\da-f]{6});/gi)].map(m => [m[1], m[2]]));
const luminance = hex => {
    const channels = hex.slice(1).match(/../g).map(value => parseInt(value, 16) / 255)
        .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
    return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
};
const contrast = (a, b) => {
    const values = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (values[0] + .05) / (values[1] + .05);
};

test('shared studio reading, links and outcome tokens retain normal-text contrast', () => {
    for (const foreground of ['ink', 'ink-soft', 'ink-faint', 'accent', 'accent-deep']) {
        for (const surface of ['canvas', 'paper', 'panel-2', 'lavender']) {
            assert.ok(contrast(tokens[foreground], tokens[surface]) >= 4.5, `${foreground} on ${surface}`);
        }
    }
    for (const outcome of ['pass', 'warn', 'fail']) {
        assert.ok(contrast(tokens[outcome], tokens[`${outcome}-surface`]) >= 4.5, outcome);
    }
});
