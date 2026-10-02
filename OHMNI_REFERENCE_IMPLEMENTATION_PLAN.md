# Ohmni: Reference-Grade PCB Visualization and Dense Demonstrator Plan

**Implementation brief for a fresh Claude Code session**  
**Scope ID:** `VIS-REF-001` (map into the current task ledger; do not silently reuse or approve M10)  
**Prepared:** 2026-09-14  
**Primary input:** the user's 1500 × 853 reference screenshot.  
**Secondary input:** the user's current Ohmni board screenshot.  
**Deliverable:** a substantially more detailed interactive renderer, a complete reference-inspired component asset library, and a separately identified dense educational board scene. A genuinely more complex electrical demonstrator is a separate, gated design change.

> The target is not “a few extra capacitors.” Reproduce the reference's complete visual vocabulary: different package families, individual leads, connector cavities and contacts, differently sized cans, colored passives, coil windings, solder, pads, printed markings, dense interconnects, board thickness, camera, lighting and shadows.

## Read this before implementation

The reference is a **rendered image, not a schematic, bill of materials or source CAD model**. Its fine text is not reliably readable. Some shapes are generic, ambiguous or partly occluded. Appearance does not establish that the depicted electronics constitute a working circuit. The unseen underside, actual layer count/stackup, hidden pins and occluded body details cannot be catalogued from this top-side view.

This package contains **158 inventory entries**: 145 image-located objects/features/ambiguous patches, plus 13 shared board/rendering features. This is NOT a claim that the image contains exactly 158 components. In particular, the 63 `P` entries include visible passive bodies, band/end details and ambiguous terminations, not 63 independently verified resistors or capacitors. Tiny indistinguishable features are retained in `X01–X08` rather than assigned invented identities.

Three different kinds of information are kept separate throughout:

- **Observed:** color, silhouette, approximate image location, visible repetition.
- **Inferred:** likely package family, with uncertainty retained. An IC-shaped object is not automatically a processor. A silver can is not a known capacitance.
- **Proposed:** our rendering parameters, sample-scene density and implementation choices. These are not recovered manufacturer specifications.

Do not invent part numbers, capacitance, resistance, pin counts, protocols, manufacturer logos, net membership or hidden backside content from this screenshot. An exact component-by-component electrical identification would require a clearer source, BOM or CAD files. The scope here is exhaustive visual coverage at the resolution actually available.

## Package contents

- `OHMNI_REFERENCE_IMPLEMENTATION_PLAN.md`: this complete plan, including the per-entry inventory.
- `REFERENCE_INVENTORY.json`: machine-readable IDs, image points, descriptions, confidence and asset-family requirements.
- `REFERENCE_ATLAS.html`: searchable visual index; open from the extracted package.
- `assets/reference.png`: the user-provided visual reference.
- `assets/current_ohmni.png`: the earlier current-board screenshot for before/after comparison.
- `assets/01_major_components.png`: annotated chips, headers, connectors, posts and mounting holes.
- `assets/02_capacitors_and_coil.png`: annotated cans, coil and orange part.
- `assets/03_small_parts.png`: annotated small passive features and unresolved patches.

Keep the user's supplied reference in private development assets unless its public redistribution rights are established. The user supplying an image is not proof of its original copyright/license.

---

# 1. What every visible family is, in beginner language

These explanations describe component families generally. They do not establish what a particular unmarked device in the reference does.

| Reference family | What is visibly present | Beginner explanation | What must be modeled |
|---|---|---|---|
| IC01 | One large central square black package with perimeter leads | An integrated circuit contains many tiny electronic elements in one package. This one's function is unknown. | Beveled body, individual leads, top markings, orientation dots, underside clearance and solder feet. |
| IC02–IC10 | Nine other prominent rectangular/square multi-lead black packages | Additional packaged electronic circuits. They might perform many different jobs; this image does not identify them. | Several body aspect ratios and lead arrangements, not scaled copies of one blank block. |
| S01–S20 | Twenty candidate smaller black bodies | These could include small ICs, transistors, diodes or oscillator-like packages. Their shapes alone cannot settle the role. | Small-outline leaded packages, few-lead bodies and lead-poor blocks as separate assets. Preserve ambiguous identity. |
| H01–H06 | Six black multiway connector strips with metallic contacts | These let the board connect to other boards or wiring. | Raised black shrouds, real recesses, repeated gold contacts, mounting feet and end walls. Do not guess exact contact counts from pixels. |
| J01–J02 | Two white/light-gray connector-like housings | Insulated housings organize and protect electrical contacts. | Hollow opening, key/latch details, inner contacts, sidewalls, solder/anchor tabs. Exact connector family unresolved. |
| J03 | One silver shell with two circular top apertures and a dark front opening | Likely a shielded connector-like part. Exact protocol and mating interface unknown. | Thin metal shell, openings, seams, inner dark insert, mounting tabs; do not label it USB-C or HDMI without evidence. |
| J04–J05 | Two tall rectangular silver bodies along the rear | Metal-bodied port/shield/heatsink-like objects. The view does not distinguish these possibilities. | Faithful outer silhouette and inset faces. Leave function unknown instead of teaching a guessed function. |
| C01–C15 | Fifteen distinct short silver-can forms | Capacitor-like packages. Capacitors store charge and are often used in supply filtering, but no exact role/value is recoverable here. | Aluminum wall and top, rim, base, body-height variants and restrained markings. |
| E01–E04 | Four tall navy/purple cylinders with silver tops; one cropped | These resemble sleeved electrolytic capacitors. | Sleeve, aluminum top, lip, lower base, possible polarity stripe; marking pattern illustrative unless sourced. |
| L01 | One reddish-brown ribbed cylinder near the rear corner | Looks like a wound inductor or choke, a component whose winding stores energy in a magnetic field. Exact role is unknown. | Actual winding/rib silhouette, core/top, winding color and leads, not a smooth cylinder. |
| O01 | One upright orange coated part | A coated radial part, possibly capacitor-like; subtype unknown. | Rounded orange body, small leads, dark restrained markings. Do not assert “tantalum.” |
| P-series | Blue, blue-banded, tan, red and light terminal details | Banded axial forms often represent resistors. Other small bodies may be capacitors or other two-terminal parts. Color does not prove function. | Separate axial bodies, ceramic/chip bodies, bands, bent leads and metal ends. Some P markers identify a subpart, not another component. |
| T01–T08 | Eight gold post-like silhouettes | Could be terminals, test contacts, adjustment hardware or connector subparts. | Stem, collars, base, metallic highlights; no invented signal labels. |
| M01–M04 | Three clear large gold-rimmed holes and one partial rear-corner hole | Mechanical openings that may support mounting. Electrical grounding/plating is unknown. | Actual through-hole opening and inner wall, surrounding annulus only where modeled in the board. |
| B01–B10 | Green board, edge, traces, small holes, pads, solder, silk and package subdetails | The board physically supports parts and provides connections. | All these layers matter; omitting them is a main reason simple renders look unfinished. |
| V01–V03 | Gray grid, axis widget, view cube | Navigation aids in the rendering application, not electronics. | Optional Ohmni-native presentation aids; do not copy another application's UI as board content. |

**Do not add together package bodies, their leads, their solder fillets and annotation markers to report a BOM count.**

---

# 2. The actual gap between the current Ohmni board and the reference

The current screenshot visibly emphasizes one ESP32 module, two switches, one shielded connector, a small sensor region, a pin header, a few passive clusters and a large amount of empty green board. This is an observation of the screenshot, not a fresh repository audit or exact current BOM count.

The reference's visual complexity comes from five things at once:

1. **More occupied regions:** large, medium and small component clusters cover most of the board's useful area.
2. **Height variation:** low chips and passives, medium silver cans, tall headers and taller navy cylinders create a recognizable silhouette.
3. **Subcomponent detail:** leads, connector contacts, can rims, coil ridges, solder and body markings multiply the visible detail without adding fictional electrical parts.
4. **Material variety:** matte black, green enamel-like mask, bright solder, brushed aluminum, warm gold contacts, blue coatings and beige ceramics respond differently to light.
5. **Interconnect and printed detail:** trace fanouts and white markings visually tie the larger objects into a coherent board.

