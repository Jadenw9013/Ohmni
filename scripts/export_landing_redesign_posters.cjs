/* Export local scene captures, with output provenance separate from source identity.
 * OHMNI_SHARP_MODULE may select an existing local Sharp installation.
 */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require(process.env.OHMNI_SHARP_MODULE || 'sharp');
const input = path.resolve(process.argv[2] || 'out/landing-pcb-redesign/visual');
const destination = path.resolve('apps/web/landing-pcb-redesign');
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
(async () => {
    const capture = JSON.parse(fs.readFileSync(path.join(input, 'capture.json')));
    const outputs = [];
    for (const [kind, budget] of [['desktop', 250000], ['mobile', 120000]]) {
        const source = path.join(input, `poster-${kind}.png`);
        const output = path.join(destination, `poster-${kind}.webp`);
        await sharp(source).webp({ quality: 90, effort: 6 }).toFile(output);
        const bytes = fs.readFileSync(output);
        if (bytes.length > budget) throw new Error(`${kind} poster exceeds ${budget} bytes`);
        outputs.push({ path: path.relative(process.cwd(), output).replaceAll('\\', '/'),
            captureSha256: digest(fs.readFileSync(source)), sha256: digest(bytes), bytes: bytes.length,
            dimensions: await sharp(bytes).metadata().then(({ width, height }) => ({ width, height })) });
    }
    const { VISUAL_SOURCE_HASH } = await import('../apps/web/visual-version.js');
    fs.writeFileSync(path.join(input, 'poster-provenance.json'), JSON.stringify({
        sourceSha256: capture.sourceSha256, visualSourceHash: VISUAL_SOURCE_HASH,
        view: capture.overview, outputs, kind: 'DETERMINISTIC_SCENE_CAPTURE', generationCreditsSpent: 0,
    }, null, 2));
    console.log(JSON.stringify(outputs, null, 2));
})().catch(error => { console.error(error); process.exit(1); });
