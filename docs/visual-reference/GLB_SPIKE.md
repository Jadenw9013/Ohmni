# KiCad GLB spike and actual-board integrity audit

Measured on 2026-09-14 for the human-approved `VIS-REF-001` scope, W0/W2 of
`OHMNI_REFERENCE_IMPLEMENTATION_PLAN.md`. This is a tooling and display audit;
it does not add electrical evidence or change an engineering verdict.

## Decision

Use the artifact-derived board, copper, pads, drills, and component identities
with separately attached package visuals. Retain the successful KiCad GLB as a
geometry comparison artifact, not the sole source of interactive truth.

The actual saved PCB has **zero 3D model associations**. Its successful GLB
therefore has no component bodies. Copper, pads, and vias are merged into
unnamed electrical groups without net or pad IDs. An additional, private-copy
probe establishes that KiCad **can preserve a component reference** when a
model is explicitly attached: `R1` survives as a parent node. This supports a
future controlled GLB enrichment pipeline, but does not make the current raw
board GLB complete or give its mesh names electrical authority.

For the present renderer, package visuals should resolve through a versioned
sidecar keyed by the authoritative component reference and footprint binding.
Store the package asset hash, provenance, unit scale, local origin, transform,
and display-only limitations separately. Selection must resolve back through
that mapping. Missing assets require an explicitly illustrative fallback;
they must not become invented component or supplier facts.

## Baseline: the actual saved board

Source directory: `out/sensor-controller-90x55-local`.

The confirmed brief is **Sense & control**: USB-C 5 V input, 3.3 V logic,
ESP32-WROOM-32E, BME280, four indicator outputs, two active-low button inputs,
a programming header, and a 90 by 55 mm two-layer board. The exact brief is in
`confirmed-brief.json`; this spike did not reinterpret or resynthesize it.

| Artifact fact | Measured value |
| --- | ---: |
| Components / emitted footprints | 29 / 29 |
| Electrical nets | 21 |
| Outline | Rectangle, (0, 0) to (90, 55) mm |
| Emitted track segments | 452 |
| Emitted vias | 55, each with 0.4 mm drill |
| Pads | 132: 112 SMD, 18 plated through-hole, 2 non-plated |
| Copper zones | 0 |
| Source `(model ...)` associations | 0 |
| Source general thickness | 1.6 mm |

The two non-plated holes are the USB-C footprint's 0.65 mm locating holes.
There are no separate mounting-hole footprints to decorate into Output A.
The thickness is the compiler's emitted display/board setting, not a verified
manufacturing stackup. Output A must retain this population, placement,
outline, copper, vias, and drill geometry.

The saved `report.json` contains an `identity` check group marked
`PARTIALLY_VERIFIED`, including `PB-ID-005` (hand-soldering preference) with a
`FAIL` outcome. Saved ERC is `pass_with_warnings`; saved DRC is `pass`.
These are observations of existing files, not fresh verifier runs. Their
existing coverage and limitations remain applicable; realistic rendering
does not establish bench operation, thermal, RF, signal-integrity, or firmware
behavior.

The pre-change viewer already uses a custom WebGL renderer with depth testing
(`board-renderer-webgl.js`) and a Canvas 2D fallback. `board-view.js` consumes
the renderer-independent scene and geometry modules; it is not merely an SVG
or a flat screenshot. Its package shapes and heights are illustrative. The
visual work can reuse its artifact projection and interaction contract while
improving materials, package detail, lighting, and camera behavior.

The existing local demo command is:

```powershell
.venv/Scripts/python.exe scripts/demo_server.py --host 127.0.0.1 --port 8765
```

This subtask did not start another server, change application code, run a
browser performance test, or capture the parent task's before/after views.
Relevant existing regression families include `board-model.test.mjs`,
`board-renderer.test.mjs`, `board-motion.test.mjs`, and
`test_synthesis_board_dimensions.py`; the parent owns implementation testing.

## Installed tool and bounded process evidence

The locator `ohmni.adapters.tools.find_kicad_cli()` resolved:

```text
C:\Users\wongj\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe
```