Changing green to a brighter green will not reproduce those properties. Neither will adding random capacitors to an otherwise empty board.

## 2.1 Three outputs, not one misleading output

### Output A: the existing actual Ohmni board, rendered properly

Preserve the current real circuit, placement, pad and route artifacts. Upgrade every existing component's 3D representation. Real components must not appear/disappear to satisfy a composition score. The richer viewer should also improve the current sparse design.

### Output B: the reference-inspired dense component explorer

Build a **separate, explicitly labeled educational scene** that includes the whole reference vocabulary and comparable density. It can be visually close to this screenshot without claiming that a screenshot has been reverse-engineered into a validated electrical design.

Permanent label: `Reference-inspired educational model · not an electrically verified design`.

No inherited PASS badges, real BOM prices, Gerber downloads, fabrication readiness, connectivity proofs or AI-generation claims. Default product wording must distinguish “Explore sample board” from “Run actual Ohmni design.” Artistic guide lines are not electrical nets. A mesh/model download, if offered, must carry the same illustrative status.

### Output C: a new genuinely complex Ohmni demonstrator

Propose a separate electrical architecture and build it only after its functional scope is approved. A larger real board must have a real purpose, valid parts and verified connections. Its density can approach the reference, but it cannot be manufactured by importing Output B's plausible-looking wires.

The user's current request authorizes planning for all three and the reference-level visual implementation brief. It does not silently authorize purchasing parts, accepting unknown electrical designs, or inventing exact circuitry from this image.

---

# 3. Renderer direction: stop treating 3D as a painted diagram

## 3.1 Preferred implementation

Use a maintained, pinned browser 3D engine, preferably **Three.js directly with the current frontend**, unless the repository already has a suitable GPU renderer. Do not rewrite the app in React merely to use React Three Fiber. Three.js supplies metallic/roughness materials, model loading, camera controls and instanced meshes [R1–R5].

The existing renderer-agnostic board scene can remain the integration boundary. Replace only the rendering backend and add the asset/model layer. A no-build frontend is not, by itself, a reason to retain a software rasterizer for a target that specifically requires better lighting, materials and occlusion. Local versioned ES modules or a small documented bundling step are acceptable; decide from a short spike and measured payload.

Do not create a new bespoke physically based renderer to avoid a dependency. Keep the old 2D view as the low-capability fallback.

## 3.2 KiCad-first model export spike

Current KiCad documentation describes `pcb export glb`, including optional tracks, pads, zones, silkscreen and solder-mask content [R6]. First check the **actually installed** CLI:

```text
kicad-cli version
kicad-cli pcb export glb --help
kicad-cli pcb render --help
```

Use a small, time-bounded spike to answer:

- Does this installed version export GLB successfully?
- Are the required 3D model associations present? Embedded footprints alone do not guarantee model assets exist.
- Are component node identities preserved? If not, can a deterministic sidecar preserve them without brittle name guessing?
- Do pads, holes, copper and component transforms agree with the source PCB?
- What is export time, file size and triangle count?

Choose **artifact-derived board layers + separately attached package models** if monolithic export loses component selection/net identity. The intended renderer must support clicking parts, not merely displaying a merged mesh.

Do not promise GLB export will reconstruct missing component models automatically. Do not make glTF mesh names an electrical authority.

## 3.3 Data pipeline

```text
Actual engineering artifact + exact footprint bindings
    -> authoritative geometric projection + semantic ID mapping
    -> 3D model bindings and rendering metadata
    -> render manifest with source/model hashes
    -> GPU scene
    -> selection, learning, layer inspection, replay
```

For the dense educational sample, replace the first line with `explicit illustrative scene specification`, and retain that status all the way to the UI.

## 3.4 Source and visual truth are separate

Each selectable instance needs:

```ts
type VisualProvenance =
  | 'ARTIFACT_DERIVED'
  | 'PACKAGE_APPROXIMATION'
  | 'ILLUSTRATIVE_ONLY';

type RenderInstance = {
  instanceId: string;
  sourceComponentId: string | null;
  sourceFootprintId: string | null;
  modelAssetId: string;
  visualProvenance: VisualProvenance;
  roleLabel: string;
  roleEvidenceId: string | null;
  transform: { position: [number, number, number]; quaternion: [number, number, number, number] };
  dimensionalSource: string | null;
  selectable: boolean;
};
```

Do not put `verificationStatus: PASS` into model assets. Verification comes from the existing backend. Approximated appearance does not downgrade known netlist facts, but must not claim verified package height or collision accuracy.

---

# 4. Complete asset library specification

Every family below is required for the reference explorer, even if absent from today's ESP32 board. Every family must have a catalog preview tile, close-up screenshot and selection test. “A black cube represents the chip” is not sufficient at this quality bar.

## 4.1 Board slab, mask, copper and holes

- Use real board outline and thickness for Output A. If thickness is absent, show a labeled rendering assumption; do not infer it from screenshot perspective.
- The illustrative scene can use a proposed 140 × 100 × 1.6 mm board as an initial artboard. These are composition choices, not recovered reference dimensions.
- Model top/bottom surfaces separately from edge faces. Preserve openings and cutouts; a hole must remain a hole at grazing view angles.
- Sidewall is muted brown/olive FR-4-like material. Do not give the whole board metallic shading.
- Actual tracks stay at substrate/copper-layer elevation. They are not round green pipes lying on top of the board.
- With solder mask visible, tracks should show restrained green relief/contrast. With mask hidden in inspection mode, show actual copper geometry and label the layer.
- Do not add unmodeled ground pours, decorative vias or fake annular rings to the real board.
- Pads need appropriate rounded/rectangular shape, size, orientation and mask opening from the source artifact.
- Solder fillets are appearance approximations unless an assembly model supplies them. Keep them within plausible lead/pad contact regions and out of fabrication calculations.
- Mirror bottom geometry once, under one tested convention. Never mirror text, pad numbering and package transforms inconsistently.
- Silkscreen comes from the real silk layer. For the sample, author Ohmni labels rather than reproducing unreadable gibberish or invented manufacturer part numbers.

## 4.2 Large square leaded IC

Model IC01 with:

- Dark charcoal resin body with a shallow chamfer; top not perfectly black.
- Subtle top-surface roughness and tiny edge highlights.
- Four rows of individually shaped bent leads where the package model calls for them.
- Proper lead shoulder, descending bend and flat solder foot; never vertical fence teeth.
- Consistent physical lead pitch. Reference lead count is unknown; a sample package's chosen count must be explicit and illustrative.
- Orientation dot/chamfer from the selected asset. Do not teach which reference pin is pin 1 from a blurred mold mark.
- Low-contrast neutral package lettering in the sample, e.g. `OHMNI SAMPLE`, not an invented manufacturer's marking.
- Low underside clearance and convincing contact shadow.

## 4.3 Medium multi-lead ICs

IC02–IC10 need different proportions. Provide at least:

- A four-sided leaded square family.
- A narrow two-sided small-outline family.
- A wider two-sided family.
- A longer low-profile package family.

Choose a shape for an ambiguous reference object as an **illustrative approximation**, not an assertion that it is a particular SOIC/TSSOP/QFP device. Real board assets use the exact package binding.

## 4.4 Small black devices

For S01–S20 provide:

- Small two-sided leaded device, configurable lead count.
- Few-terminal transistor/diode-style body.
- Flat leadless/large-terminal block.
- Narrow long body with end/side terminations where appropriate.

Differentiate resin from terminals. Retain type/function UNKNOWN for reference objects. Never add a “memory chip,” “op-amp” or “crystal” explanation solely from its silhouette.

## 4.5 Black headers and sockets

Six reference connector strips drive much of the dense silhouette. Each needs:

- Solid outside walls and genuinely recessed interior.
- Individual gold-toned contacts, with visible spacing.
- Black plastic floor/body and subtle bevels.
- End walls or key notches only when appropriate to the asset.
- Correct orientation and real pitch for actual designs.
- Visible solder/terminal interface without duplicating the footprint's pads.

Do not call all six “female headers”: the render shows contacts but does not reliably establish mating gender for every connector. The educational sample may select a named generic shrouded-header geometry and label that choice.

## 4.6 White connector bodies

Provide two sizes matching J01/J02's visual roles:

