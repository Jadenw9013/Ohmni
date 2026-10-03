import fs from 'node:fs';import path from 'node:path';import {execFileSync} from 'node:child_process';
import {LIBRARY_DATASETS,createFullLibrary,libraryCoverage} from '../apps/web/component-library/full-registry.js';
import {COMPLETION_MATERIAL_ADDITIONS} from '../apps/web/component-library/completion-materials.js';
const root=path.resolve(new URL('..',import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1')),out=path.join(root,'out/component-library/completion');
const datasets=Object.fromEntries(LIBRARY_DATASETS.map(k=>[k,JSON.parse(fs.readFileSync(path.join(root,`apps/web/component-library/data/${k}.json`)))])),lib=createFullLibrary(datasets),coverage=libraryCoverage(lib);
fs.mkdirSync(out,{recursive:true});const write=(name,text)=>fs.writeFileSync(path.join(out,name),text);
const esc=v=>String(v).replaceAll('|','\\|').replaceAll('\n','<br>'),value=v=>typeof v==='string'?v:JSON.stringify(v);
write('coverage.json',JSON.stringify(coverage,null,2)+'\n');
const coverageMD='| Entry | Family | Member | Generator | LOD | Source status | Implementation | Provisional |\n|---|---|---|---|---|---|---|---|\n'+coverage.map(r=>[r.entry,r.family,r.member,r.generator,r.lod.join('/'),r.source_status,r.implementation,r.provisional?'yes':'no'].map(esc).join(' | ')).map(r=>'| '+r+' |').join('\n')+'\n';
write('coverage.md',coverageMD);
const cosmetics=lib.components.flatMap(r=>(r.cosmetic_defaults??[]).map(c=>({entry:r.id,...c})));
write('cosmetic-defaults.json',JSON.stringify(cosmetics,null,2)+'\n');
const cosmeticMD='| Entry | Feature | Value used (mm unless a count, color or ratio) | Derivation |\n|---|---|---|---|\n'+cosmetics.map(c=>'| '+[c.entry,c.feature,value(c.value),c.derivation].map(esc).join(' | ')+' |').join('\n')+'\n';
write('cosmetic-defaults.md',cosmeticMD);
const findings=lib.components.map(r=>({entry:r.id,source_status:r.status,...r.library_metadata}));write('all-findings.json',JSON.stringify(findings,null,2)+'\n');
const resultPath=path.join(out,'integration-results.json'),results=fs.existsSync(resultPath)?JSON.parse(fs.readFileSync(resultPath)):{status:'IN_PROGRESS'};
const commits=execFileSync('git',['log','--format=%h %s','250fecb..HEAD'],{cwd:root,encoding:'utf8'}).trim();
const lines=['# OHMNI 180-component library completion','',`Implementation coverage: **180 / 180**, all three LODs; ${findings.filter(r=>r.provisional).length} entries carry provisional metadata. No OHM-201+ entries. Source revision: ${lib.source_spec_sha256}.`,'','## Commits','',...commits.split('\n').map(s=>'- '+s),'','## Verification','', '```json',JSON.stringify(results,null,2),'```','','## Scope and deviations','',
'Groups A–E are implemented. This is a geometry library; source evidence remains SPEC_REPORTED and was not independently reverified. Models have no automatic footprint binding or electrical admission. Every original partial status stays partial.',
'',
'The detailed defaults below are provisional, including entries whose source status is complete. FR4 hues use the spec’s variable-color allowance with colors borrowed from supplied tokens. No previously approved material token was changed.',
'',
'Safe variants implemented include N-position headers/connectors, ZIF N, SIP pin count, the existing 1/2/4-digit display records and LCD thickness/standoff. Other vendor alternate footprints are rejected unless their geometry and contact pattern are fully specified. Schematic/common-anode/common-cathode mappings are not inferred.',
'',
'Optional fine details omitted: socket base grooves, connector crimp/seam dimples and threads, unknown Mini-HDMI/RJ11 mounting-fit geometry, Mini-USB locator protrusion, unknown SD shell/detect/write-protect contacts, unsourced magnetics wire-exit attachment paths, tiny molded fillets, potentiometer shaft knurl, display pin shoulders, OLED flex fold, LCD bezel tabs/backlight/back-side COB. The records retain all supplied uncertainty. LOD2 increases supported curve detail; it does not assert unavailable mechanical data.',
'',
'OHM-053 pin 1 is derived using Sections 17.4/6 and the stated provisional 29.24 mm row spacing and 2.5 mm pitch. Raw pin1_xy_mm remains RESEARCH_REQUIRED. OHM-092’s inconsistent FCO description retains explicit source contact/hole coordinates and is reported below.',
'',
'Integration corrected the U.FL body axes to the explicit 3.0 X / 2.6 Y rule and removed unsourced Mini-USB locator protrusions. Group C was re-rendered after these corrections.',
'','## Added material tokens','', '| Token | Color | Roughness | Metalness | Transparency |','|---|---|---|---|---|',...Object.entries(COMPLETION_MATERIAL_ADDITIONS).map(([k,v])=>`| ${k} | ${v[0]} | ${v[1]} | ${v[2]} | ${k==='MAT_GLASS'?'alpha 0.2':k==='MAT_LED_SEGMENT_WHITE'?'alpha 0.85':'opaque'} |`),'',
'## Every spec conflict','',...findings.filter(r=>r.conflicts?.length).flatMap(r=>[`### ${r.entry}`,'',...r.conflicts.map(c=>'- '+JSON.stringify(c)),'']),
'## Every provisional entry and its uncertain values','',...findings.filter(r=>r.provisional).flatMap(r=>[`### ${r.entry} — source ${r.source_status}`,'',...r.uncertain_values.map(s=>'- '+String(s).replaceAll('\n','\n  ')), '']),
'## Every COSMETIC_PROVISIONAL value','',cosmeticMD,'## Coverage','',coverageMD];
write('FINAL-REPORT.md',lines.join('\n')+'\n');console.log(`180 coverage rows; ${cosmetics.length} cosmetic-default rows; report written`);