Every native call used `ohmni.adapters.process.run_tool` with an explicit
argument list and timeout. No shell-composed KiCad command, bypass runner,
network service, or new model download was used.

| Probe | Result | Wall time |
| --- | --- | ---: |
| `version` | 10.0.5, exit 0 | 0.239 s |
| `pcb export glb --help` | Exit 0 | 0.249 s |
| `pcb render --help` | Exit 0 | 0.246 s |
| Unmodified-board GLB export | Exit 0 | 3.285 s |
| Private-copy R1 model identity export | Exit 0 | 0.423 s |

The initial restricted-access version and help probes each hit a 10-second
timeout while KiCad attempted to initialize its Documents/KiCad directories.
The same three probes succeeded with normal local access after escalation.
Both exports used that successful access mode with a 60-second timeout. This
was a bounded total of eight native invocations: three failed probes, three
successful probes, and two successful exports. No render process was run.

The installed GLB help confirms support for `--include-tracks` (tracks and
vias), `--include-pads`, `--include-zones`, `--include-inner-copper`,
`--include-silkscreen`, `--include-soldermask`, `--cut-vias-in-body`,
`--no-board-body`, `--component-filter`, `--board-only`, `--no-components`,
`--fuse-shapes`, origins, and model substitution. The render help confirms
PNG rendering with size, side, quality, background, perspective, rotation,
lighting, and stackup-color controls. Help availability does not establish
the correctness of untested combinations.

Raw local records are in `out/visual-reference-spike/`: `baseline.json`,
`probes.json`, `probes-normal.json`, the three `*-normal.txt` probe outputs,
`glb-export.json`, `glb-analysis.json`, `model-audit.json`,
`association-identity-input.json`, `association-identity-export.json`,
`association-identity-analysis.json`, and `source-integrity-after.json`.
These are local diagnostic outputs, not published visual assets.

## Unmodified-board GLB result

The export input `actual-board-unmodified.kicad_pcb` was a byte-for-byte copy
of `golden.kicad_pcb`. The guarded runner received this argument list after
the located executable:

```text
pcb export glb
--include-tracks --include-pads --include-soldermask --include-silkscreen
--cut-vias-in-body
--output out/visual-reference-spike/actual-board.glb
out/visual-reference-spike/actual-board-unmodified.kicad_pcb
```

Absolute paths were supplied at execution. The result is a valid GLB 2.0
container, with one embedded binary buffer and no external images or used
extensions. Its generator is Open CASCADE Technology 7.9, with KiCad 10.0.5
in `asset.extras`. The native log reports 1.090 seconds of export time;
3.285 seconds is the measured complete subprocess wall time.

| Result | Measured value |
| --- | ---: |
| GLB file size | 3,681,232 bytes (3.51 MiB) |
| Binary buffer | 2,273,008 bytes |
| Nodes / meshes / materials | 7 / 6 / 5 |
| Triangle primitives | 3,308 |
| Triangles, including node instances | 71,654 |
| Component bodies | 0 |

All primitives use triangle mode. Counts were computed directly from the
GLB JSON accessors and mesh/node references, not estimated visually. The
3,308 primitives are a batching concern for direct Three.js loading; they
are not a measured draw-call count or a browser frame-rate result.

| Mesh group | Triangles | Primitives | Bounds in mm, X/Y/Z |
| --- | ---: | ---: | --- |
| Copper | 31,732 | 1,747 | (6.627402, -0.035, 9.377402) to (87.312138, 1.545, 48.372598) |
| Pads | 18,642 | 1,246 | (5.750001, -0.04, 10.04) to (88.58, 1.55, 51.85) |
| Vias | 10,560 | 220 | (10.55, -0.035, 10.30) to (74.95, 1.545, 45.20) |
| Top soldermask | 2,662 | 1 | (0, 1.56, 0) to (90, 1.56, 55) |
| Bottom soldermask | 514 | 1 | (0, -0.05, 0) to (90, -0.05, 55) |
| PCB laminate | 7,544 | 93 | (0, 0, 0) to (90, 1.51, 55) |