- Off-white plastic shell, not pure-white emissive material.
- Hollow mating opening or terminal cavities.
- Retention/key features.
- Internal dark contacts/shadow and metallic terminals.
- Appropriate wall thickness and rounded molding edges.

Do not identify the large J02 as a particular JST/Molex/RJ-family connector without a known source model.

## 4.7 Shielded metal connector and ambiguous rear metal blocks

For J03, model the visible two top openings, dark front opening, thin folded shell, seams and feet. Preserve “unidentified shielded connector-like body” until a source identity exists.

For J04/J05, reproduce the silver rectangular silhouette and inset panel. Do not add deep heatsink fins or connector pins not visible in the image just to settle the ambiguity. The sample tooltip should state what is unknown.

For the **actual Ohmni USB-C connector**, use its own correct model. Do not replace it with J03's dramatically different reference shell.

## 4.8 Silver capacitor cans

C01–C15 require at least three height/diameter variants while sharing materials:

- Aluminum cylinder, top disc and rolled lip.
- Dark base/insulator.
- Restrained brushed or machined-looking highlight variation.
- Top sleeve/marking sector where visible; do not assume every stripe is a pressure vent.
- Solder/lead mounting appropriate to the selected package.

In the real design, adding a can is an electrical design change. Upgrading an existing can's rendering is not.

## 4.9 Navy/purple sleeved capacitors

E01–E04 require:

- Navy/purple dielectric sleeve material distinct from the exposed metal lid.
- Slight lower ring, shoulder and top rim.
- Printed sleeve detail and optional polarity stripe only when sourced or explicitly generic in the sample.
- Silver top and subtle vent detail appropriate to the chosen asset.
- Multiple body heights; avoid four identical smooth tubes.

## 4.10 Coil-like component

L01 should show a reddish-copper winding/rib structure. Use a helical mesh at close LOD or ring geometry/normal detail at distant LOD. Include the visible core/top and legs where appropriate to the chosen generic asset.

Do not add an inductor to the real LDO circuit simply because the reference has one. Switching-power design is a separate engineering decision.

## 4.11 Orange and red coated parts

O01: upright orange body with rounded shoulder and small supporting leads. Its exact subtype stays unresolved.

P-series red forms: small molded/coated two-terminal bodies, darker red side and subtle highlights. Do not automatically make them glowing LEDs. Color alone does not establish emission, diode function or polarity.

## 4.12 Axial resistor-style parts

For clearly banded forms:

- Blue or beige cylindrical body, metal wire out each end, bends down to the board.
- Circumferential dark/color bands as geometry or a controlled texture.
- Rounded ends and visible solder land connections.
- Real values may be encoded only from actual BOM resistance/tolerance data.
- Generic sample bands must be labeled illustrative; do not teach a decoded resistance from this blurry reference.

Do not build bands as extra standalone capacitors. P59–P63 specifically point at end/band/terminal details of the front row.

## 4.13 Tan ceramic/chip and other unbanded passives

Use a separate material and geometry family for:

- Tan rectangular MLCC-style bodies with two metal terminations.
- Small coated axial/radial tan forms where the reference calls for a rounded body.
- Low-profile two-terminal chip resistor-style parts.

Exact electrical identity can remain unknown in the sample. Do not turn every beige body into the same capacitor package.

## 4.14 Gold posts and adjustment/test-like features

Model stems, collars and dark base rings. Maintain shape variants where the reference differs. These remain visually identified post-like objects. Only actual project metadata may give them a test-point label such as GND or 3V3.

## 4.15 Mounting rings and holes

Three holes are clearly visible; a fourth is partly visible near the rear. For the illustrative reference layout, use four corner positions, with the hidden one treated as inferred composition. Real board mounting holes require proper source geometry and clearance checking before being added.

Do not render actual mounting holes as painted black discs. Do not infer grounded plating from gold color.

## 4.16 Repeated microscopic detail

Every asset family must account for its subparts:

- Metal lead shoulders and feet.
- Contact sockets/pins.
- Ceramic end caps.
- Can rims and bases.
- Solder fillets.
- Pad boundaries.
- Via openings.
- Polarity/orientation marks when known.
- Body printing and silk.

This is where a 19-component board can gain hundreds of useful visible details **without lying about its component count**.

---

# 5. Color, material and lighting specification

## 5.1 Palette

These are **artist-selected starting values** estimated from the screenshot's appearance, not calibrated material measurements or manufacturer colors. Tune them in a fixed lighting environment. A sampled screenshot color already contains lighting and should not be blindly used as a physically measured albedo.

| Material | Suggested sRGB color | Metalness | Roughness starting range | Visual instruction |
|---|---|---:|---:|---|
| Solder mask | `#28633B` | 0 | 0.38–0.55 | Rich medium green, readable in shadows; not black-green. |
| Mask over traces | `#477D4D` | 0 | 0.38–0.55 | Subtle raised/light-green response; actual track mask remains dielectric. |
| Board sidewall | `#5B5332` | 0 | 0.75–0.90 | Olive-brown edge, thin and restrained. |
| IC resin | `#25282A` | 0 | 0.58–0.78 | Charcoal, mild edge reflections; not perfectly flat black. |
| Connector plastic | `#171B1B` | 0 | 0.48–0.68 | Deep recesses but readable outer walls. |
| White connector plastic | `#DFE3DC` | 0 | 0.45–0.65 | Off-white with gentle molding highlights. |
| Aluminum cans | `#BCC4C8` | 1 | 0.25–0.42 | Bright but not mirror chrome. |
| Shield metal | `#AEB8BD` | 1 | 0.22–0.38 | Sheet-metal sheen and edge highlights. |
| Leads and solder | `#B8C0C3` | 1 | 0.25–0.45 | Distinct individual metal feet. |
| Gold-toned contacts | `#BCA25A` | 1 | 0.24–0.38 | Warm gold, not luminous yellow. |
| Navy capacitor sleeve | `#211D55` | 0 | 0.34–0.50 | Blue-purple, with metal top kept separate. |
| Blue passive coating | `#5B9EC1` | 0 | 0.48–0.66 | Reference's small blue accents. |
| Beige ceramic/coating | `#CBA77B` | 0 | 0.56–0.74 | Warm cream/tan. |
| Orange coating | `#D88A19` | 0 | 0.45–0.60 | One strong warm accent. |
| Red coating | `#903B39` | 0 | 0.42–0.62 | Muted red; no emission by default. |
| Winding conductor/coating | `#92502E` | asset-dependent | 0.30–0.52 | Exposed copper may be metallic; insulation is not. |
| Silkscreen | `#E0E8D7` | 0 | 0.75–0.95 | Off-white, legible, no fake glow. |
| Stage background | `#3F464B` | 0 | 1 | Neutral gray, lighter than current navy backdrop. |
| Optional grid | `#65717A` | 0 | 1 | Low contrast; less important than board. |

Use separate metal/dielectric regions rather than one intermediate-metalness material for an entire compound component. Three.js documents the metallic/roughness workflow and environment lighting [R1]. Clearcoat and anisotropy are available when worthwhile, but have added rendering cost [R2].

## 5.2 Lighting and camera

- Three-quarter elevated view, with the whole outline visible. Start near 40–50 degrees elevation and a mild perspective or orthographic camera; these are composition proposals, not recovered camera settings.
- Match reference framing by board occupancy and silhouette, not by copying a random camera vector.
- Board should fill roughly 75–85% of the viewer width while keeping breathing room for labels. Verify at the actual app viewport.
- Soft large key from upper-left/front, weaker fill on opposite side, and restrained environment reflections.
- Directional/contact shadows must anchor cans, ICs and connectors. Add ambient occlusion only if it improves contact detail without dirty halos.
- Large aluminum tops should show shaped highlights, not uniform gray circles.
- Default view: no depth of field, motion blur, lens flare or bloom. They hide small parts. Optional hero export can add gentle focus treatment, labeled as a render.
- Correct color handling and tone mapping: configure color textures as color data, normal/roughness data as non-color. Do not compensate for a color-space bug with arbitrary light intensity [R1].
- The grid and camera cube are UI aids. Provide an Ohmni-native version; do not bake the reference editor chrome into the scene.

## 5.3 Detail, resolution and performance

Proposed acceptance targets, to be measured on a declared test machine:

- Aim for 60 fps during ordinary orbit at 1080p; provide a lower-quality fallback that maintains usable interaction if not reached.
- Initial compressed scene/model transfer target ≤10 MB for the reference explorer; renderer bundle budget reported separately. Do not pretend this budget has been benchmarked yet.
- Target ≤250,000 visible triangles initially, using LOD and instancing; raise only with measurement and justification.
- Clamp device pixel ratio reasonably, e.g. at 2 on the initial implementation. Expose quality settings rather than forcing expensive shadows on all devices.
- Use instancing for repeated leads, passives, contacts and vias where it preserves selection mapping. InstancedMesh is designed to reduce draw calls for repeated geometry/material combinations [R4].
- Render on interaction/state change when idle. Dispose old geometries, materials and model resources when changing projects.
- Serve renderer/model files locally with versioned hashes. Preserve the existing client/server generation binding. Do not depend on a public CDN for the offline demo.
- A GPU-unavailable or context-lost case gets the actual existing 2D board view, not a blank result panel.

---

# 6. Dense reference scene: explicit layout and complexity target

This section is **art direction for Output B**, not a schematic.

## 6.1 Composition

Use normalized board coordinates, never image pixel positions as manufactured millimeters. The reference's four image corners are perspective-distorted. Its inventory coordinates are for locating visible features only.

Suggested regions:

- **Rear edge:** four navy capacitor forms, two silver blocks, the reddish coil and orange upright part.
- **Center:** one dominant square IC, with other medium IC families arranged around it and visible interconnect corridors.
- **Left interior:** three medium ICs, can clusters and a bank of blue passives beside the long header.
- **Right interior:** medium ICs, small black devices, blue/tan passive bank and the distinctive silver connector shell.
- **Front edge:** two long connector strips, silver cans and a repeated resistor-style row.
- **Corners:** three clearly visible gold-ring holes and the inferred fourth corner hole.

Do not turn every region into a perfect grid; match the reference's structured clusters, orientations and connected-looking corridors.

## 6.2 Reference-inspired population

Seed the sample from the inventory, not random scatter:

| Family | Target for the illustrative scene | Interpretation |
|---|---:|---|
| Prominent IC bodies | 10 | One dominant central square, nine smaller multi-lead bodies. |
| Small black bodies | About 20 | Resolve overlapping/unclear silhouettes conservatively. |
| Black connector strips | 6 | Different lengths; generic chosen contact count recorded. |
| White connector housings | 2 | One small rear, one larger front-left. |
| Distinct silver connector-like shell | 1 | Two top apertures as visible; function unknown. |
| Ambiguous rear metal bodies | 2 | Keep visual/function uncertainty. |
| Short silver cans | 15 | Multiple body dimensions. |
| Tall navy cans | 4 | Different heights; crop does not eliminate the fourth asset. |
| Coil-like object | 1 | Visible winding structure. |
| Orange upright body | 1 | Generic unidentified radial/coated part. |
| Gold post-like objects | About 8 | Some may be subassemblies; do not force a testpoint BOM count. |
| Independent small passive bodies | Initial art target 40–55 | Proposed illustrative count, NOT a count recovered from P01–P63. Avoid counting bands/end caps twice. |
| Mounting holes | 4 | Three clear, one partly observed; chosen sample geometry documented. |
| Leads/contact feet/pads/solder details | Hundreds of mesh subfeatures | These do not increase BOM component count. |

This produces roughly 110–125 main visual bodies depending on ambiguity resolution, plus four holes and many subfeatures. It is a **sample-scene density target**, not an electrical parts list or a measured count of the original.

## 6.3 Interconnect appearance

For Output B, artistic trace-like paths can match the reference's fanouts and corridors, but must be kept in an `illustrativeGuideGeometry` layer, not actual `nets`. No fabricated signal names or current direction. The scene tooltip can teach that real PCB traces connect components while explicitly stating that this model's paths are illustrative.

For Output A, only actual board traces/vias/zones are allowed. Never add decorative interconnects to the authenticated board view.

## 6.4 Do not stop after the silhouette

Completion requires the small blue/tan banks, small black devices, contacts, solder and markings. A central chip plus six headers plus a few tall cylinders is not enough. Use the per-entry inventory as a coverage checklist; every ID must be implemented, mapped to a parent subpart, or explicitly marked unresolved with a faithful approximation.

---

# 7. How to make a genuinely richer electrical demo later

The current ESP32 board should not simply receive nine unexplained additional processors. First define a useful higher-complexity board, for example a **USB-powered environmental and general-purpose I/O learning board**.

Candidate functional modules, subject to source verification and supported scope:

| Module | User value | What would justify additional parts |
|---|---|---|
| USB input and 3.3 V supply | Safe, practical power entry | Actual connector requirements, sourced protection/load budget, regulator input/output network. Do not duplicate capacitors already present. |
| ESP32 module and bring-up | Computing and wireless experiments | Required enable/boot network, approved programming interface, useful test access. Exact antenna keepout from module documents remains mandatory. |
| Environmental sensor section | Meaningful demo measurement | Sensor, explicit support circuitry, connector option, placement justified by thermal/airflow goals. |
| I2C expansion | Add supported sensors | One/few connectors, address planning, pull-up ownership, current budget and logic-domain validation. |
| GPIO expansion and indicators | Explore switches and LEDs | A real expander/driver if needed, resistors, LEDs, accessible headers. Do not add an expander when unused. |
| Low-speed analog inputs | Teach reading sensors | Only if a supported ADC/protection/reference design and requirements justify the extra ICs/passives. |
| SPI storage/peripheral | Log measurements or attach an accessory | Only if catalog, firmware responsibility and SPI constraints are explicitly in scope. |
| Mechanical and assembly aids | Make the board usable | Actual mounting constraints, silk, test points and assembly features, not decorative holes. |

Do not promise microSD logging, phone telemetry, working Wi-Fi or application behavior without firmware and system validation. Do not add inductors, switching stages or large electrolytics merely to match the sample's colors. Their electrical and thermal implications require actual design work.

A real dense demo is eligible to replace the main **generated-design** fixture only after:

1. Functional requirements and interface/resource budgets are approved.
2. Exact catalog parts, package variants, footprints and models are sourced.
3. Every populated component has a purpose and design requirement/evidence link.
4. Current/power/logic/address/boot/antenna constraints are reviewed within supported capability.
5. Synthesis, placement, route compilation and verification support the new design without exception waivers.
6. ERC/DRC and Ohmni rules run on the new artifacts; historical golden results are never copied over.
7. Model-to-footprint/board mapping is tested, all export hashes bind to the correct design.
8. Hardware/firmware/bench limitations remain explicit. Cosmetic equivalence is not electrical equivalence.

Do not invent new universal “PCB correctness” checks just to claim this phase complete. State unsupported analysis and require targeted review where necessary.

---

# 8. Interaction and education requirements

The dense board must remain understandable, not merely become busier.

## 8.1 Object selection

- Every component instance has a stable selectable ID, independent of mesh object names.
- A click on a lead/contact/solder submesh selects its owning component, unless pad-inspection mode is explicitly active.
- Enlarge hit areas in screen space without visually enlarging real parts. Resolve overlapping hit regions using visible depth and a small candidate picker.
- Provide a component list/search and keyboard navigation. Users should not hunt for 1 mm objects.
- Show human name first, then technical ID. Unknown reference objects should say `Unidentified small package`, not an invented purpose.

## 8.2 Inspector card

Fields:

- What you are looking at.
- What that component family generally does.
- What is known about this actual part.
- Appearance/model provenance.
- Engineering evidence, when it exists.
- Circuit role, only when supported by actual project data.
- View close-up / isolate / locate in schematic.

In the reference sample: `General educational explanation; this image does not establish the part's electrical function.`

## 8.3 Explode and layers

- Explode components by actual assembly transforms in Output A; return exactly to original transforms.
- Functional grouping in Output A must expose heuristic grouping as heuristic, not datasheet truth. Generic sample grouping should be by visual family/region.
- Front/back flip preserves labels/picking and layer identity.
- Mask/copper/components/silk toggles use actual layers where available.
- Transparent/X-ray presentation is a visualization mode, not a claim about physical board translucency.