The GLB uses meters. The measured board plane is X/Z, with Y vertical:
source board X maps to GLB X, and source board Y maps to GLB Z. The source
outline's 90 by 55 mm extent is preserved. The laminate alone is 1.51 mm;
the copper/pad/mask surfaces span different elevations, so treating the
laminate thickness as the source's complete nominal thickness is incorrect.
These bounds are parsed mesh accessor bounds, not a proof that every copper
edge or drill tessellation equals its source geometry.

No silkscreen mesh was emitted despite requesting the flag. This source has
hidden reference/value text on F.Fab rather than visible silkscreen labels.
Visible educational reference overlays must remain distinct from claims
about emitted silkscreen artwork.

The root has six mesh children whose node names are OpenCASCADE labels such
as `=>[0:1:1:2]`. Mesh names identify broad groups such as
`actual-board-unmodified_copper`; they do not carry component references,
footprint UUIDs, pad numbers, or net names. Board-triangle picking cannot
directly identify an electrical net from this output. An authoritative
geometry/identity sidecar or the existing artifact-derived layer is required.

## Model availability and identity probe

All nine library footprint files referenced by `OhmniFootprintSource` exist
locally. Eight associated STEP files exist in the normal KiCad model library,
covering 28 of 29 components **if** explicitly attached through a reviewed
mapping. None are attached in the actual source PCB today.

| Actual footprint binding | References | Normal library STEP |
| --- | --- | --- |
| `Button_Switch_THT:SW_PUSH_6mm` | SW1, SW2 | Available |
| `Capacitor_SMD:C_0805_2012Metric` | C1-C7 | Available |
| `Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical` | J2 | Available |
| `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12` | J1 | **Missing** |
| `LED_SMD:LED_0805_2012Metric` | D1-D4 | Available |
| `Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering` | U3 | Available |
| `Package_TO_SOT_SMD:SOT-23-5` | U2 | Available |
| `RF_Module:ESP32-WROOM-32` | U1 | Available |
| `Resistor_SMD:R_0805_2012Metric` | R1-R5, R10-R13, R20-R21 | Available |

The library links use `${KICAD10_3DMODEL_DIR}/<family>.3dshapes/<name>.step`.
The installed root is
`C:/Users/wongj/AppData/Local/Programs/KiCad/10.0/share/kicad/3dmodels`.

A same-named USB-C `.STEP` exists under the bundled
`demos/royalblue54L_feather/lib/3dmodels/Connector_USB.3dshapes` directory.
It is an unvetted candidate, not a resolved association: its identity,
transform, and redistribution provenance were not approved by this spike.
The installed `ESP32-WROOM-32E.step` is also not automatically interchangeable
with the actual `RF_Module:ESP32-WROOM-32` footprint binding, despite the
catalog part ID being ESP32-WROOM-32E. Match geometry and explicit variants;
do not resolve this discrepancy by name similarity.

The second export used `association-identity-probe.kicad_pcb`, a private
copy with exactly one added `R1` model association, zero offset, unit scale,
and zero rotation. Removing the exact inserted model bytes reproduces the
original PCB bytes. No actual source, pad, net, placement, copper, or drill
was changed. The export arguments used `--no-board-body --component-filter
R1` and the private output path.

It returned a 21,388-byte GLB in 0.423 seconds (native export 0.099 seconds),
with three nodes, one mesh, three materials, 26 primitives, and 244 triangles.
The component parent is named **`R1`**, with translation
`[0.040, 0.001595, 0.043]` meters. Its X/Z position matches the actual R1
placement at `(40, 43)` mm. Its child has an OpenCASCADE name and the mesh
is named `R_0805_2012Metric`. The parent name supports component selection
through a validated sidecar, but is not evidence of a footprint UUID, net,
pin, or verified part identity.

Only this one unrotated, top-side component was tested. Repeated instances,
bottom-side placement, nonzero rotations/model offsets, variants, and
multi-model components remain untested. Do not describe this probe as a
complete production exporter or stable general-purpose identity contract.

No KiCad models were downloaded, vendored into the app, or redistributed in
this subtask. Installed file availability alone is not license/provenance
clearance for publishing those files.

## Reproducibility and integrity hashes