## 8.4 Animated tours

- Orbit/turntable, assembly explode, component focus and failure replay are allowed.
- Animation geometry is generated from real transforms/events or clearly illustrative scene data.
- Do not use AI video generation to fill in missing pins/traces on the authoritative board.
- Future AI may select tour steps and phrase explanations from typed facts. Every requested highlight must resolve to an existing instance/net ID.
- Pulsing along a net is labeled a conceptual connectivity explanation, not electrons, measured current, firmware execution or SPICE simulation.
- Do not animate a visual wire replacement as though it were a completed PCB reroute unless the corresponding board artifacts exist. A schematic repair replay can be labeled as such.
- Honor reduced motion and offer pause/stop for automatic motion [R8]. Default camera remains still until the user interacts.

---

# 9. Implementation work packages and gates

Use the actual repository's workflow. Do not overwrite an active review candidate. Do not assume old commit hashes, filenames or test counts remain current.

## W0: baseline and scope mapping

Read `AGENTS.md`, the current task/review/checkpoint state, `docs/product/`, current renderer/projection/server contract and actual PCB artifacts. Inspect dirty changes and running servers without terminating unrelated processes. Map this visual scope to a dedicated approved task set; do not silently approve the deferred LLM/cloud/electrical roadmap.

Deliver a short baseline note: actual current renderer, board/model data available, output assets, start command, actual artifact hashes and existing screenshot tests.

**Gate:** existing real demo still runs; no engineering data changes.

## W1: reference coverage and asset registry

Import the inventory and image privately into the repo. Classify each entry as component, subpart, unknown patch, board feature or viewport-only. Keep the paired end/band details from becoming extra BOM lines. Create `VISUAL_COVERAGE.md` mapping every ID to asset/parent/unknown disposition.

Create an asset registry with source/license, asset hash, package binding or generic status, dimensions/units, transforms, material slots, LODs and selection ownership.

**Gate:** all 158 entries have a disposition; no invented MPNs/functions/pin counts; all required asset families have preview tiles.

## W2: renderer/GLB spike and first quality proof

Time-box the technology spike; do not spend days defending a software renderer. Prove a green slab with real holes, one leaded IC, one connector, one aluminum can and one blue axial resistor under the intended lighting in-browser.

Run the KiCad GLB spike described in section 3. Choose export/import, procedural authoritative geometry or a hybrid based on selection fidelity and asset completeness. Document the choice, measured bundle/model cost and fallback.

**Gate:** at least one macro screenshot visibly contains individual leads, metal/plastic separation, cavity depth and contact shadows. User can orbit and select parts. No application rewrite just for the viewer.

## W3: full component material/model library

Implement every family in section 4. Build a grid of close-up specimens using neutral lighting. Reuse internals without making every component visibly identical. Instanced repeated contacts/leads must keep correct parent selection.

**Gate:** black devices do not look like plain blocks; capacitors do not look like smooth extruded circles; headers do not look like solid bars; ambiguous reference objects stay ambiguous in labels.

## W4: upgrade the actual Ohmni board

Attach rich models to exact existing components/footprints. Preserve positions, geometry, nets and counts. Add proper mask/metal/silk/layer rendering and an authoritative sidecar mapping. Validate orientations and offsets against the existing board projection and KiCad view.

**Gate:** source circuit/PCB hashes unchanged; 100% of actual populated components represented or explicitly missing-model labeled; no extra electrical body; no missing/bogus traces; actual demo remains operable.

## W5: dense reference-inspired explorer

Create the separate scene with the counts/composition of section 6. Include all small-feature families, not merely major chips. Add every individual body via a scene manifest, not anonymous random scatter. Camera and materials match the target closely enough that the before/after gap is unambiguous.

**Gate:** user can open the sample, see the persistent illustrative label, explore all families and use selection. No manufacturing or verified-design endpoint can accept the sample.

## W6: interaction and education

Add list selection, hover, family/region focus, layer toggles, explode and camera reset. Human labels first. For actual designs, preserve technical identifiers behind details. Animation has meaning and can be paused/reduced.

**Gate:** five beginner tasks work: find power entry, find largest IC, identify a capacitor family, identify a connector's contacts, distinguish real project from sample. This is an internal heuristic check until actual users perform it; do not label it a user study.

## W7: quality, truth and performance acceptance

Capture the exact required comparison shots. Run existing fast/backend/frontend gates plus targeted renderer tests. Run the full electrical route flow once if required by current policy, not after every material edit. Run one focused independent review of visual-source integrity and regression behavior, plus an explicit human visual comparison.

**Gate:** no unresolved HIGH/BLOCKER; screenshots satisfy the visual rubric; costs/performance measured. If review exposes a concrete integrity regression, fix and target re-review; do not start unlimited broad historical panels. Do not close on test count alone.

## W8: optional richer actual circuit proposal, not stealth implementation

Deliver a short proposed module/BOM plan for Output C. Estimate engineering work and identify unsupported footprints/rules/firmware obligations. Hold component additions outside Output A until this electrical scope is expressly approved. Keep the current golden baseline available.

---

# 10. Concrete tests and acceptance rubric

## 10.1 Automated correctness tests

- Input circuit/board digest does not change when renderer settings or model assets change.
- Every real component instance and source footprint maps to exactly one visual owner; lead and solder submeshes do not count as new BOM parts.
- Missing/ambiguous models cannot receive fabricated manufacturer dimensions or PASS statuses.
- Reference coordinates are not accepted as PCB millimeters.
- Bottom-side transform round-trips; pad positions and ownership remain correct after flip/explode/reset.
- Real tracks/vias/holes correspond to artifact geometry; never draw “nice looking” extra connections in the real scene.
- Gold-ring holes are actual openings, not dark textures; verify with side/grazing and underside views.
- Selection works through the list and with instanced geometry; tiny parts remain reachable.
- Switching actual/reference scenes cannot carry over verification badges, BOM/costs, export actions or stale selection.
- Reference sample cannot pass through manufacturing/export APIs, even if request fields are tampered with.
- Source board/model manifest changes invalidate cached visual projection. Reference scene has its own isolated hash namespace.
- Asset download/serve hashes and response bytes retain the existing integrity guarantees; do not reopen previously fixed hash/read races.
- Missing model/texture, WebGL loss, offline use, browser resize, reduced motion and mobile/narrow panels are tested.
- Loading failure states show actionable fallback, not a completed/verified board.

## 10.2 Required visual evidence

Produce side-by-side images using the same viewer size:

1. Original current Ohmni board before this scope.
2. Same real board after the new renderer/model library, same camera framing as closely as possible.
3. Dense educational board in reference-matched three-quarter view.
4. Central IC macro showing actual bent lead detail and package edge.
5. Header macro showing hollow cavity and individual gold contacts.
6. Silver/navy capacitor and blue/tan passive macro showing distinct materials and solder attachment.
7. Low grazing board-edge/hole view.
8. Underside/layer view, accurately labeled by data availability.
9. Selected tiny component through the non-spatial list.
10. Reduced-motion state and compact viewport.

Do not generate these acceptance screenshots with an image model. They must be screenshots of the actual browser implementation.

## 10.3 Visual rubric

Score each category 0–2: 0 absent/incorrect; 1 partial; 2 convincing at standard viewing size.

- Dense scene has the reference's family variety, not one chip repeated.
- Large/medium/small body distribution resembles the reference.
- Height silhouette includes headers, silver cans and tall navy cylinders.
- Individual leads/contacts read as metal, not a pale texture stripe.
- Connector openings visibly have depth.
- Board has edge thickness and genuine holes.
- Pads, solder and silkscreen are present and scaled sensibly.
- Blue/tan/orange/red accents are present without neon appearance.
- Lighting gives depth without hiding board detail.
- Traces look like board layers, not thick floating wires.
- Camera framing makes the board prominent and comparable to the source.
- Interaction reveals useful explanations and preserves source status.

Target **20/24 or above, with no zero in source truth, holes, component-family coverage or interaction**. This is a proposed internal art-review threshold, not a scientific similarity metric. A human owner must view the screenshots; the implementation agent cannot award itself “identical.”

## 10.4 Completion report

Report actual files changed, renderer selected, package/model source licenses, source/hash invariance, reference inventory coverage, unknown/deferred items, screenshot paths, measured frame time and loading size, tests actually run, review findings and resolution, scene truth labels, commit boundaries, and exact run/open instructions.

Do not say “almost identical” without side-by-side rendered evidence. Do not say the real PCB gained 100 components when only the sample did.

---

# 11. Research and implementation references

The inventory is derived from the user's image, not these sources. These sources support renderer/tooling choices only. Versions and exact flags must still be checked in the installed environment.

- **R1 — Three.js MeshStandardMaterial:** metallic/roughness shading, environment lighting and texture color-space handling. https://threejs.org/docs/pages/MeshStandardMaterial.html
- **R2 — Three.js MeshPhysicalMaterial:** clearcoat, anisotropy and their performance tradeoff. https://threejs.org/docs/pages/MeshPhysicalMaterial.html
- **R3 — Three.js GLTFLoader:** GLTF 2.0 loading and supported model/material extensions. https://threejs.org/docs/pages/GLTFLoader.html
- **R4 — Three.js InstancedMesh:** repeated geometry/material rendering. https://threejs.org/docs/pages/InstancedMesh.html
- **R5 — Three.js documentation index:** camera, controls, geometry and rendering interfaces. https://threejs.org/docs/
- **R6 — KiCad 10 CLI:** PCB GLB export, optional layers/features and PCB render commands. https://docs.kicad.org/10.0/en/cli/cli.html
- **R7 — KiCad library license:** distinguishes use in generated designs from redistribution of library collections. Preserve attribution and inspect source-specific model licenses. https://www.kicad.org/libraries/license/
- **R8 — W3C reduced-motion technique:** honor reduced-motion preferences for interactive animation. https://www.w3.org/WAI/WCAG22/Techniques/css/C39

Do not claim a legal clearance from this document. In particular, redistributing a vendored model library is a different activity from shipping a board design that uses library data [R7].

---

# Appendix A. Per-entry reference inventory

Coordinates are approximate pixel centers in the original 1500 × 853 image, with origin at top-left. They are **not body dimensions, CAD positions, pin locations or an electrical netlist**. IDs are invented visual annotation IDs, not recovered reference designators. The annotated sheets and HTML atlas make these locations inspectable.

Confidence refers to visual identification, not electrical correctness. Where subtype is unresolved, a generic visual asset must not silently become a known component.


## A1. Prominent integrated-circuit bodies

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| IC01 | (779, 292) | Large central square black package with fine silver leads around its perimeter and circular orientation marks | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |
| IC02 | (529, 229) | Horizontal rectangular multi-lead package below the short rear-left header | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |
| IC03 | (692, 169) | Horizontal multi-lead package immediately in front of the tall blue capacitors | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |
| IC04 | (956, 211) | Rectangular multi-lead package inside the upper-right headers | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |
| IC05 | (607, 315) | Upright rectangular multi-lead package directly left of the large central package | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |
| IC06 | (717, 437) | Horizontal multi-lead package below the central package | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |
| IC07 | (972, 434) | Horizontal multi-lead package above the front-right long header | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |
| IC08 | (365, 286) | Upright multi-lead package in the upper-left interior | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |
| IC09 | (425, 387) | Upright multi-lead package halfway down the left interior | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |
| IC10 | (542, 496) | Upright multi-lead package in the lower-left interior | Integrated-circuit package; exact device, lead count and function unknown. High for body; unknown electrical identity | qfp_or_small_outline |

## A2. Small black package candidates

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| S01 | (296, 213) | Small black package behind the upper-left main IC, left of its neighboring small black package | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S02 | (338, 201) | Small black package beside IC-small 01 near the white rear-left connector | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S03 | (245, 291) | Small horizontal black package between left header and upper-left main IC | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S04 | (323, 420) | Small black horizontal body below the left header, just above the left silver-can trio | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S05 | (252, 442) | Partly obscured small black body behind/left of the silver-can cluster | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S06 | (350, 444) | Small square black body between the left silver cans | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S07 | (440, 676) | Small multi-lead package near the front-left mounting hole, farther from the hole | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S08 | (473, 726) | Small multi-lead package near the front-left mounting hole, nearer the hole | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S09 | (482, 608) | Small multi-lead package immediately right of the large white front-left connector | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S10 | (550, 604) | Larger lead-poor black rectangle above the front-left silver can | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S11 | (711, 543) | Small multi-lead package between the front silver-can pair and long front header | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S12 | (887, 515) | Small multi-lead package above the right end of the long front header | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S13 | (866, 129) | Small low black body below the coil, inward from rear-right header | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S14 | (878, 99) | Small black body between coil-side passives and rear-right header | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S15 | (887, 111) | Adjacent small elongated black body along the rear-right header support cluster | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S16 | (1029, 281) | Horizontal black package below the long right header | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S17 | (967, 302) | Small multi-lead black package inward from the metal connector, upper one | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S18 | (992, 327) | Small multi-lead black package inward from the metal connector, lower one | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S19 | (1240, 432) | Flat rectangular black package between front-right header and right corner | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |
| S20 | (654, 620) | Long narrow marked black package directly behind the left end of the long front header | Small IC / transistor / diode / oscillator-like package; function unresolved. Medium; partly occluded for S05 | small_semiconductor |

## A3. Six perimeter connector strips

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| H01 | (205, 337) | Long black shrouded pin strip along the left edge | Multiway shrouded pin-header/connector form; exact mating type and pin count unknown. High for six connector bodies | shrouded_header |
| H02 | (477, 154) | Short black shrouded pin strip on the rear-left edge | Multiway shrouded pin-header/connector form; exact mating type and pin count unknown. High for six connector bodies | shrouded_header |
| H03 | (967, 107) | Medium black pin strip on the rear-right edge, closer to rear corner | Multiway shrouded pin-header/connector form; exact mating type and pin count unknown. High for six connector bodies | shrouded_header |
| H04 | (1126, 226) | Long black pin strip farther down the right edge | Multiway shrouded pin-header/connector form; exact mating type and pin count unknown. High for six connector bodies | shrouded_header |
| H05 | (803, 620) | Longest foreground pin strip across the lower edge | Multiway shrouded pin-header/connector form; exact mating type and pin count unknown. High for six connector bodies | shrouded_header |
| H06 | (1103, 493) | Separate long pin strip across the lower-right edge | Multiway shrouded pin-header/connector form; exact mating type and pin count unknown. High for six connector bodies | shrouded_header |

## A4. White, shielded and ambiguous metal bodies

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| J01 | (237, 210) | Small white connector body at the rear-left edge | White wire-to-board connector-like housing. Medium | white_connector |
| J02 | (375, 576) | Large white/light-gray rectangular connector at the lower-left edge | Shrouded connector-like housing; protocol and receptacle type unknown. Medium | white_connector |
| J03 | (1109, 395) | Large silver rectangular shell with two dark circular apertures on top and a dark front opening | Metal-shielded connector-like body; not positively USB/HDMI/Ethernet/audio. Medium for shell; low for function | shielded_connector |
| J04 | (580, 96) | Tall silver rectangular body at rear edge, left of matching tall silver body | Metal-bodied port/shield/heatsink-like object; silhouette insufficient to decide. Low for function | ambiguous_metal_block |
| J05 | (660, 71) | Second tall silver rectangular body at rear edge | Metal-bodied port/shield/heatsink-like object; silhouette insufficient to decide. Low for function | ambiguous_metal_block |

## A5. Fifteen silver-can forms

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| C01 | (211, 235) | Upper-left large silver can beside rear-left white connector | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C02 | (282, 249) | Smaller silver can just right of the upper-left large can | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C03 | (371, 167) | Rear silver can of a close pair beside the short rear-left header | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C04 | (393, 200) | Front silver can of that close pair | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C05 | (352, 336) | Silver can beside upper-left main IC and left header | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C06 | (295, 452) | Leftmost can of the mid-left lower trio | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C07 | (383, 469) | Lower/front can of the mid-left trio | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C08 | (435, 446) | Right can of the mid-left trio | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C09 | (602, 573) | Left/front can of the pair beside IC10 | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C10 | (654, 544) | Right/rear can of the pair beside IC10 | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C11 | (758, 508) | Left/front can under IC06 | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C12 | (808, 482) | Right/rear can under IC06 | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C13 | (1152, 322) | Small silver can behind the metal connector | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C14 | (1270, 346) | Larger silver can to the right of the metal connector | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |
| C15 | (555, 705) | Large silver can near the front-left mounting hole | Aluminum-can capacitor form; chemistry, value and rating unknown. High for visible can; medium for capacitor class | aluminum_can |