SHA-256 below means **file bytes**. It must not be substituted for an
application's typed/canonical fingerprint or routing-plan content hash.
All ten source hashes were recomputed after both exports and matched the
pre-spike baseline.

| Source file | SHA-256 |
| --- | --- |
| `circuit.json` | `137155eff5c52e397e313e46517fa12761760edd4c154617645c486f4c254a4b` |
| `confirmed-brief.json` | `9b1a0b31dcfbeb2a02973076048d16f28abeb623c1f6bb2a2f0275181a05d6b4` |
| `golden.kicad_sch` | `ea77fa2f9eabea3ef53fd0b80ced8d4a1d64a3529adc7334b865257e573e18e2` |
| `golden.placed.kicad_pcb` | `fd0bc1b4e63985381bbc07c0793f93c53e3fbc9aa6243557d5c710c28ffa05c8` |
| `golden.kicad_pcb` | `8ec92f595a26b5769e16186e32231332955db4411247973489abe6c9c9def4f8` |
| `routing-plan.json` | `196be2294d6da59678fbe9d3c67538e003b261e461d531dbdb4b2284e91b3273` |
| `routing-verification.json` | `ce7cc5edd3da122514b2a97b62c8075019e790b0826733caf98b7a3f18d2d371` |
| `erc-report.json` | `510b2dd327d8d4aab6f227bcee587b3dba9fc117513c30adab50190b74a71945` |
| `drc-report.json` | `aa64c0d1338a3e669863dfc77de7d7d9b553b52492ff2ab92f4ddc1f1f4cb4e9` |
| `report.json` | `fd40fd529e6faaa7c187f3eb87e12f1988bff97167b041aaf7b1a3f18e39972b` |

| Probe output | SHA-256 |
| --- | --- |
| `actual-board.glb` | `38d97b0125f96a681c98df7a76ea60dee947276b4ee6b3ae04f9e3d9fd34f434` |
| `association-identity-probe.kicad_pcb` | `5a4ba67bc6c887c2f38e9417e61b666dc2f418f9681b4d7506785940a5a2584c` |
| `association-identity-probe.glb` | `544d2f76277cbe2f33e358990dff6979704c59b5d5b738474ec7de76a7213a9b` |

GLB `asset.extras.generated_at` includes a timestamp. These output hashes
identify this execution; identical bytes on a later native rerun are not
claimed. Geometry/identity normalization would need a separate tested
contract if a reproducible production GLB pipeline is introduced.

Installed model hashes, captured before export:

| Model stem | Bytes | SHA-256 |
| --- | ---: | --- |
| `SW_PUSH_6mm` | 179,934 | `eb2ba2737299cc764145d8d10ea26d992f819ff5522fb3c0dfa2605b8221f9d6` |
| `C_0805_2012Metric` | 43,618 | `9a669c1a2f1ea25b88b401acef6efeaa80a067bd7da9db6993de719a7fbe155c` |
| `PinHeader_1x06_P2.54mm_Vertical` | 215,953 | `d6113af109a14a67c50dcefd1cfc7b43b59b59afa85d808b2319e2452da91318` |
| `LED_0805_2012Metric` | 78,220 | `0aa8b791804f5d72a2fc7d1bf231dd9959207d83df8ad801176fbc459f575b98` |
| `Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering` | 74,162 | `52ce10ea1a6ad1544c3399c9b5fe10717df6e95598d13bdee97aa508af643ef0` |
| `SOT-23-5` | 87,532 | `720a6eab0024069bbee68e7cb4c3ff1149468a34611225cdc852662c5d0ec2b7` |
| `ESP32-WROOM-32` | 1,221,098 | `35a8a3ad9783ddd103ce8d2cb5caf20511a8f729e009f18dd6e7ca447c66a739` |
| `R_0805_2012Metric` | 40,592 | `ded342cdb394fb45395227beaaa75cc390613cf2581b29cd6d22c12abd6103b2` |

The successful export and identity results are sufficient to choose the
hybrid renderer for this scope. Browser load time, frame rate, visual
alignment, package fidelity, raycast behavior, and offline operation still
belong to the implementation's subsequent verification.