## A6. Four tall navy/purple cylinders

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| E01 | (583, 151) | Nearest/front tall navy can beside J04 | Sleeved radial electrolytic-style capacitor. High for capacitor-like form; value unknown | radial_electrolytic |
| E02 | (679, 100) | Second tall navy can beside J05 | Sleeved radial electrolytic-style capacitor. High for capacitor-like form; value unknown | radial_electrolytic |
| E03 | (743, 49) | Third tall navy can toward the rear edge | Sleeved radial electrolytic-style capacitor. High for capacitor-like form; value unknown | radial_electrolytic |
| E04 | (801, 25) | Fourth tall navy can, cropped by the top edge | Sleeved radial electrolytic-style capacitor. High for capacitor-like form; value unknown | radial_electrolytic |

## A7. Reddish wound form

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| L01 | (852, 37) | Single reddish-brown ribbed cylinder at the far/rear corner | Wound inductor/choke-like form, not electrically identified. Medium | wound_inductor |

## A8. Orange upright body

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| O01 | (775, 102) | Orange upright cylindrical/rounded body in front of rear blue capacitors | Capacitor-like or other coated radial component; exact type unresolved. Low | coated_radial |

## A9. Gold post-like objects

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| T01 | (718, 107) | Slender gold post between rear capacitor group | Gold post / test terminal / adjustable hardware-like form; role unknown. Medium for form; low for function | gold_post |
| T02 | (723, 132) | Lower gold post in front of the same group | Gold post / test terminal / adjustable hardware-like form; role unknown. Medium for form; low for function | gold_post |
| T03 | (885, 174) | Gold post above the upper-right main IC | Gold post / test terminal / adjustable hardware-like form; role unknown. Medium for form; low for function | gold_post |
| T04 | (397, 335) | Gold post beside upper-left main IC | Gold post / test terminal / adjustable hardware-like form; role unknown. Medium for form; low for function | gold_post |
| T05 | (490, 423) | Gold post beside mid-left main IC | Gold post / test terminal / adjustable hardware-like form; role unknown. Medium for form; low for function | gold_post |
| T06 | (468, 575) | Gold post next to front-left white connector | Gold post / test terminal / adjustable hardware-like form; role unknown. Medium for form; low for function | gold_post |
| T07 | (848, 486) | Gold post between front-center can cluster and small IC | Gold post / test terminal / adjustable hardware-like form; role unknown. Medium for form; low for function | gold_post |
| T08 | (1208, 379) | Gold post next to right metal connector and silver can | Gold post / test terminal / adjustable hardware-like form; role unknown. Medium for form; low for function | gold_post |

## A10. Mounting-hole features

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| M01 | (137, 245) | Rear-left gold-rimmed mounting hole | Large mechanical hole with gold-colored annulus; plating/grounding not established. High for first three; partial for fourth | mounting_hole |
| M02 | (495, 797) | Front-left gold-rimmed mounting hole | Large mechanical hole with gold-colored annulus; plating/grounding not established. High for first three; partial for fourth | mounting_hole |
| M03 | (1358, 390) | Right-corner gold-rimmed mounting hole | Large mechanical hole with gold-colored annulus; plating/grounding not established. High for first three; partial for fourth | mounting_hole |
| M04 | (875, 17) | Partly occluded/cropped rear-corner gold-rimmed hole | Large mechanical hole with gold-colored annulus; plating/grounding not established. High for first three; partial for fourth | mounting_hole |

## A11. Individually indexed small passive features

**Read P-series as feature markers, not a guaranteed component count.** End bands, terminal caps and solder details may belong to the same component as a neighboring marker. P31/P32/P38/P48 are unresolved boundaries; P59–P63 are front-row subdetails. Their colors never establish electrical values.

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| P01 | (432, 197) | blue small passive body near (432, 197) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P02 | (456, 191) | tan small passive body near (456, 191) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P03 | (480, 184) | blue small passive body near (480, 184) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P04 | (503, 177) | tan small passive body near (503, 177) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P05 | (526, 171) | blue small passive body near (526, 171) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P06 | (307, 239) | banded blue small passive body near (307, 239) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P07 | (348, 225) | banded blue small passive body near (348, 225) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P08 | (263, 309) | banded blue small passive body near (263, 309) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P09 | (280, 328) | banded blue small passive body near (280, 328) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P10 | (293, 346) | banded blue small passive body near (293, 346) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P11 | (300, 362) | banded blue small passive body near (300, 362) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P12 | (320, 352) | red small passive body near (320, 352) | Red coated small two-terminal component; diode/capacitor/indicator role unresolved. Low for subtype | coated_red |
| P13 | (572, 269) | tan small passive body near (572, 269) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P14 | (593, 255) | blue small passive body near (593, 255) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P15 | (616, 241) | tan small passive body near (616, 241) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P16 | (659, 226) | tan small passive body near (659, 226) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P17 | (703, 226) | blue small passive body near (703, 226) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P18 | (722, 215) | banded blue small passive body near (722, 215) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P19 | (766, 205) | blue small passive body near (766, 205) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P20 | (856, 68) | blue small passive body near (856, 68) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P21 | (877, 80) | banded blue small passive body near (877, 80) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P22 | (904, 144) | blue small passive body near (904, 144) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P23 | (923, 153) | banded blue small passive body near (923, 153) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P24 | (854, 229) | blue small passive body near (854, 229) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P25 | (878, 246) | banded blue small passive body near (878, 246) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P26 | (896, 264) | tan small passive body near (896, 264) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P27 | (1026, 315) | banded blue small passive body near (1026, 315) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P28 | (1043, 308) | banded blue small passive body near (1043, 308) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P29 | (1058, 301) | banded blue small passive body near (1058, 301) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P30 | (1075, 295) | banded blue small passive body near (1075, 295) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P31 | (1066, 330) | tan small passive body near (1066, 330); body/end-pad separation is ambiguous in this patch | Small passive or its terminal/band; not safe to count independently. Unresolved body boundary | passive_subdetail |
| P32 | (1016, 329) | tan small passive body near (1016, 329); body/end-pad separation is ambiguous in this patch | Small passive or its terminal/band; not safe to count independently. Unresolved body boundary | passive_subdetail |
| P33 | (918, 317) | tan small passive body near (918, 317) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P34 | (931, 328) | blue small passive body near (931, 328) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P35 | (941, 338) | tan small passive body near (941, 338) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P36 | (949, 348) | tan small passive body near (949, 348) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P37 | (1218, 326) | banded blue small passive body near (1218, 326) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P38 | (1233, 318) | banded blue small passive body near (1233, 318); body/end-pad separation is ambiguous in this patch | Small passive or its terminal/band; not safe to count independently. Unresolved body boundary | passive_subdetail |
| P39 | (1262, 305) | red small passive body near (1262, 305) | Red coated small two-terminal component; diode/capacitor/indicator role unresolved. Low for subtype | coated_red |
| P40 | (1293, 415) | banded blue small passive body near (1293, 415) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P41 | (897, 361) | blue small passive body near (897, 361) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P42 | (856, 379) | tan small passive body near (856, 379) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P43 | (768, 374) | tan small passive body near (768, 374) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P44 | (529, 351) | red small passive body near (529, 351) | Red coated small two-terminal component; diode/capacitor/indicator role unresolved. Low for subtype | coated_red |
| P45 | (642, 398) | tan small passive body near (642, 398) | Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved. Medium for form; low for subtype | ceramic_or_axial |
| P46 | (669, 382) | blue small passive body near (669, 382) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P47 | (696, 378) | banded blue small passive body near (696, 378) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P48 | (719, 380) | Tan end/band area adjacent to P47; may belong to the same axial body | Passive-body end/band detail; not counted as a separate component. Unresolved body boundary | passive_subdetail |
| P49 | (417, 522) | blue small passive body near (417, 522) | Blue axial/coated passive, possibly resistor or capacitor; function unknown. Medium for form; low for subtype | coated_axial |
| P50 | (438, 543) | banded blue small passive body near (438, 543) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P51 | (449, 560) | banded blue small passive body near (449, 560) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P52 | (503, 658) | banded tan small passive body near (503, 658) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P53 | (512, 682) | banded tan small passive body near (512, 682) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P54 | (738, 581) | banded blue small passive body near (738, 581) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P55 | (763, 570) | banded blue small passive body near (763, 570) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P56 | (789, 559) | banded blue small passive body near (789, 559) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P57 | (815, 548) | banded blue small passive body near (815, 548) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P58 | (840, 537) | banded blue small passive body near (840, 537) | Banded axial resistor-like passive; exact value unreadable. Medium for resistor family; bands not decodable | axial_resistor |
| P59 | (748, 594) | Tan/light terminal or band detail at the front end of P54; not a separately established component | End/band/solder detail associated with the resistor row, not an extra capacitor. Visible detail; separate component NOT established | passive_subdetail |
| P60 | (775, 583) | Tan/light terminal or band detail at the front end of P55; not a separately established component | End/band/solder detail associated with the resistor row, not an extra capacitor. Visible detail; separate component NOT established | passive_subdetail |
| P61 | (801, 572) | Tan/light terminal or band detail at the front end of P56; not a separately established component | End/band/solder detail associated with the resistor row, not an extra capacitor. Visible detail; separate component NOT established | passive_subdetail |
| P62 | (827, 561) | Tan/light terminal or band detail at the front end of P57; not a separately established component | End/band/solder detail associated with the resistor row, not an extra capacitor. Visible detail; separate component NOT established | passive_subdetail |
| P63 | (852, 550) | Tan/light terminal or band detail at the front end of P58; not a separately established component | End/band/solder detail associated with the resistor row, not an extra capacitor. Visible detail; separate component NOT established | passive_subdetail |

## A12. Tiny/occluded detail regions

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| X01 | (473, 205) | Sub-pixel/occluded parts and shiny terminations in the row beneath the short rear-left header | Unresolved microdetail group; exact object count and types not recoverable. Unresolved | unresolved_microdetail |
| X02 | (334, 218) | Tiny pads, leads and possible chip passives between rear-left silver cans and small black packages | Unresolved microdetail group; exact object count and types not recoverable. Unresolved | unresolved_microdetail |
| X03 | (855, 91) | Tiny green/black/tan objects under coil and behind rear-right support ICs | Unresolved microdetail group; exact object count and types not recoverable. Unresolved | unresolved_microdetail |
| X04 | (711, 222) | Overlapping small passives above central IC fanout | Unresolved microdetail group; exact object count and types not recoverable. Unresolved | unresolved_microdetail |
| X05 | (1050, 317) | Interleaved tiny tan parts and metallic pads in right-hand resistor bank | Unresolved microdetail group; exact object count and types not recoverable. Unresolved | unresolved_microdetail |
| X06 | (784, 568) | Interleaved tiny bodies, solder fillets and printed marks beside foreground resistor bank | Unresolved microdetail group; exact object count and types not recoverable. Unresolved | unresolved_microdetail |
| X07 | (528, 678) | Occluded small passive/lead regions behind the large front silver can | Unresolved microdetail group; exact object count and types not recoverable. Unresolved | unresolved_microdetail |
| X08 | (726, 397) | Small plated holes and terminations between central lower passive trio and main IC | Unresolved microdetail group; exact object count and types not recoverable. Unresolved | unresolved_microdetail |

## A13. Shared board/package subfeatures

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| B01 | Repeated / shared | Green rectangular board slab with visible near-edge thickness | Board substrate and solder-mask surfaces. Visible; many repeated subfeatures cannot be counted from screenshot | board_slab |
| B02 | Repeated / shared | Dark green/brown near-edge band | Board sidewall/substrate cross-section, not a wire. Visible; many repeated subfeatures cannot be counted from screenshot | board_edge |
| B03 | Repeated / shared | Lighter green branching fine lines between component terminals | Trace-like surface network; exact electrical netlist cannot be recovered. Visible; many repeated subfeatures cannot be counted from screenshot | trace_layers |
| B04 | Repeated / shared | Numerous small round holes/dots along traces | Via/test-pad-like features; individual connectivity unknown. Visible; many repeated subfeatures cannot be counted from screenshot | via_and_pad |
| B05 | Repeated / shared | Silver rectangular attachment lands under metal component feet | Solder pads and modeled solder/terminal highlights. Visible; many repeated subfeatures cannot be counted from screenshot | solder_joint |
| B06 | Repeated / shared | White/light-gray component labels, outlines and orientation marks | Silkscreen-style printed layer; text mostly unreadable. Visible; many repeated subfeatures cannot be counted from screenshot | silkscreen |
| B07 | Repeated / shared | Dark circles/chamfers on IC tops | Package orientation/mold marks, not automatically pin-1 proof. Visible; many repeated subfeatures cannot be counted from screenshot | package_marking |
| B08 | Repeated / shared | Numerous silver bent feet along black packages | Individual metallic leads; not separate components. Visible; many repeated subfeatures cannot be counted from screenshot | gullwing_lead |
| B09 | Repeated / shared | Recesses, gold contacts and white solder toes around headers | Connector subparts, not separate BOM components. Visible; many repeated subfeatures cannot be counted from screenshot | connector_subpart |
| B10 | Repeated / shared | Dark halos and grounding shadows under parts | Lighting/contact-shadow cues rather than engineering objects. Visible; many repeated subfeatures cannot be counted from screenshot | contact_shadow |

## A14. Viewport features, not PCB hardware

| ID | Image point | What to locate | Identification / confidence | Asset requirement |
|---|---|---|---|---|
| V01 | Repeated / shared | Gray grid around board | 3D editor viewport ground grid, not PCB copper. Visible; many repeated subfeatures cannot be counted from screenshot | viewport_grid |
| V02 | Repeated / shared | Axis/corner widget at lower left | Editor navigation overlay, not board hardware. Visible; many repeated subfeatures cannot be counted from screenshot | viewport_axis |
| V03 | Repeated / shared | Orientation cube at top right | Editor camera gizmo, not a board component. Visible; many repeated subfeatures cannot be counted from screenshot | viewport_gizmo |


# Appendix B. Fresh Claude Code starter instruction

```text
Read AGENTS.md and current repository state, then read
OHMNI_REFERENCE_IMPLEMENTATION_PLAN.md in full, including the inventory.
Inspect assets/reference.png, assets/current_ohmni.png, the annotated sheets,
and REFERENCE_INVENTORY.json. Do not treat this as a vague styling request.

Implement the bounded reference-grade VISUAL scope through the repository's
approved-workflow mechanism. Do not silently approve unrelated M10+ work.

Deliver both:
1. A much higher-quality view of the actual existing Ohmni board, with its
   electrical component count, geometry, netlist and verification unchanged.
2. A separate, unmistakably illustrative dense reference-inspired component
   explorer, covering the complete inventory and matching the reference's
   visual richness. It must never masquerade as a verified generated PCB.

Use a real 3D material/model pipeline, not a new hand-written software renderer.
Probe installed KiCad GLB export, model completeness and semantic ID retention;
choose a small Three.js integration or an existing equivalent based on evidence.
Do not rewrite the whole app just to install a renderer.

Every visible family, including tiny passives, contacts, leads, can rims,
connector cavities, solder, silk and board holes, needs a tracked disposition.
Do not omit the small pieces, and do not count bands or lead ends as extra parts.

Show real browser screenshots against the reference at the first rendering
proof, then complete the library, integration, interactions and acceptance gates.
Keep reviews bounded and fixes scoped. Preserve all artifact integrity rules.

A genuinely denser electrical board is a separate proposed architecture under
section 7. Do not insert electrically unjustified ICs, capacitors or fake nets
into the current golden circuit. Do not purchase anything.

Begin by auditing the current renderer/data and building the five-object
quality proof. Do not spend the session only creating another plan.
```

The reference's precise unreadable device identities remain unknown. This does not prevent a detailed visual reconstruction; it prevents presenting that reconstruction as a validated reverse-engineered circuit.
