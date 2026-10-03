# OHMNI 180-component library completion

Implementation coverage: **180 / 180**, all three LODs; 134 entries carry provisional metadata. No OHM-201+ entries. Source revision: c140887db02b0d7bfb25a45a4154f6c4ee58d0ddb493ba502eee53b7e3d38639.

## Commits

- a5dd882 Build Group E networks potentiometers and display assemblies
- 1f7a9e3 Build Group D magnetics with provisional source conventions
- eacb3b2 Build Group C I/O connector families from spec records
- 09af85a Build completion Group B crystals oscillators and resonators
- 8ffc8fb Build completion Group A headers and terminal connectors

## Verification

```json
{
  "status": "PASSED",
  "review_status": "AWAITING_HUMAN_LIBRARY_REVIEW",
  "entry_count": 180,
  "lod_model_builds": 540,
  "frontend": {
    "passed": 994,
    "failed": 0,
    "log": "frontend-final.txt"
  },
  "python_full": {
    "passed": 1760,
    "skipped": 89,
    "failed": 0,
    "log": "python-full-native.txt",
    "note": "Completed with native-tool access after a sandboxed run was interrupted due to native-tool failures. Skipped tests are not counted as passed; no independent source-corpus certification is claimed."
  },
  "source_imports": {
    "datasets": 10,
    "entries": 180,
    "status": "PASSED"
  },
  "lint": "python -m ruff check .: PASSED",
  "raw_partial_preserved": 84,
  "provisional_entries": 134,
  "added_material_tokens": 18,
  "cosmetic_provisional_values": 283,
  "visual_review": {
    "status": "PASSED_SELF_REVIEW",
    "independent": false,
    "all_180_inspected": true,
    "browser_errors": 0,
    "record": ".ai/verification/C3D-INTEGRATION-visual.json"
  },
  "production_repair_changes": "untouched in original checkout",
  "deviations": "See scope/deviations and per-entry conflicts below; no unresolved blocker."
}
```

## Scope and deviations

Groups A–E are implemented. This is a geometry library; source evidence remains SPEC_REPORTED and was not independently reverified. Models have no automatic footprint binding or electrical admission. Every original partial status stays partial.

The detailed defaults below are provisional, including entries whose source status is complete. FR4 hues use the spec’s variable-color allowance with colors borrowed from supplied tokens. No previously approved material token was changed.

Safe variants implemented include N-position headers/connectors, ZIF N, SIP pin count, the existing 1/2/4-digit display records and LCD thickness/standoff. Other vendor alternate footprints are rejected unless their geometry and contact pattern are fully specified. Schematic/common-anode/common-cathode mappings are not inferred.

Optional fine details omitted: socket base grooves, connector crimp/seam dimples and threads, unknown Mini-HDMI/RJ11 mounting-fit geometry, Mini-USB locator protrusion, unknown SD shell/detect/write-protect contacts, unsourced magnetics wire-exit attachment paths, tiny molded fillets, potentiometer shaft knurl, display pin shoulders, OLED flex fold, LCD bezel tabs/backlight/back-side COB. The records retain all supplied uncertainty. LOD2 increases supported curve detail; it does not assert unavailable mechanical data.

OHM-053 pin 1 is derived using Sections 17.4/6 and the stated provisional 29.24 mm row spacing and 2.5 mm pitch. Raw pin1_xy_mm remains RESEARCH_REQUIRED. OHM-092’s inconsistent FCO description retains explicit source contact/hole coordinates and is reported below.

Integration corrected the U.FL body axes to the explicit 3.0 X / 2.6 Y rule and removed unsourced Mini-USB locator protrusions. Group C was re-rendered after these corrections.

## Added material tokens

| Token | Color | Roughness | Metalness | Transparency |
|---|---|---|---|---|
| MAT_PLASTIC_NATURAL | #DCCFB0 | 0.5 | 0 | opaque |
| MAT_PLASTIC_GREEN_TERM | #2E8B3E | 0.5 | 0 | opaque |
| MAT_CERAMIC_PKG_TAN | #C9C0A8 | 0.6 | 0 | opaque |
| MAT_RESONATOR_COAT_BLUE | #5F86B4 | 0.5 | 0 | opaque |
| MAT_CERAMIC_CORE_BEIGE | #D9CBA8 | 0.7 | 0 | opaque |
| MAT_MOLDED_COMPOSITE_DARK | #26272A | 0.6 | 0 | opaque |
| MAT_WIRE_ENAMEL_COPPER | #B8733A | 0.35 | 0.6 | opaque |
| MAT_HEATSHRINK_BLACK | #17171A | 0.5 | 0 | opaque |
| MAT_TAPE_POLYESTER_YELLOW | #D9B73A | 0.4 | 0 | opaque |
| MAT_PLASTIC_BLUE | #1E5AA8 | 0.45 | 0 | opaque |
| MAT_BRASS | #C9A24A | 0.35 | 1 | opaque |
| MAT_LED_FACE_GRAY | #6B6B6B | 0.6 | 0 | opaque |
| MAT_LED_SEGMENT_WHITE | #EDEDE8 | 0.4 | 0 | alpha 0.85 |
| MAT_LCD_POLARIZER_GRAY | #7F8C7C | 0.3 | 0 | opaque |
| MAT_OLED_PANEL_BLACK | #08080A | 0.15 | 0 | opaque |
| MAT_FR4_GREEN | #2F4F3A | 0.5 | 0 | opaque |
| MAT_FR4_BLUE | #1E5AA8 | 0.5 | 0 | opaque |
| MAT_GLASS | #CFE0E8 | 0.05 | 0 | alpha 0.2 |

## Every spec conflict

### OHM-012

- {"code":"CEMENT_OUTLINE_TEXT","policy":"Independent width and height columns and entry box procedure win over the conflicting cylindrical summary."}

### OHM-013

- {"code":"WIREWOUND_CAP_EXTENT","A_mm":22.23,"B_max_mm":25.4,"cap_mm":1.59,"policy":"Use explicit procedure: coating A-2*cap, caps within A. Family B=25.40 and prose saying caps beyond A conflict with that procedure; retain both, do not enlarge silently."}

### OHM-015

- {"code":"SHUNT_BLOCK_LENGTH","geometry_choice":"Use element A=15.62 and overall85, deriving each copper block34.69. Prose33.7 uses B=17.65; no gap or overlap introduced. Sense positions remain stated uncertain +/-4.5, not manufacturer-verified."}

### OHM-020

- {"code":"ROTARY_SHAFT_CLEARANCE","geometry_choice":"Stated shaft6 and bushing7 yield equality in diameter <= bushing-1, while coupled prose says strict <; keep explicit defaults unchanged."}

### OHM-028

- {"code":"DISC_COATING_ENVELOPE","policy":"Use 7 x 2.5 as finished coated envelope. Adding the procedural .4 coating on every face would contradict those dimensions; coating has material only."}

### OHM-030

- {"code":"SMD_CAN_TERMINAL_ARITHMETIC","source_span_mm":7.8,"source_gap_mm":1.8,"source_pad_length_mm":2.9,"modeled_span_mm":7.7,"modeled_gap_mm":1.9,"policy":"Preserve contact x=2.4 and 2.9-long pads (outer 3.85, inner .95). B=7.8/P=1.8 imply 3.0-long pads; do not silently stretch terminals."}
- {"code":"SMD_CAN_HEIGHT_STACK","can_height_mm":7.7,"plate_height_mm":1,"policy":"Body-height L remains cylinder height above the provisional 1 mm plate; total seating height is L+1. The plate/H/K callouts are unresolved."}
- {"code":"SMD_CAN_MEMBER_NAME","policy":"Raw member D8 is retained, but the second-pass numeric default is diameter 6.3 mm."}

### OHM-031

- {"code":"SNAPIN_TAIL_OVERRIDE_LOCATION","policy":"Entry YAML supplies terminal_protrusion/length=4.0 rather than the addendum tail key. Apply the explicit requested override, bottom Z=-4.0."}
- {"code":"SNAPIN_SEAT_HEIGHT_STACK","policy":"Follow procedure can D x L above 2 mm seat: rendered top is 42 mm. Nominal body L=40 is retained; seat dimensions are provisional."}

### OHM-032

- {"code":"SMD_CAN_TERMINAL_ARITHMETIC","source_span_mm":7.8,"source_gap_mm":1.8,"source_pad_length_mm":2.9,"modeled_span_mm":7.7,"modeled_gap_mm":1.9,"policy":"Preserve contact x=2.4 and 2.9-long pads (outer 3.85, inner .95). B=7.8/P=1.8 imply 3.0-long pads; do not silently stretch terminals."}
- {"code":"SMD_CAN_HEIGHT_STACK","can_height_mm":7.9,"plate_height_mm":1,"policy":"Body-height L remains cylinder height above the provisional 1 mm plate; total seating height is L+1. The plate/H/K callouts are unresolved."}

### OHM-037

- {"code":"FILM_UNCUT_VS_TRIMMED_LEAD","policy":"Raw terminal length 6 mm is uncut/ambiguous; apply default below-board tail 2.6 mm per mounting convention."}

### OHM-038

- {"code":"FILM_UNCUT_VS_TRIMMED_LEAD","policy":"Raw terminal length 6 mm is uncut/ambiguous; apply default below-board tail 2.6 mm per mounting convention."}

### OHM-039

- {"code":"MICA_STANDOFF_AND_BULGE","policy":"Use explicit YAML .5 standoff. LOD2 face bulge stays inside the 4.3 mm finished thickness rather than adding .4 to it."}

### OHM-040

- {"code":"SUPERCAP_TAIL_LANGUAGE","policy":"Keep global 2.6 mm trimmed tail; raw length_mm=3.0 is not an explicit below-board override and is unsourced."}

### OHM-045

- {"code":"POWER_INDUCTOR_TERMINALS","geometry_choice":"Keep 7.3 x 6.7 x 2.8 body; bottom contact plates 2.5 long centered +/-2.95 span 8.4, beyond body. Procedure 1.0 underfold and second-pass 1.8 terminal callout are unresolved."}

### OHM-046

- {"code":"DRUM_PAD_SPAN","geometry_choice":"Stated provisional centers +/-2.5 and visual 2 mm terminals span 7 mm, beyond 5.8 mm drum diameter. Keep stated centers, report metal overhang."}

### OHM-049

- {"code":"TOROID_INNER_DIAMETER","geometry_choice":"Use stated 12.0 mm ID default (rounded 0.55*21.84=12.012); OD21.84/body thickness11.43, add stated1.57 standoff. Leads +/-4.064 lie inside aperture; render stated straight-down exit default without inventing unsourced attachment routes."}

### OHM-051

- {"code":"CMC_AXES","geometry_choice":"Use YAML body X15.8/Y7.8/H18 and explicit10x4.5 pin rectangle; 10/18 drawing labels remain unresolved."}

### OHM-052

- {"code":"SIGNAL_PIN_STOCK","geometry_choice":"Use stated 0.0375x0.020 inch rectangular stock (0.9525x0.508); alternate .042 square and 1.5 mounting-hole positions remain unresolved; no unknown mounting holes created."}

### OHM-053

- {"code":"FLYBACK_PIN1_DERIVATION","geometry_choice":"Raw pin1_xy_mm remains RESEARCH_REQUIRED. Apply Section 17.4 long-side-terminal / Section 6 dual-row convention to stated candidate row spacing 29.24 and pitch 2.5: pin1=(-14.62,+6.25), CCW, 6 per side. Entire placement remains provisional, not manufacturer-verified."}

### OHM-054

- {"code":"CT_BODY_AND_HOLE","geometry_choice":"Use stated default17.2x9.53x20.4 and 3 rectangular0.66x0.45 pins. Alternate dimensions and PCB YAML1.4 vs prose1.0 hole remain uncertain; hole metadata never drives pin size."}

### OHM-055

- {"code":"LAN_WIDTH_HEIGHT","geometry_choice":"Keep first-pass body X9.53/Y12.7/H6.8 and explicit10.16 contact-row spacing; alternate6.80 width/6.09 height not silently substituted."}

### OHM-061

- {"code":"BODY_HEIGHT_VS_SEATED_HEIGHT","rendered_mm":1.2,"yaml_body_height_mm":1.15,"policy":"Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values."}
- {"code":"FOOT_EXCEEDS_EXTERNAL_LEAD_RUN","external_run_mm":0.5,"foot_mm":0.85,"policy":"Entry procedure permits an under-body foot. Preserve foot/span and model a folded-under lead; conventional outward gull-wing slope is impossible with these defaults."}

### OHM-062

- {"code":"BODY_HEIGHT_VS_SEATED_HEIGHT","rendered_mm":1,"yaml_body_height_mm":0.95,"policy":"Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values."}
- {"code":"FOOT_EXCEEDS_EXTERNAL_LEAD_RUN","external_run_mm":0.5,"foot_mm":0.6,"policy":"Entry procedure permits an under-body foot. Preserve foot/span and model a folded-under lead; conventional outward gull-wing slope is impossible with these defaults."}

### OHM-063

- {"code":"BODY_HEIGHT_VS_SEATED_HEIGHT","rendered_mm":0.62,"yaml_body_height_mm":0.62,"policy":"Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values."}
- {"code":"FOOT_EXCEEDS_EXTERNAL_LEAD_RUN","external_run_mm":0.2,"foot_mm":0.35,"policy":"Entry procedure permits an under-body foot. Preserve foot/span and model a folded-under lead; conventional outward gull-wing slope is impossible with these defaults."}

### OHM-064

- {"code":"BODY_HEIGHT_VS_SEATED_HEIGHT","rendered_mm":2.25,"yaml_body_height_mm":2.15,"policy":"Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values."}

### OHM-065

- {"code":"BODY_HEIGHT_VS_SEATED_HEIGHT","rendered_mm":2.25,"yaml_body_height_mm":2.15,"policy":"Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values."}

### OHM-066

- {"code":"BODY_HEIGHT_VS_SEATED_HEIGHT","rendered_mm":2.44,"yaml_body_height_mm":2.34,"policy":"Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values."}

### OHM-067

- {"code":"BODY_HEIGHT_VS_SEATED_HEIGHT","rendered_mm":1.2,"yaml_body_height_mm":1.15,"policy":"Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values."}
- {"code":"FOOT_EXCEEDS_EXTERNAL_LEAD_RUN","external_run_mm":0.5,"foot_mm":0.85,"policy":"Entry procedure permits an under-body foot. Preserve foot/span and model a folded-under lead; conventional outward gull-wing slope is impossible with these defaults."}

### OHM-068

- {"code":"BODY_HEIGHT_VS_SEATED_HEIGHT","rendered_mm":1.2,"yaml_body_height_mm":1.15,"policy":"Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values."}
- {"code":"FOOT_EXCEEDS_EXTERNAL_LEAD_RUN","external_run_mm":0.5,"foot_mm":0.85,"policy":"Entry procedure permits an under-body foot. Preserve foot/span and model a folded-under lead; conventional outward gull-wing slope is impossible with these defaults."}

### OHM-069

- {"code":"TVS_PIN1_VS_PACKAGE","entry_pin1_x_mm":-2.425,"package_pin1_x_mm":-2.15,"policy":"User requires identical SMB package geometry; use OHM-065 contacts. Preserve raw TVS YAML and narrative unmodified."}
- {"code":"BODY_HEIGHT_VS_SEATED_HEIGHT","rendered_mm":2.25,"yaml_body_height_mm":2.15,"policy":"Follow entry explicit body height plus standoff; family calls A seated height. Preserve both values."}

### OHM-070

- {"code":"CONTACT_REFERENCE_VS_FOOT_CENTER","spec_contact_abs_mm":1,"geometric_foot_center_abs_mm":1.025,"delta_mm":0.025,"policy":"Preserve mandated contact reference and physical lead span/foot length separately. Reference lies on foot; no exact footprint fit claimed."}
- {"code":"INHERITED_SOT23_STANDOFF","entry_standoff_mm":0,"family_standoff_mm":0.05,"policy":"Use owner PKG-SOT23 standoff 0.05 and overall A=1.0, per entry inheritance instruction; preserve raw YAML body_height/standoff."}

### OHM-071

- {"code":"BRIDGE_TAIL_CONVENTION","modeled_bottom_z_mm":-2.6,"stock_length_below_body_mm":4.25,"stock_implied_bottom_z_mm":-3.25,"policy":"Use explicit installed tail Z=-2.6. Source prose calls 4.25-standoff-1.6 the below-board tail, mixing board-top and board-bottom conventions."}

### OHM-073

- {"code":"DOME_RADIUS_ROUNDING","source_radius_mm":1.4,"modeled_radius_mm":1.45,"policy":"Body radius 1.45 and drawing R1.4 differ by .05. Follow explicit hemisphere D/2 procedure; preserve R1.4 in source."}
- {"code":"LED3_FLAT_VS_LEAD","flat_x_mm":-1.2,"lead_outer_x_mm":-1.52,"policy":"Flat x=-1.2 from the provisional .4 depth cuts inside cathode lead extent -1.52. Preserve both; full assembly bounds include the projecting lead. Flat depth needs research."}

### OHM-076

- {"code":"RECT_LED_VENDOR_HEIGHT","policy":"Use second-pass 5 x 2 x 7 and long axis along X; 7.05/7.5 vendor heights and axis association remain unresolved."}

### OHM-077

- {"code":"CHIP_LED_WINDOW_HEIGHT","policy":"Overall H includes the emitter window: recess the central window by its .08 cap height. The literal box-H-plus-dome procedure would exceed stated overall height."}

### OHM-078

- {"code":"CHIP_LED_WINDOW_HEIGHT","policy":"Overall H includes the emitter window: recess the central window by its .08 cap height. The literal box-H-plus-dome procedure would exceed stated overall height."}

### OHM-079

- {"code":"CHIP_LED_WINDOW_HEIGHT","policy":"Overall H includes the emitter window: recess the central window by its .08 cap height. The literal box-H-plus-dome procedure would exceed stated overall height."}

### OHM-080

- {"code":"CHIP_LED_WINDOW_HEIGHT","policy":"Overall H includes the emitter window: recess the central window by its .08 cap height. The literal box-H-plus-dome procedure would exceed stated overall height."}

### OHM-081

- {"code":"PLCC2_CONTACT_CENTER","policy":"Preserve YAML x=-1.2; the coupled 3.5/2-1/2 expression gives -1.25. Modeled feet center on the explicit YAML coordinate."}

### OHM-084

- {"code":"WS2812B_LENGTH","policy":"Keep default 5 x 5 x 1.6; Worldsemi V5 5 x 5.4 x 1.57 is an explicit unresolved alternative."}
- {"code":"WS2812B_PIN1_FUNCTION","policy":"Entry pin1 is VDD at top-left, not an LED cathode. Preserve VDD/DOUT/VSS/DIN and list this exception to the generic LED rule."}

### OHM-085

- {"code":"POWER_LED_SPHERICAL_CAP","rounded_diameter_mm":2.96,"policy":"Use sourced R1.53 and h1.15; derived diameter 2.96358 differs from rounded YAML 2.96, retained as rounding."}

### OHM-086

- {"code":"STAR_HEX_DIAMETER","source_diameter_mm":20,"across_flats_mm":20,"policy":"Use second-pass regular hex 20 mm across flats. Across vertices is 23.094, so cannot also be 20 mm overall diameter."}
- {"code":"STAR_UNRESOLVED_PIN1","policy":"Raw pin1=[0,0] is an unresolved placeholder under the emitter. Visual-only wire-pad centers are explicit provisional data at +/-8,+/-3, pin1 cathode at -X per requested polarity. No footprint binding."}

### OHM-091

- {"code":"LCD_BEZEL_STACK","geometry_choice":"Use explicit70x26 bezel and71x25 stack; coupled strict bezel<70x26 conflicts with explicit default. Header centered X remains stated provisional; no vendor pin offset inferred."}

### OHM-092

- {"code":"OLED_FCO_COORDINATES","geometry_choice":"Keep explicit YAML header Y=-12, hole centersY=+/-11.5 and body_offsetY=+0.25 without moving pins/holes. Center-based bbox of stated coordinates is Y=-0.25; source claims these form centered FCO. Remains provisional; no silent +0.25 correction to contacts."}
- {"code":"OLED_HEADER_ENVELOPE","geometry_choice":"Stated header Y=-12 and depth2.54 reaches -13.27; PCB with stated offset+0.25 reaches -13.25. Keep both dimensions; assembled outline is27.02 alongY, not silently trimmed to27."}

### OHM-093

- {"code":"TO92_LEAD_TYPE_TEXT","policy":"Raw YAML says round_lead; narrative explicitly specifies 0.45 x 0.40 rectangular ribbon. Use narrative cross-section."}

### OHM-094

- {"code":"CONTACT_REFERENCE_VS_FOOT_CENTER","spec_contact_abs_mm":1,"geometric_foot_center_abs_mm":1.025,"delta_mm":0.025,"policy":"Preserve mandated contact reference and physical lead span/foot length separately. Reference lies on foot; no exact footprint fit claimed."}

### OHM-095

- {"code":"CONTACT_REFERENCE_VS_FOOT_CENTER","source_abs_y_mm":1.5,"geometric_abs_y_mm":1.525,"policy":"Preserve source contact reference and specified span/foot separately; reference lies on actual foot."}
- {"code":"FOOT_EXCEEDS_EXTERNAL_LEAD_RUN","external_run_mm":0.8,"foot_mm":1.05,"policy":"Fold under body per flat-pad/tab narrative; no silent shortening of foot."}

### OHM-096

- {"code":"CONTACT_REFERENCE_VS_FOOT_CENTER","source_abs_y_mm":3.05,"geometric_abs_y_mm":3.025,"policy":"Preserve source contact reference and specified span/foot separately; reference lies on actual foot."}

### OHM-098

- {"code":"SHOULDER_LONGER_THAN_TRIMMED_TAIL","shoulder_length_mm":3.56,"available_at_default_standoff_mm":2.6,"policy":"Truncate at requested Z=-2.6 without shortening the shoulder. At default zero standoff no narrower tail remains visible at LOD1/2."}

### OHM-099

- {"code":"SHOULDER_LONGER_THAN_TRIMMED_TAIL","shoulder_length_mm":4.2,"available_at_default_standoff_mm":2.6,"policy":"Truncate at requested Z=-2.6 without shortening the shoulder. At default zero standoff no narrower tail remains visible at LOD1/2."}
- {"code":"TO247_PLASTIC_THICKNESS_ARITHMETIC","narrative_mm":3.03,"coordinate_difference_mm":3.02,"policy":"Explicit y=-2.61..0.41 wins over rounded 3.03 text."}
- {"code":"TO247_DISH_TOP_INTERSECTION","dish_top_mm":18.38,"plastic_top_mm":18.35,"policy":"Preserve numeric defaults; front dish opens through plastic top by 0.03 mm rather than moving/resizing it."}

### OHM-100

- {"code":"SOURCE_COUNT_EXCLUDES_TAB","source_lead_count":2,"modeled_distinct_terminals":3,"policy":"Raw source count means two formed leads (1,3); expose tab as terminal 2 with alias 4 separately, giving three physical terminals."}
- {"code":"TAB_SOLID_VS_EXPOSED_CONTOUR","policy":"Procedure describes full internal plate extent; geometry shows the specified minimum exposed contour under the plastic plus projecting tab. Hidden internal metal is omitted, not exposed across the entire belly. Contour placement remains provisional."}
- {"code":"CONTACT_REFERENCE_VS_FOOT_CENTER","source_abs_y_mm":4.1,"geometric_abs_y_mm":4.16,"policy":"Preserve pin1 reference -4.1 and actual foot center -4.16; no footprint fit claimed."}

### OHM-101

- {"code":"SOURCE_COUNT_EXCLUDES_TAB","source_lead_count":2,"modeled_distinct_terminals":3,"policy":"Raw source count means two formed leads (1,3); expose tab as terminal 2 with alias 4 separately, giving three physical terminals."}
- {"code":"TAB_SOLID_VS_EXPOSED_CONTOUR","policy":"Procedure describes full internal plate extent; geometry shows the specified minimum exposed contour under the plastic plus projecting tab. Hidden internal metal is omitted, not exposed across the entire belly. Contour placement remains provisional."}
- {"code":"D2PAK_SOURCE_OUTLINE_CONFLICT","policy":"Use second-pass plastic 9.0 + tab extension 1.5 = 10.5, versus Nexperia 11 mm title; keep corrected A1=0.1 and embedded tab."}

### OHM-102

- {"code":"POWERPAK_UNMODELED_END_FRAME","source_y_mm":5.15,"modeled_y_mm":4.9,"policy":"Use explicit Vishay molded-body Y=4.90; unexplained D=5.15 end frame remains unmodeled, not silently invented."}
- {"code":"POWERPAK_HEIGHT_LANGUAGE","source_A_mm":1.04,"standoff_mm":0.05,"policy":"A=1.04 is seating-plane-to-top; plastic Z=.05..1.04. Procedure phrase height 1.04 from standoff would incorrectly yield 1.09."}

### OHM-120

- {"code":"CONTACT_REFERENCE_VS_FOOT_CENTER","spec_contact_abs_mm":1.2,"geometric_foot_center_abs_mm":1.3,"delta_mm":0.1,"policy":"Preserve mandated contact reference and physical lead span/foot length separately. Reference lies on foot; no exact footprint fit claimed."}

### OHM-121

- {"code":"CONTACT_REFERENCE_VS_FOOT_CENTER","spec_contact_abs_mm":1.2,"geometric_foot_center_abs_mm":1.3,"delta_mm":0.1,"policy":"Preserve mandated contact reference and physical lead span/foot length separately. Reference lies on foot; no exact footprint fit claimed."}

### OHM-122

- {"code":"HEIGHT_LIMIT_VS_RENDERED_STACK","source_overall_height_mm":1.2,"rendered_height_mm":1.1,"policy":"Entry geometry/family identifies source height as A max; use standoff + body thickness, preserve YAML field unchanged."}

### OHM-123

- {"code":"HEIGHT_LIMIT_VS_RENDERED_STACK","source_overall_height_mm":1.2,"rendered_height_mm":1.1,"policy":"Entry geometry/family identifies source height as A max; use standoff + body thickness, preserve YAML field unchanged."}

### OHM-124

- {"code":"HEIGHT_LIMIT_VS_RENDERED_STACK","source_overall_height_mm":1.2,"rendered_height_mm":1.1,"policy":"Entry geometry/family identifies source height as A max; use standoff + body thickness, preserve YAML field unchanged."}

### OHM-125

- {"code":"HEIGHT_LIMIT_VS_RENDERED_STACK","source_overall_height_mm":1.2,"rendered_height_mm":1.1,"policy":"Entry geometry/family identifies source height as A max; use standoff + body thickness, preserve YAML field unchanged."}

### OHM-126

- {"code":"HEIGHT_LIMIT_VS_RENDERED_STACK","source_overall_height_mm":1.6,"rendered_height_mm":1.5,"policy":"Entry geometry/family identifies source height as A max; use standoff + body thickness, preserve YAML field unchanged."}

### OHM-127

- {"code":"PULLBACK_REQUEST_VS_FLUSH_SPEC","source_pullback_mm":0,"policy":"Keep flush spec default; expose explicit provisional terminal_pullback parameter and 0.05 mm demonstration render."}

### OHM-128

- {"code":"PULLBACK_REQUEST_VS_FLUSH_SPEC","source_pullback_mm":0,"policy":"Keep flush spec default; expose explicit provisional terminal_pullback parameter and 0.05 mm demonstration render."}

### OHM-129

- {"code":"PULLBACK_REQUEST_VS_FLUSH_SPEC","source_pullback_mm":0,"policy":"Keep flush spec default; expose explicit provisional terminal_pullback parameter and 0.05 mm demonstration render."}

### OHM-130

- {"code":"PULLBACK_REQUEST_VS_FLUSH_SPEC","source_pullback_mm":0,"policy":"Keep flush spec default; expose explicit provisional terminal_pullback parameter and 0.05 mm demonstration render."}

### OHM-131

- {"code":"PULLBACK_REQUEST_VS_FLUSH_SPEC","source_pullback_mm":0,"policy":"Keep flush spec default; expose explicit provisional terminal_pullback parameter and 0.05 mm demonstration render."}

### OHM-134

- {"code":"EP_CLEARANCE_BELOW_FAMILY_RULE","actual_mm":0.15,"family_min_mm":0.2,"policy":"Preserve WSON source geometry; TI source shows no K limit. No silent resizing; only this documented exception accepted."}
- {"code":"ROW_CORNER_MARGIN_BELOW_FAMILY_RULE","row_plus_width_mm":1.7,"body_minus_margin_mm":1.6,"policy":"Preserve source values; resulting total margin is 0.30, not family 0.40."}

### OHM-136

- {"code":"HEIGHT_LIMIT_VS_RENDERED_STACK","source_overall_height_mm":1.5,"rendered_height_mm":1.35,"policy":"Entry geometry/family identifies source height as A max; use standoff + body thickness, preserve YAML field unchanged."}

### OHM-137

- {"code":"BALL_MAP_EXTRACTION_CONFLICT","policy":"Full 10x10=100 array follows the family resolution; contradictory extracted 'corner balls removed' is not used."}
- {"code":"STALE_VALIDATION_ARITHMETIC","source_text_mm":7.65,"calculated_mm":7.6,"policy":"Use 9*0.8+0.40=7.60; raw source text retained."}
- {"code":"HEIGHT_LIMIT_VS_RENDERED_STACK","source_overall_height_mm":1.2,"rendered_height_mm":1.05,"policy":"Entry geometry/family identifies source height as A max; use standoff + body thickness, preserve YAML field unchanged."}

### OHM-138

- {"code":"HEIGHT_LIMIT_VS_RENDERED_STACK","source_overall_height_mm":1.55,"rendered_height_mm":1.36,"policy":"Entry geometry/family identifies source height as A max; use standoff + body thickness, preserve YAML field unchanged."}

### OHM-141

- {"code":"SUPPLIED_VS_TRIMMED_LEAD","geometry_choice":"Keep explicit 2.6 mm mounted tail rather than as-supplied 12.7 mm minimum."}

### OHM-142

- {"code":"SUPPLIED_VS_TRIMMED_LEAD","geometry_choice":"Keep explicit 2.6 mm mounted tail rather than as-supplied 12.7 mm minimum."}

### OHM-145

- {"code":"PROSE_HEIGHT_VS_YAML","geometry_choice":"Use YAML overall height 0.45 mm; recompute stated fractional ceramic/lid split instead of older approximate prose heights."}

### OHM-146

- {"code":"PAD_OVERHANG_005","geometry_choice":"Keep explicit contacts Y=+/-1.905 and pad Y size=1.2. Metal spans 5.01 mm vs ceramic body width 5.0; do not shorten pads or move terminals to enforce the contradictory pads-inside-body sentence."}

### OHM-147

- {"code":"PROSE_HEIGHT_VS_YAML","geometry_choice":"Use YAML overall height 0.9 mm; recompute stated fractional ceramic/lid split instead of older approximate prose heights."}

### OHM-152

- {"code":"SOCKET_LENGTH_RULE","geometry_choice":"Use second-pass N*pitch+0.4; older variant prose omits the end allowance."}

### OHM-153

- {"code":"SOCKET_LENGTH_RULE","geometry_choice":"Use second-pass N*pitch+0.4; older variant prose omits the end allowance."}

### OHM-156

- {"code":"XH_WINDOW_SIDE","geometry_choice":"Entry Geometry +X wins over family -X description."}

### OHM-157

- {"code":"SH_MATING_CONVENTION","geometry_choice":"Section 18.12 / entry -X supersedes general side-entry +Y; no mirror."}

### OHM-158

- {"code":"KK_WALL_THICKNESS","geometry_choice":"Use explicit X=-2.88..-1.99 (0.89), rather than the rounded 1.0 wall prose."}
- {"code":"KK_BODY_OFFSET","geometry_choice":"Use explicit outline -2.88..+2.92 (center +0.02); raw body_offset remains [0,0] as entry allows."}
- {"code":"KK_STUB_POSITION","geometry_choice":"Entry +2.32..+2.92 wins over older family +2.43..+3.03."}

### OHM-159

- {"code":"SCREW_ENTRY_DIRECTION","geometry_choice":"Entry explicit +X wins over general Section 18 side-entry +Y."}
- {"code":"SCREW_HEIGHT","geometry_choice":"Use adopted 13.8 above board with 3.5 tail; retain alternative 10.3 from ambiguous overall-height listings."}

### OHM-160

- {"code":"SCREW_ENTRY_DIRECTION","geometry_choice":"Entry explicit +X wins over general Section 18 side-entry +Y."}
- {"code":"SCREW_HEIGHT","geometry_choice":"Use adopted 13.8 above board with 3.5 tail; retain alternative 10.3 from ambiguous overall-height listings."}

### OHM-161

- {"code":"PLUG_INTERLOCK_UNKNOWN","geometry_choice":"Use stated overlapping assembly envelopes with explicit provisional internal features; exact mating interlock/coding remains unknown."}
- {"code":"PLUG_VERTICAL_LOCATION","geometry_choice":"Vertical shroud envelope is sourced but tail/body offset and plug placement are unspecified. Default right-angle supported; vertical assembly parameter rejected until coordinates are supplied."}

### OHM-165

- {"code":"USB_C_DEPTH","geometry_choice":"Use default L=7.35 at offset Y=1.1 (front 4.775); PCB prose fab depth 10.45/front 6.3 disagree. Keep explicit A/B tail and shield coordinates even outside shell."}

### OHM-166

- {"code":"MINI_USB_LOCATOR_DEPTH","geometry_choice":"NPTH positions and diameter are stated, but locating-peg protrusion is not. Retain hole metadata and omit peg solids to avoid inventing a below-board bounding-box dimension."}

### OHM-167

- {"code":"HDMI_HEIGHT_AND_SHIELD","geometry_choice":"Use YAML H=6.5 vs procedure 6.0; explicit shield X=6.775 vs formula 6.825; odd contacts Z=0, even contacts Z=-1.6 per straddle mounting and Section 2 board default."}
- {"code":"HDMI_CAVITY_WIDTH","geometry_choice":"14 mm cavity equals 14 mm shell width; derive cosmetic cavity inside stated shell instead of a zero-wall cavity."}

### OHM-168

- {"code":"MINI_HDMI_MOUNT_COORDINATES","geometry_choice":"Shield pad X=+/-5 is given without Y; omit unlocated shield pads. Keep explicit single-row placeholder 19 signal contacts; no footprint admission."}

### OHM-170

- {"code":"RJ11_UNSPECIFIED_DRILL","geometry_choice":"NPTH centers +/-4,+3.5 are stated, diameter is absent; retain metadata only, omit pegs rather than infer fit."}

### OHM-172

- {"code":"DC_JACK_ENVELOPE","geometry_choice":"Retain second-pass 10.7 width, 14.4 length and 11 height; 9.0-wide KiCad outline and 6.5 callout remain unresolved. Bore axis 5.5 is stated placeholder."}

### OHM-173

- {"code":"XT30_LENGTH_ARITHMETIC","geometry_choice":"Use 13.95 length at stated +1.3 offset, giving -5.675..8.275. Prose front 9.275 implies 14.95 and is not used. Explicit peg centers lie outside 9.9 body; retain detached locator geometry and report missing attachment outline."}

### OHM-177

- {"code":"SMA_EDGE_WIDTH","geometry_choice":"Hex across flats 7.87 implies wider than YAML 6.35 barrel diameter; model barrel diameter 6.35 and explicit 7.87 hex, report combined envelope. Axis Z=-0.785 remains stated provisional slot-center assumption."}

### OHM-179

- {"code":"SD_INCOMPLETE_FCO","geometry_choice":"Use stated provisional body offset and exemplar signal row. Unknown shell tabs, locator posts and detect/write-protect contacts omitted; FCO remains signal-row-only provisional."}

## Every provisional entry and its uncertain values

### OHM-010 — source complete

- lead_pitch: 10.16 mm (DERIVED/L)
- Formed pitch and tail trim are mounting choices; bend radius, shoulders, example band colors and coating appearance are visual defaults. No resistance/inductance value is asserted.

### OHM-011 — source complete

- lead_pitch: 10.16 mm (DERIVED/L)
- Formed pitch and tail trim are mounting choices; bend radius, shoulders, example band colors and coating appearance are visual defaults. No resistance/inductance value is asserted.

### OHM-012 — source complete

- lead_pitch: 25.4 mm (DERIVED/L)
- Formed pitch and tail trim are mounting choices; bend radius, shoulders, example band colors and coating appearance are visual defaults. No resistance/inductance value is asserted.
- Cement lead length/pitch, edge radius and printed marking field remain provisional.

### OHM-013 — source partial

- lead_pitch: 27.94 mm (DERIVED/L)
- end_cap_length: 1.59 mm (DERIVED/L)
- Formed pitch and tail trim are mounting choices; bend radius, shoulders, example band colors and coating appearance are visual defaults. No resistance/inductance value is asserted.
- Wirewound B column/cap interpretation, green coating, cap taper and lead geometry are not independently resolved.

### OHM-014 — source partial

- Dimensions M (single manufacturer, tolerance +/-0.254 is large), Geometry M, Materials/appearance L. Gap-fill: 0612 wide-terminal dimensions added (Vishay WSL0612 and Yageo PE0612, M). Unresolved: 3-terminal geometry, 4-terminal terminal roles (Yageo PS0612 B1..B5 and Vishay WSK E1/E2 edges), WSL2512 T/H per resistance range, WSLP and Bourns CSS/CSM not retrievable, relation of PKG-CHIP2T deltas to G01's numbers. Validation: pad center = (L - T)/2 = 1.815 and window L - 2T = 0.91 for 2512 (positive); size names imperial/metric stated. status partial.
- overall_height default 0.70 mm: resistance-range dependent, confidence L.
- terminal_length default 2.72 mm: second-pass narrative limits it to the lowest-ohm range (L); source YAML confidence M is preserved.
- MAT_ALLOY_MANGANIN is a G02 proposed token; appearance is an OHMNI default.
- 3/4-terminal Kelvin layouts unresolved; only the default 2-terminal 2512 is supported.

### OHM-015 — source partial

- hole_center_spacing: 60 (MFR_DATASHEET/L)
- Default style: bolt-on (Vishay WSBS8518...35 reference, gap-fill corrected, see PKG-SHUNT): overall length 85 +/-0.41 (M; the first-pass value 60 was the hole spacing), width 18 +/-0.20 (M), thickness 3.00 +/-0.05 (M), bolt hole dia 7 +/-0.10 (M), hole center spacing 60 (M-L, from sibling sheet 30134 only; positions X = +/-30), element length A 15.62 for 500 micro-ohm (B 17.65; A/B vary with resistance), sense pin spacing 9 +/-0.25 (M, axis unresolved). Blocks: copper, (85 - 17.65)/2 = 33.7 long each; chamfer 1.98 x 45 deg typ. OHMNI placeholders: sense pin dia 1.0 (L), sense pin length below strip 3.0 (L). RESEARCH_REQUIRED: sense pin axis/offset and length. Alternate SMD style (Isabellenhutte BVS 3920): L 10 (+0.3), W 5.2 (+0.3/-0.2), H 0.5 +/-0.1, land: l 11, w 6.2, a 2.7, x 5.6 (roles unresolved).
- 4 connection features: pins 1 and 2 = bolt holes dia 7 (terminal blocks, at X = -30 and +30, Y=0; c-c 60); pins 3 and 4 = sense pins at (-4.5, 0) and (+4.5, 0) going down (THT, dia 1.0, length 3.0, UNCERTAIN). Numbering: 1 at -X, 2 at +X, 3 at -X sense, 4 at +X sense. Terminal material copper (tinned/ nickel plated per brand, unverified).
- Sense pins THT holes dia 1.4 at (+/-4.5, 0); bolt holes through-board only if mounted to busbar (not modeled; the model has holes in the terminal blocks only). FCO origin: bbox of holes = X extent +/-30 (bolt holes) with pins inside, so origin at strip center. Body overhangs the hole pattern by 12.5 each end. Standoff default 0 (strip bottom at Z=0); real mounting heights UNCERTAIN.
- Dimensions M (length 85, width 18, thickness 3.0, hole dia 7 from a Vishay sheet; hole c-c 60 from the sibling sheet only), Geometry L, Materials/appearance L. Gap-fill resolved strip width and hole spacing; first-pass length 60 and width 15.62 were wrong readings and are superseded. Unresolved: sense pin axis/offset/length, plating colors, BVS 3920 land-pattern letter roles. Validation: holes at +/-30 with dia 7 leave 12.5 to the strip end (hole edge 9 mm from end, >= hole dia margin); element length 17.65 < hole spacing 60; 85 matches part name WSBS8518. status partial.
  
  ---
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=1.2: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-016 — source complete

- lead_thickness: 0.3 (UNCERTAIN/L)
- OHMNI default: 8 pins, bussed (4608X-101 style). Body length 20.27 max (2.54*8 - 0.05), body height (Z) 5.08 max (DERIVED from Vishay MSP A-profile 4.95 cross-check, M), body thickness (X) 3.3 (+0.5/-0.3) (MFR_DATASHEET, label association inferred, M), pitch 2.54 +/-0.07 (H), lead cross-section default 0.30 x 0.30 (UNCERTAIN), exposed lead length below body 2.29 max (Vishay MSP, M/L). Table by N in PKG-SIP_NET.
- N holes at pitch 2.54 in a line (hole dia 0.8 default, footprint choice). FCO origin = center of the pin row = body center. Standoff 0 (UNCERTAIN, real bodies sit up to ~0.5 above board). body_offset (0,0).
- Pin 1 marked by a dot or notch near the pin-1 end on the front face (datasheets show an identification on the drawing, form unspecified: RESEARCH_REQUIRED). For bussed networks pin 1 is the common pin.
- pin1_indicator: "dot near pin 1 end (style RESEARCH_REQUIRED)"
- Dimensions M, Geometry M, Materials/appearance L. Unresolved: lead cross-section and which of 3.3/5.08 is height; pin-1 mark style; standoff. Validation: body_length formula reproduces the 4 tabulated lengths; pin span (N-1)*2.54 = 17.78 < 20.27 body length (margin 1.245 each end); pin-1 at +Y by analogy with single-row rule (convention gap).
  
  ---
- COSMETIC_PROVISIONAL mark_height_fraction=0.65: Front-face pin1 dot at 65 percent of body height, within sourced envelope.
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=0.22: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-017 — source complete

- Dimensions M (column roles now confirmed by Panasonic EXB-38V A1/A2/B/G and Vishay CRA06P; 3 manufacturers agree on 3.2 x 1.6, P 0.80), Geometry M, Materials/appearance L. status complete (gap-fill): remaining unknowns are cosmetic: terminal count per type derived not stated (Vishay CRA06P and Panasonic confirm 4/8 terminal variants), no manufacturer pin-1 mark found (decal default). Validation: (4-1)*0.8 + 0.3 = 2.7 <= 3.2; 2*0.65 + 0.30 = 1.60 = W; pin counts CCW per architecture.
  
  ---
- COSMETIC_PROVISIONAL pad_stock=0.03: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=0.10666666666666667: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-018 — source partial

- pin_tail_length: 3.81 (UNCERTAIN/L)
- Default 3296W: body length (along row, Y) 9.53 (M, "3/8 in" naming plus callout plus KiCad Bourns_3296W body 9.53 x 4.83, two independent documents), thickness (X) 4.83 +/-0.13 (M), height above board 10.03 (M), 3 pins in line at 2.54 pitch (H), pin dia 0.51 +/-0.03 (H), pin tail below body 3.81 default (L, candidates 3.81 +/-0.71 and 6.4 +/-1.32), 25 turns nominal (H). Adjust screw boss/recess dia 2.19 (L). Slot width ~0.56 and depth ~0.76 (L, labels uncertain).
- Rectangular housing, flat top. Top adjust (W): a circular screw recess on the top face with a brass screw head and screwdriver slot; the screw center from the KiCad 3296W fab drawing (S5) is at Y = +3.495 (toward pin 1), X offset +1.15 from the body center, dia 2.19 (M-L; replaces the first-pass default Y = -2.54). Side adjust (X): screw head in the side/end face (position RESEARCH_REQUIRED). Pins exit the bottom face centered across the thickness.
- 3 holes (dia 0.9 default) at pitch 2.54 along Y. Origin FCO = center pin (pin 2) = body center along Y; body center offset 0 (KiCad 3296W footprint: pin row centered along the body and centered across the 4.83 thickness within 0.01, so offset (0,0) confirmed, M). KiCad pad 1.44 dia / drill 0.8 for reference (the 0.9 hole default stays an OHMNI choice). standoff: UNCERTAIN, 0 default (real trimmers often sit on molded standoffs ~0.5; not read).
- Dimensions M (body 9.53 x 4.83, pin pitch, pin row centering now confirmed by the KiCad 3296W footprint; height 10.03 and pin tail unchanged from first pass, L-M), Geometry M, Materials/appearance L. Gap-fill resolved: screw position (M-L), body offset (0,0), pin row centering, 3386P footprint pattern (in family section). Unresolved: pin tail length, standoff, 3296X side-adjust geometry, 3296Y/P/Z, 3386 height by style, housing color. Validation: KiCad 3296W pads 2.54 apart on a 9.53 body (span 5.08 < 9.53); pin span 5.08 fits within 9.53 body; 9.53 = 0.375 in matches "3/8 in"; callouts for tape/reel (12.70, 18) excluded. status partial.
  
  ---
- COSMETIC_PROVISIONAL rotor_depth=0.73: Recess within upper fifth of housing, limited by rotor diameter/3.
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=0.322: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-019 — source partial

- slot_length: 2.45 (MFR_DATASHEET/L)
- slot_width: 0.51 (MFR_DATASHEET/L)
- Low square block with a circular rotor on top: a flat-top round rotor (dia about 3.2, UNCERTAIN) with a screwdriver slot 2.45 x 0.51 across its diameter; thin plastic housing; terminal pads on the underside edges.
- Dimensions M (body 4.5 x 4.5 x 2.55 from Bourns datasheet re-read + element14 + KiCad body outline), Geometry M-L (pad centers from KiCad, S5; tab shape and rotor diameter not sourced), Materials/appearance L. Gap-fill resolved: 3314 height conflict (2.55 for G/J/H, 1.30 for R/S/Z), pad coordinates, FCO centering. Unresolved: actual terminal tab geometry (only land pattern known), rotor diameter (KiCad Fab marker 2.0 vs first-pass 3.2 guess; slot 2.45 callout exceeds a 2.0 rotor, so 3.2 kept), housing colors, 3224 pad association. Validation: pad bbox 3.6 x 6.8 is centered on the 4.5 square body; KiCad 3314G and 3314J agree on X pitch 2.30 and center; adopted height matches two sources. status partial (tab geometry and rotor diameter still unsourced).
- Dimensions M (body 4.5 x 4.5 x 2.55 from Bourns datasheet re-read + element14 + KiCad body outline), Geometry M-L (pad centers from KiCad, S5; tab shape and rotor diameter not sourced), Materials/appearance L. Gap-fill resolved: 3314 height conflict (2.55 for G/J/H, 1.30 for R/S/Z), pad coordinates, FCO centering. Unresolved: actual terminal tab geometry (only land pattern known), rotor diameter (KiCad Fab marker 2.0 vs first-pass 3.2 guess; slot 2.45 callout exceeds a 2.0 rotor, so 3.2 kept), housing colors, 3224 pad association. Validation: pad bbox 3.6 x 6.8 is centered on the 4.5 square body; KiCad 3314G and 3314J agree on X pitch 2.30 and center; adopted height matches two sources. status partial (tab geometry and rotor diameter still unsourced).
  
  ---
- COSMETIC_PROVISIONAL rotor_depth=0.51: Recess within upper fifth of housing, limited by rotor diameter/3.
- COSMETIC_PROVISIONAL slot_depth=0.255: One tenth housing height; inward rotor slot only.
- COSMETIC_PROVISIONAL pad_stock=0.1275: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=0.3: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-020 — source partial

- overall_height: 9.0 (UNCERTAIN/L)
- shaft_diameter: 6.0 (UNCERTAIN/L)
- RV16 (Taiwan Alpha catalog): thread options M6x0.75, M7x0.75, M8x0.75, M3/8x0.75; bushing length options 5.0, 6.5, 7.0, 8.0; shaft lengths 10, 15, 20, 25; angle 300 +/-5 deg. OHMNI defaults (all L unless noted): body diameter 16 (from the "16 mm" name, DERIVED, M-L), body height above PCB 9.0 (UNCERTAIN placeholder), bushing M7 x 0.75 (dia 7.0; Alps RK163 bushing width 7), bushing length 7.0, shaft dia 6.0 (L-M: Alps RK163 shaft width 6 corroborates; the Alpha sheet read gave 5, 6.5, 8), shaft length (from bushing top) 15. PTV09 alternate: bushing M9 x 0.75, plastic bushing length 11.4 +0/-0.5, shaft length options 15/20/25/30, mechanical angle 280 +/-10 deg, pin dia 1.0 +0.2/-0, pin spacing numbers 1.8 and 2.2 (+0.2/-0) as read; body dims about 10.0 x 5.5 x 6.8 as read, assignment unclear. Gap-fill: RV16 pin spacing 5.0 / drill 1.3 corroborated (M-L) only by the Alps RK163 (another manufacturer) footprint in the KiCad library; Alpha RV16 itself not opened beyond the first pass. 9 mm class (PTV09A-1, Alpha RD901F): pin pitch 2.5, shaft 7.5 from the pin row, mounting holes 8.8 to 9.6 apart (KiCad, M-L), see PKG-POT_ROTARY.
- 3 pins (1, 2 wiper, 3), flat or round, placeholder dia 1.0, spacing 5.0 along Y (M-L: Alps RK163 pitch 5.0, drill 1.3), tails to Z = -2.6 default. 9 mm alternate (PTV09/Alpha RD901F): pitch 2.5, drill 1.0, shaft on the pin-2 line 7.5 from the pin row. Pin 1 at +Y: (0, +5.0). Pin tail material MAT_TIN_BRIGHT.
- 3 holes dia 1.3 (placeholder), plus mounting tabs if present (not read). FCO origin = pin pattern center; shaft axis at body center; body_offset (0, 0) UNCERTAIN. Standoff 0.
- Dimensions L-M, Geometry M, Materials/appearance L. Gap-fill (search budget exhausted mid-pass; KiCad S5 used): pin pitch and drill of RV16 corroborated by an Alps 16 mm part (5.0 / 1.3); 9 mm footprints (PTV09A-1, Alpha RD901F: pitch 2.5, shaft offset 7.5, posts) added; PTV09 shaft styles F/S/U. Unresolved: RV16 body height, shaft tip type meanings for Alpha codes, PTV09 shaft diameter (KiCad marker 6.0 only), bushing nut/washer, mounting lugs of RV16. Validation: shaft_length options and bushing lengths taken from the sheet; angle 300 vs 280 deg per series; shaft dia 6.0 conflicts with read values 5/6.5/8 (flagged). status partial.
  
  ---
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=1.0666666666666667: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-028 — source partial

- thickness: 2.5 mm (MFR_DATASHEET/L)
- standoff: 1.0 mm (UNCERTAIN/L)
- Standoff, meniscus, fillets, resin face, lead taper and print placement are visual defaults; no certification/value is asserted.

### OHM-029 — source complete

- Sleeve overlap, vent-score shape/depth, bead, seal and printed sleeve dimensions are cosmetic construction defaults. Sleeve color is not source-verified.

### OHM-030 — source partial

- Sleeve overlap, vent-score shape/depth, bead, seal and printed sleeve dimensions are cosmetic construction defaults. Sleeve color is not source-verified.
- Base thickness 1.0 and terminal thickness .1 are visual defaults; H/K meaning unresolved. Base plate D+0.3 applies only through 10 mm. 12.5 mm and larger base/pad tables are not inferred or enabled.

### OHM-031 — source partial

- Sleeve overlap, vent-score shape/depth, bead, seal and printed sleeve dimensions are cosmetic construction defaults. Sleeve color is not source-verified.
- Snap-in 3-pin hole coordinates and terminal cross-section are unresolved. Only the sourced two-pin default is enabled; no third hole is invented. Seat diameter D-1 and height 2 are visual defaults.

### OHM-032 — source partial

- base_plate: 6.6 mm (DERIVED/L)
- overall_length: 7.8 mm (DERIVED/L)
- Sleeve overlap, vent-score shape/depth, bead, seal and printed sleeve dimensions are cosmetic construction defaults. Sleeve color is not source-verified.
- Base thickness 1.0 and terminal thickness .1 are visual defaults; H/K meaning unresolved. Base plate D+0.3 applies only through 10 mm. 12.5 mm and larger base/pad tables are not inferred or enabled.
- Polymer OS-CON base plate and terminals use the OHM-030 FK proxy; radial style B is outside this default record.

### OHM-033 — source complete

- Tantalum bevel .4, 3-degree draft and marking layout are cosmetic; end strips partition the nominal envelope instead of extending outside it.

### OHM-034 — source complete

- Tantalum bevel .4, 3-degree draft and marking layout are cosmetic; end strips partition the nominal envelope instead of extending outside it.

### OHM-035 — source complete

- Tantalum bevel .4, 3-degree draft and marking layout are cosmetic; end strips partition the nominal envelope instead of extending outside it.

### OHM-036 — source complete

- Tantalum bevel .4, 3-degree draft and marking layout are cosmetic; end strips partition the nominal envelope instead of extending outside it.

### OHM-037 — source complete

- standoff: 0.5 mm (UNCERTAIN/L)
- Standoff, meniscus, fillets, resin face, lead taper and print placement are visual defaults; no certification/value is asserted.

### OHM-038 — source complete

- standoff: 0.5 mm (UNCERTAIN/L)
- Standoff, meniscus, fillets, resin face, lead taper and print placement are visual defaults; no certification/value is asserted.

### OHM-039 — source complete

- Standoff, meniscus, fillets, resin face, lead taper and print placement are visual defaults; no certification/value is asserted.

### OHM-040 — source partial

- Sleeve overlap, vent-score shape/depth, bead, seal and printed sleeve dimensions are cosmetic construction defaults. Sleeve color is not source-verified.
- Default is Kyocera AVX SCC 10x20, not Eaton PB. Single summarized source; lead length, sleeve color and alternative styles remain uncertain.

### OHM-043 — source partial

- Unresolved: RESEARCH_REQUIRED terminal length e (no inductor datasheet opened gives it; TDK MLZ/MLK 3216, Taiyo Yuden and Samsung 3216 inductor sheets were not found, Coilcraft 1206CS is a different wirewound envelope). Body color per vendor; marking.
- terminal_length 0.50 mm is UNCERTAIN/L, borrowed from MLCC; not sourced for the inductor.

### OHM-044 — source complete

- standoff: 0.0 (UNCERTAIN/L)
- Land pattern values E/G etc. exist in the datasheet but their mapping was not verified: RESEARCH_REQUIRED. Underside at Z=0. Body centered on pad pattern; body_offset 0.
- Dimensions H / Geometry M / Materials-appearance L. Validation: pitch and pin positions checked against body length where available (pins lie inside body envelope); pin count matches geometry; pin-1 follows 00_architecture Section 6; unresolved items are marked RESEARCH_REQUIRED above. Mechanical drawings were not visually inspected (text extraction only).
- COSMETIC_PROVISIONAL pad_stock=0.051000000000000004: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=0.2: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[0.9, 0.28]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-045 — source partial

- standoff: 0.0 (UNCERTAIN/L)
- L 7.3 +-0.3, W 6.7 +-0.3 (ADOPTED; the second-pass datasheet read gives 6.7 with .264 in = 6.71 mm; the first pass had read 6.6 once, kept as a conflict note), H 2.8 +-0.2 (first pass; a second-pass label C = 1.8 +-0.3 under lead-frame terminal is probably the terminal length, unresolved). Recommended layout: 8.4 overall, 2.5 pad length, 3.5 (pad width or gap, UNCERTAIN). Basis MFR_DATASHEET, confidence M (H and terminal dims lower).
- 2 terminals, flat lead-frame, tin (Sn). Terminal width default 2.5 (UNCERTAIN, from layout ref), thickness 0.3 (UNCERTAIN). Pin 1 at -X. Centers x = +-2.95 (DERIVED from 8.4 overall minus 2.5 pad over 2).
- Dimensions M / Geometry M / Materials-appearance L. Validation: pitch 5.9 = 8.4 - 2.5 (outer span minus pad length); pads inside body envelope (outer pad span 8.4 > body 7.3, i.e. land extends past body, as expected for a land pattern); width conflict 6.6 vs 6.7 resolved to 6.7 by the inch value. Unresolved: height label (2.8 vs C 1.8), terminal width/thickness, XAL land patterns, drawings not visually inspected.
- COSMETIC_PROVISIONAL pad_stock=0.13999999999999999: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=0.44666666666666666: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[3.65, 1.675]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-046 — source partial

- pitch: 5.0 (UNCERTAIN/L)
- standoff: 0.0 (UNCERTAIN/L)
- Round drum: diameter 5.8 max, height 4.8 max (Bourns SDR0604 datasheet text via two hosted copies; RS listing "5.8 Dia. x 4.8mm"). A Farnell-hosted copy also lists terminal feature 1.8 and 6.0 overall (meaning unclear). The first pass assumed a square footprint; the sources call it a diameter, so the body is cylindrical (base plate may be square-ish, not documented). Pad pitch not given: DEFAULT 5.0 centre (UNCERTAIN; candidate 4.0 = 5.8 - 1.8). Basis MFR_DATASHEET, confidence M (body), L (pads).
- 2 bottom terminals, SnAgCu finish (datasheet); width 2.0 (UNCERTAIN). Pin 1 at -X, centers x = +-2.5 (DEFAULT).
- Pad centres +-2.5 (UNCERTAIN). Underside Z=0.
- Dimensions M (body) / L (pad pitch) ; Geometry L / Materials-appearance L. Validation: diameter and height confirmed by three S3/S4 documents; pads inside the body envelope; pitch 5.0 stays an OHMNI default. Unresolved: land pattern, terminal width, flange/winding proportions, drawings not visually inspected.
- COSMETIC_PROVISIONAL visual_terminal_size=[2, 2]: Use stated width (2.0, 1.25 or 0.30); remaining visual extent uses square width for drum/CMC or twice width for LAN foot. Contact centers unchanged; no land-pattern claim.
- COSMETIC_PROVISIONAL flange_height=0.7999999999999999: Each flange occupies one sixth sourced height.
- COSMETIC_PROVISIONAL barrel_diameter=3.77: 65 percent sourced flange diameter, inside envelope.
- COSMETIC_PROVISIONAL winding_diameter=4.93: 85 percent flange diameter, inside sourced cylinder.
- COSMETIC_PROVISIONAL pad_stock=0.2: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=0.38666666666666666: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[2.9, 1.45]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-047 — source partial

- pitch: 10.16 mm (DERIVED/L)
- standoff: 0.0 mm (UNCERTAIN/L)
- Formed pitch and tail trim are mounting choices; bend radius, shoulders, example band colors and coating appearance are visual defaults. No resistance/inductance value is asserted.
- Bourns 78F only distributor-supported; lead diameter .51 from narrative, coating green is an OHMNI default.

### OHM-048 — source complete

- standoff: 0.0 (UNCERTAIN/L)
- Holes dia 1.0 default (UNCERTAIN), pitch 5.0. Body seated on board with optional 0.5 standoff default 0.
- Shrinkable sleeve (125 C, 600 V per datasheet), color not stated in the opened text (commonly dark/black or colored with printed value; RESEARCH_REQUIRED). Wurth WE-TI 7447231471 is a different, 4-pin-or-2-pin sleeved drum; its second-pass datasheet read (dia 11 max, pin 0.8) did not match a 10 x 18 case and is not used for dimensions.
- Dimensions M / Geometry M / Materials-appearance L. Validation: body dia 8.7 < lead spacing + margins (leads at +-2.5 inside the footprint); datasheet and three distributor sources agree on 8.7 x 12.0 and 5.0; letters C, D, E of the datasheet not mapped (not needed). Sleeve color and dome shape undocumented but not key dimensions. Status complete for the key dimensions.
- COSMETIC_PROVISIONAL dome_height=0.6: Shallow rounded cap inside final 12 mm height, one twentieth height.
- COSMETIC_PROVISIONAL pad_stock=0.2: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=0.58: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[4.35, 2.175]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-049 — source partial

- standoff: 1.57 (DERIVED/L)
- OD 21.84 (0.86 in max), thickness 11.43 (0.45 in max), lead spacing 8.128 (0.32 in), lead dia 0.8636 (0.034 in), lead length 12.7 (0.5 in uncut), leads tinned to within 1.57 (0.062 in) of the mounting plane (Bourns 2100 series datasheet REV. 07/09, drawing callouts and table, plus RS/Octopart). ID default 12.0 = 0.55 OD (UNCERTAIN, not sourced). Dim B 0.75 in (19.05) unresolved. Confidence M.
- Torus with rounded-rectangular section, coated; copper turns possibly visible through the coat. The datasheet drawing shows both vertical and horizontal mounting; OHMNI default is the disc flat on the board (vertical axis Z) with two straight leads down. Exit geometry of leads otherwise RESEARCH_REQUIRED.
- 2 round leads dia 0.8636 at (-4.064,0) and (+4.064,0). Lead exit height RESEARCH_REQUIRED; default straight down from bottom.
- Dimensions M / Geometry L / Materials-appearance L. Validation: 0.32 in = 8.128 and 0.034 in = 0.8636 exactly match the RS values, 0.86/0.45 max match 21.84/11.43; leads (+-4.064) lie inside the OD. Unresolved: toroid ID, coat color, dim B 0.75 in meaning, whether leads exit radially/tangentially. A real toroid example: the 2100 series is a toroid; WE-TI is NOT (it is a sleeved drum, PKG-DRUM_IND).
- COSMETIC_PROVISIONAL pad_stock=0.2: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=1.456: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[10.92, 5.46]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-050 — source partial

- standoff: 0.0 (UNCERTAIN/L)
- WE-SL5 (adopted as default, S3): L 10.0 +-0.3, W 8.70 +-0.3, H 6.50 max; pad centres +-3.81 (E 7.62) by +-3.11 (D 6.22), land pads 2.7 x 2.7 (DERIVED from land 10.32 / 8.92), terminal width G 1.25. TDK ACM4520 (variant): 4.7 x 4.5 x 2.0 (lioncircuits + LCSC agree on 4.7 x 4.5; H single source), pad dims RESEARCH_REQUIRED. Confidence M (WE-SL5), L-M (ACM4520).
- 4 pads, CCW numbering from top-left. WE-SL5 centres: pin 1 (-3.81,+3.11), 2 (-3.81,-3.11), 3 (+3.81,-3.11), 4 (+3.81,+3.11); winding L1-2 and L4-3 (datasheet electrical table) so each winding sits on one side. Pad 2.7 x 2.7 land; component terminal width 1.25 (G), thickness UNCERTAIN. ACM4520 default pad 1.0 x 0.9 (UNCERTAIN).
- Dimensions M / Geometry L / Materials-appearance L. Validation: land numbers decompose exactly into E + 2.7 = 10.32 and D + 2.7 = 8.92, supporting pads of 2.7 x 2.7 at the E/D centres; pad centres lie within the 10.0 x 8.7 body footprint region (pads partly overhang as in a land pattern); 4 pins CCW. Unresolved: letter-to-feature mapping not visually verified, ACM4520 pad geometry and height (single source), dot position. Default material changed to MAT_PLASTIC_BLACK for the WE-SL5 housing (datasheet says UL94-V0 housing).
- COSMETIC_PROVISIONAL visual_terminal_size=[1.25, 1.25]: Use stated width (2.0, 1.25 or 0.30); remaining visual extent uses square width for drum/CMC or twice width for LAN foot. Contact centers unchanged; no land-pattern claim.
- COSMETIC_PROVISIONAL pad_stock=0.2: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=0.58: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[5.0, 2.175]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-051 — source partial

- overall_height: 18.0 (MFR_DATASHEET/L)
- standoff: 0.0 (UNCERTAIN/L)
- 4 round pins dia 0.8 default (UNCERTAIN; hole 1.1 per datasheet). Pin 1 (-5.0,+2.25), 2 (-5.0,-2.25), 3 (+5.0,-2.25), 4 (+5.0,+2.25) (rows 10.0 apart in X, pitch 4.5 in Y; Wurth pin numbering 1-4 in a rectangle, order not visually confirmed).
- Case color black/blue; RESEARCH_REQUIRED.
- Dimensions L-M / Geometry L / Materials-appearance L. Validation: pin rows (10.0) fit within the 15.8 body length and pitch 4.5 within width 7.8 (rows may overhang if the 18.0 axis is the long one: unresolved); pin count 4. Unresolved: axis assignment of 15.8/18.0/10.0, pin diameter, case color/shape, pin numbering order.
- COSMETIC_PROVISIONAL pad_stock=0.2: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=0.52: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[7.9, 1.95]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-052 — source partial

- standoff: 0.0 (UNCERTAIN/L)
- Body MAT_PLASTIC_BLACK (RESEARCH_REQUIRED); pins MAT_TIN_BRIGHT.
- Case/color not in datasheet: RESEARCH_REQUIRED.
- Second pass: no new source found (Triad TY-145P not re-opened; pin cross-section 0.0375 x 0.020 in vs .042 sq conflict still open; case color not documented), so status stays partial. YAML basis upgraded from UNCERTAIN to MFR_DATASHEET to match the already opened Triad datasheet. Dimensions M / Geometry L / Materials-appearance L. Validation: pitch and pin positions checked against body length where available (pins lie inside body envelope); pin count matches geometry; pin-1 follows 00_architecture Section 6; unresolved items are marked RESEARCH_REQUIRED above. Mechanical drawings were not visually inspected (text extraction only).
- COSMETIC_PROVISIONAL pad_stock=0.2: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=1.1866666666666668: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[8.9, 5.15]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-053 — source partial

- pitch: 2.5 (UNCERTAIN/L)
- row_spacing: 29.24 (UNCERTAIN/L)
- standoff: 0.0 (UNCERTAIN/L)
- WE-FB 750311595: overall max 32.31 x 27.03 x 13.69 (S3, drawing callouts; 13.69 = height; 32.31 is the finished-part plan envelope, not the 25 mm EFD25 core length, which resolves the first-pass oddity). Top-view typ values 29.24 +-0.05 and 28.0; land pattern callouts 30.38, 3.76, 2.5, 1.52 (mapping to row spacing / pin pitch NOT confirmed; candidate row spacing 29.24, pitch 2.5; UNCERTAIN, L). WE-OLSTM 750871111: 25.0 / 21.0 / 16.0 max (axes unresolved). Confidence L-M.
- WE-FB 750311595: 12 pins, pins 1-6 on one side, 7-12 on the other; pin 1 marked with a dot; windings N1 (pin 1...), N2 (6,7...), N3 (12,1...) per the extraction (exact pin lists unreliable). Pin diameter RESEARCH_REQUIRED. WE-OLSTM 750871111: pin positions 1..14 (windings on pins 1,3,4 / 6 / 7,9,12,14), which contradicts the first-pass 6 pins.
- Candidate only: two rows, 12 holes, row spacing about 29.24 (or 28.0), pitch 2.5 (UNCERTAIN, from unlabelled land-pattern callouts 30.38 / 3.76 / 2.5 / 1.52). Hole diameter RESEARCH_REQUIRED. Body offset 0.
- 1 Core as two E/EFD blocks (envelope within 32.31 x 27.03 x 13.69, EFD25 core nominal 25 mm long, from EFD25 designation, not read from drawing) on a bobbin box with flanges. 2 Pins in two rows of 6. 3 Tape wrap. Dimensions are envelope-level only; pin pitch/row spacing carry UNCERTAIN tags.
- Dimensions L-M (envelope M, pin layout L) / Geometry L / Materials-appearance L. Validation: 12 pins = 2 rows x 6; envelope 32.31 exceeds the 29.24 candidate row spacing, consistent with pins lying inside the envelope; EFD25 oddity explained as envelope vs core designation. Still unresolved: pin pitch and row spacing (text extraction could not read the drawing), pin diameter, hole size, pin 1 coordinates, tape color (yellow is de facto). Status moved research_required to partial because envelope dimensions are sourced.
- COSMETIC_PROVISIONAL visual_pin_diameter=0.5: One fifth of stated provisional 2.5 mm pitch, visual stock only; no hole diameter or footprint claim. Within body XY envelope.
- COSMETIC_PROVISIONAL bobbin_base=1.71125: Lower eighth of sourced height; full sourced plan envelope.
- COSMETIC_PROVISIONAL flange_stock=1.6155000000000002: One twentieth sourced X envelope; two inner flanges, do not move pin rows.
- COSMETIC_PROVISIONAL core_width=24.2325: 75 percent X envelope, bounded by bobbin flanges; no EFD core datasheet dimension asserted.
- COSMETIC_PROVISIONAL core_length=24.327: 90 percent Y envelope, inside sourced envelope.
- COSMETIC_PROVISIONAL core_stock=2.738: Core rails and center leg stock one fifth overall height.
- COSMETIC_PROVISIONAL tape_width=12.1635: Tape winding band 45 percent body Y span, inside core window.
- COSMETIC_PROVISIONAL pad_stock=0.2: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=1.802: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[16.155, 6.7575]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-054 — source partial

- body_length: 17.2 (UNCERTAIN/L)
- body_width: 9.53 (UNCERTAIN/L)
- overall_height: 20.4 (UNCERTAIN/L)
- standoff: 0.0 (UNCERTAIN/L)
- 3 in-line pins labeled 1, 2, 3; pin 2 exists on center-tapped versions only (AS series datasheet). Centres (-6.35,0), (0,0), (+6.35,0) (pitch 0.250 in, span 12.7). Pin cross-section RECTANGULAR 0.66 x 0.45 mm (two copies of the datasheet agree), replacing the first-pass round 1.0 default. Primary/secondary assignment not confirmed.
- Holes for 0.66 x 0.45 pins: DEFAULT 1.0 round or 0.9 x 0.7 slot (UNCERTAIN, not sourced); body offset 0. A 5.0 mm mounting hole is mentioned in the AS drawing (function unresolved).
- RESEARCH_REQUIRED.
- Second pass: pin cross-section and pitch now from the Talema datasheet; body axis assignment (9.53, 12.7, 20.4) still conflicting between readings, so status stays partial. Dimensions L-M / Geometry L / Materials-appearance L. Validation: pitch and pin positions checked against body length where available (pins lie inside body envelope); pin count matches geometry; pin-1 follows 00_architecture Section 6; unresolved items are marked RESEARCH_REQUIRED above. Mechanical drawings were not visually inspected (text extraction only).
- COSMETIC_PROVISIONAL pad_stock=0.2: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=0.6353333333333333: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[8.6, 2.3825]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-055 — source partial

- body_length: 9.53 (MFR_DATASHEET/L)
- overall_height: 6.8 (MFR_DATASHEET/L)
- standoff: 0.0 (UNCERTAIN/L)
- L 12.70 +-0.15 (along rows), W 9.53, H 6.80 (H1183NL 5.59), pitch 1.27. Row spacing default 10.16 (UNCERTAIN). Basis MFR_DATASHEET, M for L and pitch. Second-pass re-read of the same Pulse sheet conflicts for W/H: width .268 (6.80) and height .240 (6.09) with land callouts .236 (6.00) and .380; first-pass W 9.53 / H 6.80 retained as default, conflict flagged (W/H confidence L-M).
- Rows span 10.16 default (UNCERTAIN). Body offset 0.
- Black plastic with white print; pin-1 dot RESEARCH_REQUIRED.
- Second pass: length and pitch confirmed by two reads; W/H conflict and row spacing (land callouts 6.00 / 9.53-9.65) unresolved; 24-pin members not found; status stays partial. YAML axes note: pin coordinates place the 8-pin rows along Y, so body_length (X) = 9.53 and body_width (Y) = 12.7 is the consistent assignment; the entry text calls 12.70 the length along the rows. Dimensions M / Geometry L / Materials-appearance L. Validation: pitch and pin positions checked against body length where available (pins lie inside body envelope); pin count matches geometry; pin-1 follows 00_architecture Section 6; unresolved items are marked RESEARCH_REQUIRED above. Mechanical drawings were not visually inspected (text extraction only).
- COSMETIC_PROVISIONAL visual_terminal_size=[0.6, 0.3]: Use stated width (2.0, 1.25 or 0.30); remaining visual extent uses square width for drum/CMC or twice width for LAN foot. Contact centers unchanged; no land-pattern claim.
- COSMETIC_PROVISIONAL pad_stock=0.2: Metal visual stock one twentieth height capped0.2, contact plane unchanged.
- COSMETIC_PROVISIONAL marker_diameter=0.6353333333333333: OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal.
- COSMETIC_PROVISIONAL winding_turns=8: Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim.
- COSMETIC_PROVISIONAL label_size=[4.765, 3.175]: Optional separate label decal occupies half X and quarter Y of top face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-056 — source complete

- lead_pitch: 7.62 mm (DERIVED/L)
- hole_diameter: 0.9 mm (DERIVED/L)
- Cathode band width and bend radius are OHMNI defaults; hole pitch and tail truncation are mounting choices.

### OHM-057 — source complete

- lead_pitch: 10.16 mm (DERIVED/L)
- hole_diameter: 1.1 mm (DERIVED/L)
- Cathode band width and bend radius are OHMNI defaults; hole pitch and tail truncation are mounting choices.

### OHM-058 — source complete

- lead_pitch: 15.24 mm (DERIVED/L)
- hole_diameter: 1.6 mm (DERIVED/L)
- Cathode band width and bend radius are OHMNI defaults; hole pitch and tail truncation are mounting choices.

### OHM-059 — source complete

- Band width/color and cap/body diameter assignment are inferred; glass/plastic appearance varies by manufacturer.

### OHM-060 — source complete

- Band width/color and cap/body diameter assignment are inferred; glass/plastic appearance varies by manufacturer.

### OHM-061 — source complete

- foot_length: 0.85 mm (UNCERTAIN/L)
- standoff: 0.05 mm (UNCERTAIN/L)
- Lead exit height, band position/width and folded profile bend details are OHMNI defaults.

### OHM-062 — source complete

- foot_length: 0.6 mm (UNCERTAIN/L)
- standoff: 0.05 mm (UNCERTAIN/L)
- Lead exit height, band position/width and folded profile bend details are OHMNI defaults.

### OHM-063 — source complete

- foot_length: 0.35 mm (UNCERTAIN/L)
- standoff: 0.0 mm (UNCERTAIN/L)
- Lead exit height, band position/width and folded profile bend details are OHMNI defaults.
- SOD523 0.30 mm extracted lead thickness is unresolved; use the entry 0.12 mm default.

### OHM-064 — source complete

- foot_length: 1.1 mm (UNCERTAIN/L)
- standoff: 0.1 mm (UNCERTAIN/L)
- Lead exit height, band position/width and folded profile bend details are OHMNI defaults.
- Polarity-side body chamfer/step is RESEARCH_REQUIRED and deliberately omitted; cathode band only.

### OHM-065 — source complete

- foot_length: 1.1 mm (UNCERTAIN/L)
- standoff: 0.1 mm (UNCERTAIN/L)
- Lead exit height, band position/width and folded profile bend details are OHMNI defaults.
- Polarity-side body chamfer/step is RESEARCH_REQUIRED and deliberately omitted; cathode band only.

### OHM-066 — source complete

- foot_length: 1.1 mm (UNCERTAIN/L)
- standoff: 0.1 mm (UNCERTAIN/L)
- Lead exit height, band position/width and folded profile bend details are OHMNI defaults.
- Polarity-side body chamfer/step is RESEARCH_REQUIRED and deliberately omitted; cathode band only.

### OHM-067 — source complete

- foot_length: 0.85 mm (UNCERTAIN/L)
- foot_length: 0.85 mm (UNCERTAIN/L)
- standoff: 0.05 mm (UNCERTAIN/L)
- Lead exit height, band position/width and folded profile bend details are OHMNI defaults.

### OHM-068 — source complete

- foot_length: 0.85 mm (UNCERTAIN/L)
- foot_length: 0.85 mm (UNCERTAIN/L)
- standoff: 0.05 mm (UNCERTAIN/L)
- Lead exit height, band position/width and folded profile bend details are OHMNI defaults.

### OHM-069 — source complete

- lead_width: 2.2 mm (MFR_DRAWING/L)
- foot_length: 1.1 mm (UNCERTAIN/L)
- standoff: 0.1 mm (UNCERTAIN/L)
- Lead exit height, band position/width and folded profile bend details are OHMNI defaults.
- Polarity-side body chamfer/step is RESEARCH_REQUIRED and deliberately omitted; cathode band only.

### OHM-071 — source partial

- standoff: 1.0 mm (UNCERTAIN/L)
- Pin-to-function map RESEARCH_REQUIRED. Printed + near pin1 is only the spec visual placeholder; remaining function symbols have no positional pin assignment.
- Standoff and round/flat lead form, pin1 bevel and manufacturer marking positions remain uncertain.

### OHM-072 — source partial

- standoff: 0.5 mm (UNCERTAIN/L)
- Pin-to-function map RESEARCH_REQUIRED. Printed + near pin1 is only the spec visual placeholder; remaining function symbols have no positional pin assignment.
- Standoff and round/flat lead form, pin1 bevel and manufacturer marking positions remain uncertain.

### OHM-073 — source complete

- standoff: 0 mm (UNCERTAIN/L)
- Cathode flat depth .4 (rectangular chamfer .5), lead cross-section and 1 mm LOD2 anode extension are unsourced visual defaults. Dome is hemispherical.

### OHM-074 — source complete

- standoff: 0 mm (UNCERTAIN/L)
- Cathode flat depth .4 (rectangular chamfer .5), lead cross-section and 1 mm LOD2 anode extension are unsourced visual defaults. Dome is hemispherical.

### OHM-075 — source partial

- flange_thickness: 1.2 mm (UNCERTAIN/L)
- standoff: 0 mm (UNCERTAIN/L)
- Cathode flat depth .4 (rectangular chamfer .5), lead cross-section and 1 mm LOD2 anode extension are unsourced visual defaults. Dome is hemispherical.
- 10 mm LED flange thickness 1.2 mm is a placeholder with only <1.5 bound; single numeric drawing, not cross-verified.

### OHM-076 — source partial

- overall_height: 7.0 mm (CONSENSUS/L)
- Cathode flat depth .4 (rectangular chamfer .5), lead cross-section and 1 mm LOD2 anode extension are unsourced visual defaults. Dome is hemispherical.

### OHM-077 — source partial

- terminal_length: 0.2 mm (UNCERTAIN/L)
- Emitter window/cavity, resin cap height, mark size and terminal bend/thickness are visual defaults, not drawing-verified.

### OHM-078 — source complete

- terminal_length: 0.4 mm (UNCERTAIN/L)
- Emitter window/cavity, resin cap height, mark size and terminal bend/thickness are visual defaults, not drawing-verified.

### OHM-079 — source partial

- terminal_length: 0.5 mm (UNCERTAIN/L)
- Emitter window/cavity, resin cap height, mark size and terminal bend/thickness are visual defaults, not drawing-verified.

### OHM-080 — source partial

- terminal_length: 0.6 mm (UNCERTAIN/L)
- Emitter window/cavity, resin cap height, mark size and terminal bend/thickness are visual defaults, not drawing-verified.

### OHM-081 — source partial

- terminal_length: 1.0 mm (UNCERTAIN/L)
- Emitter window/cavity, resin cap height, mark size and terminal bend/thickness are visual defaults, not drawing-verified.

### OHM-082 — source partial

- overall_height: 1.9 mm (CONSENSUS/L)
- Emitter window/cavity, resin cap height, mark size and terminal bend/thickness are visual defaults, not drawing-verified.
- Neutral cool diffuser tint is an OHMNI unlit appearance default, chosen to distinguish the cavity from the white case.
- RGB channel-to-pin functions remain UNKNOWN; CCW pin numbering is geometric only. The general two-terminal cathode rule does not assign RGB channel functions.

### OHM-083 — source partial

- terminal_length: 0.8 mm (UNCERTAIN/L)
- Emitter window/cavity, resin cap height, mark size and terminal bend/thickness are visual defaults, not drawing-verified.
- Neutral cool diffuser tint is an OHMNI unlit appearance default, chosen to distinguish the cavity from the white case.
- RGB channel-to-pin functions remain UNKNOWN; CCW pin numbering is geometric only. The general two-terminal cathode rule does not assign RGB channel functions.

### OHM-084 — source partial

- Emitter window/cavity, resin cap height, mark size and terminal bend/thickness are visual defaults, not drawing-verified.
- Neutral cool diffuser tint is an OHMNI unlit appearance default, chosen to distinguish the cavity from the white case.
- WS2812B pin1/chamfer top-left is KiCad convention, not confirmed manufacturer corner; 5.0 vs 5.4 and lead dimensions remain provisional.

### OHM-085 — source partial

- overall_height: 2.0 mm (MFR_DATASHEET/L)
- lens_diameter: 2.96 mm (DERIVED/L)
- lens_height: 1.15 mm (MFR_DATASHEET/L)
- Emitter total height 2.0 vs 2.45, underside pad sizes, phosphor and cathode marker placement remain provisional.

### OHM-086 — source partial

- mounting_hole_spacing: 17.5 mm (MFR_DATASHEET/L)
- overall_height: 3.65 mm (DERIVED/L)
- Emitter total height 2.0 vs 2.45, underside pad sizes, phosphor and cathode marker placement remain provisional.
- Star wire-pad sizes/positions are illustrative, not source geometry. Hole spacing 17.5 lacks diameter/coordinates; optic/mounting holes and vendor lobes omitted. Hex default has no invented holes.

### OHM-087 — source partial

- Box housing 19.05 x 12.7 x 8.0 mm with square-cut edges. The top face carries a flat face plate (gray default) with 1 digit window(s); each digit is 7 white bar segments plus a right-hand DP in a figure-8 arrangement (DERIVED proportions from PKG-7SEG generator notes: bar stroke 0.14 h, digit width 0.62 h, DP dia 0.15 h). Segments are slightly recessed (~0.1, UNCERTAIN) below the face plate; face plate is flush with the housing top. Digit UP direction = +X at rotation 0. The DP sits at the digit's lower-right, i.e. at the -X (bottom) and -Y (right) corner of each digit window (PKG-7SEG orientation note).
- 10 pins, 2.54 mm pitch, rows parallel to Y at X = -7.62 and +7.62, pin Y positions [5.08, 2.54, 0.0, -2.54, -5.08]. Pin 1 at (-7.62, 5.08); pins 1..5 down the -X row; pins 6..10 up the +X row (pin 6 at (+7.62, -5.08)). Shape: flat/square pin 0.5 x 0.25 (UNCERTAIN; not legible in any drawing), tin-plated (MAT_TIN_BRIGHT). Tail bottom -2.6 (default); body standoff 0 (UNCERTAIN). Functional pin map (segment to pin) depends on common anode/cathode and vendor and is RESEARCH_REQUIRED (not legible).
- Through-hole footprint, hole 0.9-1.0 recommended (OHMNI default 1.0, UNCERTAIN), pads 1.6-1.8. FCO origin at the center of the pin bounding box: X +/-7.62, Y +/-5.08; body_offset = (0, 0) (pins assumed centered on body; RESEARCH_REQUIRED for the 4-digit part). Pin 1 at (-7.62, 5.08).
- Dimensions M; Geometry M (segment proportions DERIVED); Materials/appearance M. Unresolved: pin cross-section and hole sizes, segment dimensions, pin-to-segment map, face-plate recess, standoff, 0.28/0.36 classes. Validation: pitch 2.54 x (5-1) = 10.16 vs listed body Y 12.7 (fits); pin count 10 = 2 x 5; pin 1 follows dual-row rule; row spacing 15.24 < body X 19.05.
  
  
  ---
- COSMETIC_PROVISIONAL face_depth=0.1: Entry approximate 0.1 recess; plate partition within sourced body height.
- COSMETIC_PROVISIONAL digit_layout={'horizontal_bias': -0.06, 'dp_x': 0.38, 'dp_y': -0.43, 'bar_y': 0.43, 'vertical_x': 0.24, 'vertical_y': 0.215, 'bar_length': 0.48, 'vertical_length': 0.32}: Dimensionless proportions of sourced digit height, inside digit cell; preserves entry UP=+X and lower-right DP. Bias leaves room for DP inside 12.7 mm single-digit face.
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=0.8466666666666666: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-088 — source partial

- Box housing 19.05 x 25.0 x 8.0 mm with square-cut edges. The top face carries a flat face plate (gray default) with 2 digit window(s); each digit is 7 white bar segments plus a right-hand DP in a figure-8 arrangement (DERIVED proportions from PKG-7SEG generator notes: bar stroke 0.14 h, digit width 0.62 h, DP dia 0.15 h). Segments are slightly recessed (~0.1, UNCERTAIN) below the face plate; face plate is flush with the housing top. Digit UP direction = +X at rotation 0. The DP sits at the digit's lower-right, i.e. at the -X (bottom) and -Y (right) corner of each digit window (PKG-7SEG orientation note).
- 18 pins, 2.54 mm pitch, rows parallel to Y at X = -7.62 and +7.62, pin Y positions [10.16, 7.62, 5.08, 2.54, 0.0, -2.54, -5.08, -7.62, -10.16]. Pin 1 at (-7.62, 10.16); pins 1..9 down the -X row; pins 10..18 up the +X row (pin 10 at (+7.62, -10.16)). Shape: flat/square pin 0.5 x 0.25 (UNCERTAIN; not legible in any drawing), tin-plated (MAT_TIN_BRIGHT). Tail bottom -2.6 (default); body standoff 0 (UNCERTAIN). Functional pin map (segment to pin) depends on common anode/cathode and vendor and is RESEARCH_REQUIRED (not legible).
- Through-hole footprint, hole 0.9-1.0 recommended (OHMNI default 1.0, UNCERTAIN), pads 1.6-1.8. FCO origin at the center of the pin bounding box: X +/-7.62, Y +/-10.16; body_offset = (0, 0) (pins assumed centered on body; RESEARCH_REQUIRED for the 4-digit part). Pin 1 at (-7.62, 10.16).
- Dimensions M; Geometry M (segment proportions DERIVED); Materials/appearance M. Unresolved: pin cross-section and hole sizes, segment dimensions, pin-to-segment map, face-plate recess, standoff, 0.28/0.36 classes. Validation: pitch 2.54 x (9-1) = 20.32 vs listed body Y 25.0 (fits); pin count 18 = 2 x 9; pin 1 follows dual-row rule; row spacing 15.24 < body X 19.05.
  
  
  ---
- COSMETIC_PROVISIONAL face_depth=0.1: Entry approximate 0.1 recess; plate partition within sourced body height.
- COSMETIC_PROVISIONAL digit_layout={'horizontal_bias': -0.06, 'dp_x': 0.38, 'dp_y': -0.43, 'bar_y': 0.43, 'vertical_x': 0.24, 'vertical_y': 0.215, 'bar_length': 0.48, 'vertical_length': 0.32}: Dimensionless proportions of sourced digit height, inside digit cell; preserves entry UP=+X and lower-right DP. Bias leaves room for DP inside 12.7 mm single-digit face.
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=1.27: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-089 — source partial

- Box housing 19.0 x 50.3 x 8.35 mm with square-cut edges. The top face carries a flat face plate (gray default) with 4 digit window(s); each digit is 7 white bar segments plus a right-hand DP in a figure-8 arrangement (DERIVED proportions from PKG-7SEG generator notes: bar stroke 0.14 h, digit width 0.62 h, DP dia 0.15 h). Segments are slightly recessed (~0.1, UNCERTAIN) below the face plate; face plate is flush with the housing top. Digit UP direction = +X at rotation 0. The DP sits at the digit's lower-right, i.e. at the -X (bottom) and -Y (right) corner of each digit window (PKG-7SEG orientation note).
- 12 pins, 2.54 mm pitch, rows parallel to Y at X = -7.62 and +7.62, pin Y positions [6.35, 3.81, 1.27, -1.27, -3.81, -6.35]. Pin 1 at (-7.62, 6.35); pins 1..6 down the -X row; pins 7..12 up the +X row (pin 7 at (+7.62, -6.35)). Shape: flat/square pin 0.5 x 0.25 (UNCERTAIN; not legible in any drawing), tin-plated (MAT_TIN_BRIGHT). Tail bottom -2.6 (default); body standoff 0 (UNCERTAIN). Functional pin map (segment to pin) depends on common anode/cathode and vendor and is RESEARCH_REQUIRED (not legible).
- Through-hole footprint, hole 0.9-1.0 recommended (OHMNI default 1.0, UNCERTAIN), pads 1.6-1.8. FCO origin at the center of the pin bounding box: X +/-7.62, Y +/-6.35; body_offset = (0, 0) (pins assumed centered on body; RESEARCH_REQUIRED for the 4-digit part). Pin 1 at (-7.62, 6.35).
- Dimensions M; Geometry M (segment proportions DERIVED); Materials/appearance M. Unresolved: pin cross-section and hole sizes, segment dimensions, pin-to-segment map, face-plate recess, standoff, 0.28/0.36 classes. Validation: pitch 2.54 x (6-1) = 12.7 vs listed body Y 50.3 (fits); pin count 12 = 2 x 6; pin 1 follows dual-row rule; row spacing 15.24 < body X 19.0.
  
  
  ---
- COSMETIC_PROVISIONAL face_depth=0.1: Entry approximate 0.1 recess; plate partition within sourced body height.
- COSMETIC_PROVISIONAL digit_layout={'horizontal_bias': -0.06, 'dp_x': 0.38, 'dp_y': -0.43, 'bar_y': 0.43, 'vertical_x': 0.24, 'vertical_y': 0.215, 'bar_length': 0.48, 'vertical_length': 0.32}: Dimensionless proportions of sourced digit height, inside digit cell; preserves entry UP=+X and lower-right DP. Bias leaves room for DP inside 12.7 mm single-digit face.
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=1.2666666666666666: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-090 — source partial

- overall_length: 32.0 (UNCERTAIN/L)
- overall_width: 32.0 (UNCERTAIN/L)
- overall_height: 8.0 (UNCERTAIN/L)
- row_spacing: 25.4 (UNCERTAIN/L)
- - Class A, priority P2, complexity 3. STATUS partial (gap-fill pass): pin count (16), pin span, dot pitch 4.00 and dot dia 1.9 now come from a 1.2 in 8x8 datasheet; body Z, row spacing, face plate details remain placeholders.
- Body 32.0 x 32.0 x 8.0 (32 mm: LightKey LM12088 1.20 in class and retailer listing, M-L; Z 8.0 UNCERTAIN); alt 20.0 x 20.0 x 8.0 (unsourced). Pins 16 (8/row), pitch 2.54 (LightKey LM12088, M), pin Y span 17.78 (7 x 2.54, matches the sheet), row spacing 25.4 (UNCERTAIN placeholder, RESEARCH_REQUIRED). Dot pitch 4.00 and dot dia 1.9 (LightKey LM12088; first-pass 3.75 / 3.0 placeholders superseded; note TinyTronics gives 3 mm LED pitch and a seller listing for 1588BS gives 3.75 mm dots on a 38 mm body, so real 8x8 parts vary by size class; adopt sourced LightKey values). RESEARCH_REQUIRED: row spacing, height, face plate recess; Kingbright TC23-11 (58 mm, 5 mm dots) numerics did not extract.
- 16 round/flat pins (0.5 x 0.25 UNCERTAIN) in two rows of 8 at X = +/-12.7 (row spacing 25.4 placeholder), Y = +8.89, 6.35, 3.81, 1.27, -1.27, -3.81, -6.35, -8.89. Pin 1 at (-12.7, +8.89); pins 1-8 down the -X row; 9-16 up the +X row. Pin-to-row/column mapping RESEARCH_REQUIRED. Tails to -2.6.
- Through-hole, hole 1.0 (UNCERTAIN), pad 1.8; FCO origin at the pin-pattern center; body_offset (0,0) assumed.
- Dimensions L-M (pins, pitch, dot pitch/dia M from one 1.2 in datasheet; body Z and row spacing L); Geometry M (generic); Materials/appearance L. RESEARCH_REQUIRED: height, row spacing, pin-to-row/column map, a real 58 mm Kingbright TC23-11 drawing (numerics did not extract). Conflict kept: first-pass 24 pins / 3.75 / 3.0 placeholders replaced by 16 / 4.00 / 1.9 because the latter come from a datasheet. Validation: 8 x 2.54 span 17.78 < 32.0 body; pin count 16 = 2 x 8; 7 x 4.00 + 1.9 = 29.9 < 32.
- Dimensions L-M (pins, pitch, dot pitch/dia M from one 1.2 in datasheet; body Z and row spacing L); Geometry M (generic); Materials/appearance L. RESEARCH_REQUIRED: height, row spacing, pin-to-row/column map, a real 58 mm Kingbright TC23-11 drawing (numerics did not extract). Conflict kept: first-pass 24 pins / 3.75 / 3.0 placeholders replaced by 16 / 4.00 / 1.9 because the latter come from a datasheet. Validation: 8 x 2.54 span 17.78 < 32.0 body; pin count 16 = 2 x 8; 7 x 4.00 + 1.9 = 29.9 < 32.
  
  
  ---
- COSMETIC_PROVISIONAL face_depth=0.1: Entry approximate 0.1 recess; plate partition within sourced body height.
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=2.1333333333333333: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-091 — source partial

- pcb_thickness: 1.6 (UNCERTAIN/L)
- All from PKG-LCD_CHARACTER (Winstar WH1602 series, Vishay LCD-016N001A): PCB 80.0 x 36.0 (tol +/-0.3), module thickness 13.2 max (default; 10.0 and 13.5 variants), view area 66.0 x 16.0, active area 56.20 x 11.5, character 2.95 x 5.55 mm, character pitch 3.55 x 5.95, dot 0.55 x 0.65, dot pitch 0.60 x 0.70, 16 pins 1.0 PTH on 1.8 pads, pitch 2.54 (15 x 2.54 = 38.1), 4 holes 2.5 PTH on 5.0 pads at 75.0 x 31.0 centers. PCB thickness 1.6 (UNCERTAIN, RESEARCH_REQUIRED). Basis MFR_DATASHEET; confidence H for outline/view/active/holes (several Winstar sheets plus Vishay agree), M for thickness, L for PCB thickness, bezel, header X position.
- Sub-bodies (Z up from PCB underside = module Z0): (1) PCB 80.0 x 36.0 x 1.6, square corners (UNCERTAIN). (2) LCD glass+polarizer+backlight stack: footprint ~71 x 25 (DERIVED, UNCERTAIN), from PCB top to 13.2 total (stack height = 13.2 - 1.6; the H2 callouts 8.6-8.9 in Vishay/Raystar sheets are unresolved). (3) Metal bezel frame, outer 70.0 x 26.0 centered (DERIVED, UNCERTAIN), window 66.0 x 16.0 centered (view area), top at 13.2; bent tabs optional (LOD2). (4) Polarizer inside the window showing 2 rows x 16 characters of 5x8 dots (decal: 2.95 x 5.55 characters, pitch 3.55 x 5.95; active area 56.20 x 11.5 centered in the window). (5) Header: 16 round pins on a single row. (6) Backlight: LED at the edge or back (pins 15, 16 = A, K); not modeled externally for the default. Reading orientation: header along the top (+Y) edge, pin 1 at the left (-X).
- 16 round pins (1.0 PTH hole per the sheets; pin dia 0.64 UNCERTAIN), pitch 2.54 along X. Pin 1 at (-19.05, 15.5) from the pin/hole bbox center, pin 16 at (+19.05, 15.5): pin row Y aligned with the mounting-hole row (hole row at +/-15.5 from center; DERIVED from the 2.5 mm callout), pin X centered (RESEARCH_REQUIRED; pin-1 offset callouts of 2.0 / 2.5 / 4.95 conflict). DEVIATION from the single-row header rule (Section 6, row along Y): the module stays in display-upright orientation with the header along X; the coordinator may rotate the footprint 90 deg if the editor requires. Pin function (VSS, VDD, V0, RS, RW, E, D0-D7, A, K) is marking only. Tail below host board -2.6 default if inserted; real tail length RESEARCH_REQUIRED.
- FCO origin: center of the bbox of hole pattern (75.0 x 31.0 outer hole centers) and pins (inside it) = module PCB center (0,0). Mounting holes at (+/-37.5, +/-15.5), 2.5 PTH with 5.0 pads. Header holes 1.0 PTH, pads 1.8, pitch 2.54. Module standoff: default 0 (RESEARCH_REQUIRED; real installs use spacers or a socket); parameter standoff_mm. Body offset (0,0). Pin 1 (-19.05, +15.5).
- Dimensions M (outline H; PCB thickness, bezel, header X offset L); Geometry M; Materials/appearance M. Unresolved after the gap-fill pass (drawing numerics of Winstar/Newhaven/Vishay still not text-extractable; qeda community footprint offered a pin-1 offset that is not adopted, see family note): bezel outline, PCB thickness, header X offset, standoff, glass-stack height vs H2 8.6-8.9 callout; an 85 mm Crystalfontz variant exists. Validation: 15 x 2.54 = 38.1 < 80 (pin 16 at +19.05 inside hole bbox +/-37.5); holes 2.5 mm from each edge ((80-75)/2, (36-31)/2); view 66.0 < bezel 70.0 < 75.0; active 56.2 < view 66.
  
  
  ---
- COSMETIC_PROVISIONAL bezel_stock=0.32999999999999996: Inward bezel stock one fortieth total height, top remains13.2.
- COSMETIC_PROVISIONAL polarizer_inset=0.132: Polarizer recessed one hundredth total height below bezel.
- COSMETIC_PROVISIONAL pcb_color=#2F4F3A: Section7 FR4 color is variable; borrow supplied BGA substrate green / supplied plastic blue hue, keeping FR4 roughness0.5. Appearance default only.
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=2.4: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-092 — source partial

- overall_height: 4.1 (MFR_DATASHEET/L)
- pcb_thickness: 1.0 (UNCERTAIN/L)
- hole_diameter: 2.8 (UNCERTAIN/L)
- OHMNI default module: PCB 27.0 x 27.0 (Ozdisan-hosted sheet: "27.0MM * 27.0MM * 4.1MM"), panel 26.70 x 19.26 x 1.85, active area 21.74 x 11.2, pixel 0.15 x 0.15, total thickness 4.1 (all S4, vendor not identified; M/L). PCB thickness 1.0 (UNCERTAIN). Header: 4 pins 2.54 pitch (7.62 span), row at Y = -12.0 (qeda, S5, L). Holes: dia 2.8 at (+/-10.25 or +/-11.15, +/-11.5) per the qeda library (its file says set 2 was measured on a real module; UNCERTAIN, RESEARCH_REQUIRED). Conflicts: PCB 26 (Waveshare) / 27 / 30 (DFRobot); active height 10.864 (DFRobot) / 11.18 (Waveshare) / 11.2; hole dia 2.0 (DFRobot) / 2.8 (qeda).
- Sub-bodies: PCB 27.0 x 27.0 x 1.0 with 4 corner holes; OLED panel 26.70 x 19.26 x 1.85 glass (black when off) on a spacer/tape 1.25 high (DERIVED so total = 1.0 + 1.25 + 1.85 = 4.1), panel centered in X and flush to the PCB top edge (UNCERTAIN offset), active-area rectangle 21.74 x 11.2 centered on the panel as a decal; flex-tail fold ignored. Header: black plastic housing 10.16 x 2.54 x 2.5 on the underside, 4 pins at 2.54 pitch.
- 4 round pins 0.64 (UNCERTAIN) on pitch 2.54 along X at Y = -12.0, X = -3.81, -1.27, +1.27, +3.81 relative to the module center. Pin 1 at (-3.81, -12.0) (the single-row header rule says along Y, but the module is kept display-upright with the header along X; DEVIATION recorded). Pin order commonly GND/VCC/SCL/SDA but VCC/GND swaps exist (DFRobot: VCC, GND, SCL, SDA, D/C, CS); RESEARCH_REQUIRED per module. Tail 2.6 below host board top; housing underside at Z = standoff.
- Dimensions L-M (PCB size/panel M; holes, header offset, thickness L); Geometry M; Materials/appearance M. Unresolved after gap-fill (no Adafruit/Waveshare/Midas vendor drawing numerics extractable; Adafruit text gives PCB 29.2 x 26.7, hole spacing 24 mm, total 6.2 for its own board only): hole positions, header Y offset, panel Y offset, PCB thickness, pin order per vendor. A cited vendor drawing for the 27 mm default module is still missing. Validation: 4 pins x 2.54 = 7.62 span < 27; panel 26.70 < 27.0 PCB; stack 1.0 + 1.25 + 1.85 = 4.1 total (DERIVED to match sheet); active 21.74 < panel 26.70.
  
  
  ---
- COSMETIC_PROVISIONAL pcb_color=#1E5AA8: Section7 FR4 color is variable; borrow supplied BGA substrate green / supplied plastic blue hue, keeping FR4 roughness0.5. Appearance default only.
- COSMETIC_PROVISIONAL pad_stock=0.15: Visual metal stock no more than 5 percent height or0.15; contact planes unchanged.
- COSMETIC_PROVISIONAL mark_diameter=1.8: Optional pin1 dot one fifteenth smaller body dimension, within face.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-093 — source partial

- standoff: 0 mm (UNCERTAIN/L)
- Lead row/body offset, dome radius and cosmetic top bevel are inferred. Kinked/formed lead geometry is not sufficiently sourced and is not enabled.

### OHM-095 — source partial

- standoff: 0.05 mm (UNCERTAIN/L)
- Body chamfer/radii and lead/tab exit height are cosmetic defaults; SOT89 center-lead width assignment remains uncertain.

### OHM-096 — source complete

- Body chamfer/radii and lead exit height are cosmetic defaults.

### OHM-097 — source partial

- hole_center_from_top: 3.75 mm (MFR_DRAWING/L)
- plate_thickness: 1.2 mm (MFR_DRAWING/L)
- Hole position, plate/plastic split, tab contour and lead shoulder details are inferred; tab holes are body features excluded from FCO.
- Shoulder length 1.0 mm is an unsourced visual default (width 1.32 from entry); optional chamfers omitted.

### OHM-098 — source partial

- hole_center_below_tab_top: 3.2 mm (DERIVED/L)
- standoff: 0 mm (UNCERTAIN/L)
- Hole position, plate/plastic split, tab contour and lead shoulder details are inferred; tab holes are body features excluded from FCO.

### OHM-099 — source partial

- hole_center_below_tab_top: 6.17 mm (MFR_DRAWING/L)
- tab_thickness: 2.0 mm (MFR_DRAWING/L)
- Hole position, plate/plastic split, tab contour and lead shoulder details are inferred; tab holes are body features excluded from FCO.
- TO247 dish depth 0.5 mm is cosmetic; plastic top 2.6 below tab top and exposed back start 4.4 are provisional.

### OHM-100 — source partial

- tab_extension: 1.08 mm (MFR_DRAWING/L)
- stub_length: 0 mm (MFR_DRAWING/L)
- Tab extension/symbol assignment, unsourced taper and cropped-lead stub remain uncertain. Tab is embedded at Z=0, not stacked beneath the plastic.
- Exposed underside uses the family minimum thermal contour centered under plastic; its exact contour placement is an OHMNI visual default. Hidden internal tab metal is omitted.

### OHM-101 — source partial

- tab_extension: 1.5 mm (DERIVED/L)
- Tab extension/symbol assignment, unsourced taper and cropped-lead stub remain uncertain. Tab is embedded at Z=0, not stacked beneath the plastic.
- Exposed underside uses the family minimum thermal contour centered under plastic; its exact contour placement is an OHMNI visual default. Hidden internal tab metal is omitted.

### OHM-102 — source partial

- standoff: 0.05 mm (UNCERTAIN/L)
- A1 standoff extraction remains scrambled; unmapped end frame and dual-pad outline omitted.

### OHM-108 — source complete

- overall_length: 37.4 mm (UNCERTAIN/L)
- Wide DIP length/width defaults are derived midpoints, not manufacturer nominal values.

### OHM-109 — source complete

- overall_length: 51.75 mm (UNCERTAIN/L)
- Wide DIP length/width defaults are derived midpoints, not manufacturer nominal values.

### OHM-119 — source complete

- body_thickness 0.85 mm is RESEARCH_REQUIRED in the family and entry narrative; overall 0.95 = 0.10 + 0.85.

### OHM-122 — source complete

- lead_thickness: 0.15 mm (UNCERTAIN/L)
- Pin-1 dimple size/position and bend radii are cosmetic, not sourced manufacturer features.

### OHM-123 — source complete

- lead_thickness: 0.15 mm (UNCERTAIN/L)
- Pin-1 dimple size/position and bend radii are cosmetic, not sourced manufacturer features.

### OHM-124 — source complete

- lead_thickness: 0.15 mm (UNCERTAIN/L)
- Pin-1 dimple size/position and bend radii are cosmetic, not sourced manufacturer features.

### OHM-125 — source complete

- lead_thickness: 0.15 mm (UNCERTAIN/L)
- Pin-1 dimple size/position and bend radii are cosmetic, not sourced manufacturer features.

### OHM-126 — source complete

- lead_thickness: 0.15 mm (UNCERTAIN/L)
- Pin-1 dimple size/position and bend radii are cosmetic, not sourced manufacturer features.

### OHM-134 — source partial

- Terminal size 0.40 x 0.20 mm versus 0.32 x 0.18 in another extraction of TI DSG0008A.
- EP 0.90 x 1.60 mm is one option; onsemi alternative 0.80 x 1.20.

### OHM-135 — source partial

- standoff: 0.64 mm (MFR_DRAWING/L)
- lead_thickness: 0.2 mm (UNCERTAIN/L)
- pin1_mode center_top rests on a secondary engineering reference, not a legible primary numbering diagram.
- Pin-1 bevel 1.0 x 1.0 mm and dimple size are UNCERTAIN cosmetic defaults.
- Contact apex radial 5.775 mm is derived from an assumed 0.45 mm curl radius.

### OHM-136 — source complete

- Ball diameter 0.46 mm is the first-pass NXP 0.41-0.51 value; not reverified in the second pass.

### OHM-139 — source partial

- Array offset [0,0] assumes centering on the 1.50 x 1.28 die (RESEARCH_REQUIRED).
- Ball diameter 0.24 mm is borrowed from other vendors' 0.4-pitch WLCSP drawings.

### OHM-141 — source complete

- Can length (X) 10.8 max, width (Y) 4.65 max, height above seating plane 13.5 max (13.46 in Crystek; 13.5 endrich HC-49/U sheet; Pletronics lists 13.21: kept 13.5, conflict recorded in PKG-XTAL_HC49). Lead pitch 4.88 +/-0.2, lead dia 0.43 (+0.05/-0.03), lead length 12.7 min as supplied (OHMNI models a trimmed tail). Superseded first-pass values: length 11.05 (no HC-49/U source), pitch/dia/height 'RESEARCH_REQUIRED, uncited' (now sourced). Basis MFR_DATASHEET (S3/S4 listed in the family); confidence M (drawing label mapping partly ambiguous in text extraction; three documents agree on 13.5/13.46, 4.88, 0.43).
- Oval ("stadium") metal can: rectangle 10.8 x 4.65 with full-radius ends (r = 2.325, UNCERTAIN), height 13.5, flat top (slight crimped seam along the top center line at LOD2). Bottom seal plate at Z = standoff with two glass-bead/solder seals at the lead exits. Two round leads exit the bottom at X = -2.44 and +2.44 on the long axis, dia 0.43. Optional black plastic insulating pad/sleeve (not default).
- Through-hole, drill 0.8-1.0 (OHMNI default 0.9, UNCERTAIN), pads 1.6; body centered on the hole pair: body_offset (0,0); standoff 0 (UNCERTAIN; a seated can may sit 0-1 above the board); pin 1 at (-2.44, 0). Lying-flat mounting is a board-side variant (not modeled).
- Dimensions M; Geometry M; Materials/appearance M. Remaining minor gaps (not key dimensions): can end radius (assumed full radius), standoff, drill size, sleeve. Validation: height 13.5 agrees across endrich (13.5 max) and Crystek (0.530 in = 13.46); pitch 4.88 agrees across endrich, Pletronics, Crystek, SaRonix; lead dia 0.43 agrees across endrich and Pletronics (Crystek 0.48, SaRonix 0.46 max noted); leads +/-2.44 fit inside 10.8 length with 2.96 margin each side; width 4.65 > lead dia. Contradiction kept: first-pass 11.05 length vs 10.8 sourced; adopted 10.8 because it appears in two HC-49/U sheets; 11.05 is retained for the /S member (SaRonix 49S max 11.18).
  
  
  ---
- COSMETIC_PROVISIONAL radius=2.325: HC49 full-radius ends from half width; resonator 0.8 top radius stated in entry.
- COSMETIC_PROVISIONAL seal_diameter=1.29: Three times stated lead diameter, inside bottom plate.
- COSMETIC_PROVISIONAL seam_width=0.09300000000000001: One fiftieth of can width; surface seam inside top envelope.
- COSMETIC_PROVISIONAL label_width=5.940000000000001: 55 percent of sourced body length; optional identity decal.
- COSMETIC_PROVISIONAL label_height=0.93: One fifth of smaller face dimension.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-142 — source complete

- Oval ("stadium") metal can: rectangle 11.05 x 4.65 with full-radius ends (r = 2.325, UNCERTAIN), height 3.5 (max), flat top (slight crimped seam along the top center line at LOD2). Bottom seal plate at Z = standoff with two glass-bead/solder seals at the lead exits. Two round leads exit the bottom at X = -2.44 and +2.44 on the long axis, dia 0.43. Optional black plastic insulating pad/sleeve (not default).
- Through-hole, drill 0.8-1.0 (OHMNI default 0.9, UNCERTAIN), pads 1.6; body centered on the hole pair: body_offset (0,0); standoff 0 (UNCERTAIN; a seated can may sit 0-1 above the board); pin 1 at (-2.44, 0). Lying-flat mounting is a board-side variant (not modeled).
- Dimensions M; Geometry M; Materials/appearance M. Remaining minor gaps (not key dimensions): can end radius, standoff, drill. Validation: height 3.5 agrees between SaRonix 49S and Abracon ABL; pitch 4.88 agrees across four documents; leads +/-2.44 fit inside 11.05 with 3.1 margin; first-pass 11.05 x 4.65 sits within SaRonix maxima 11.18 x 4.65 and Abracon 11.5 x 5.0 (kept as default, no contradiction). OHM-142 length differs from OHM-141 (10.8) by sourced vendor data.
  
  
  ---
- COSMETIC_PROVISIONAL radius=2.325: HC49 full-radius ends from half width; resonator 0.8 top radius stated in entry.
- COSMETIC_PROVISIONAL seal_diameter=1.29: Three times stated lead diameter, inside bottom plate.
- COSMETIC_PROVISIONAL seam_width=0.09300000000000001: One fiftieth of can width; surface seam inside top envelope.
- COSMETIC_PROVISIONAL label_width=6.077500000000001: 55 percent of sourced body length; optional identity decal.
- COSMETIC_PROVISIONAL label_height=0.7: One fifth of smaller face dimension.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-143 — source partial

- terminal_width: 1.0 (DERIVED/L)
- terminal_length: 0.9 (DERIVED/L)
- Restated from PKG-XTAL_SMD: length (X) 3.2, width (Y) 2.5, height default 0.8, max 1.0 (NDK NX3225GD: 0.80 typ, max 1.0; Abracon ABM8G 1.0 max; Epson FA-238 0.7 and TSX-3225 0.6 are thinner vendor variants). Tolerance L/W +/-0.1 (NDK). Pads (OHMNI default, DERIVED/UNCERTAIN; real values RESEARCH_REQUIRED): 1.0 (X) x 0.9 (Y), centers X +/-1.1, Y +/-0.8. Basis MFR_DATASHEET for L/W/H max; confidence M for L/W/H, L for pads.
- Ceramic base box 3.2 x 2.5 x ~0.56 (about 70 percent of height, DERIVED) topped by a metal lid 3.0 x 2.3 x ~0.24 (lid inset 0.1 per side, DERIVED, UNCERTAIN) that sits on the ceramic ring. Four metallized pads wrap the bottom corners and appear as small notches or wraparound strips on the side faces (castellation optional at LOD2). Lid has a small chamfer or corner mark; the part-number print reads left to right with pin 1 at the upper-left corner (NDK/Epson; Abracon prints pin 1 at lower-left).
- Dimensions M (L/W/H) / L (pads); Geometry M; Materials/appearance M. Unresolved: pad sizes and exact land pattern (no 3225 drawing text extracted with usable labels), lid inset, 2-pad variant dims, numbering direction. Contradiction kept: first-pass pin 1 bottom-left (Abracon) vs adopted top-left (NDK, Epson). Validation: pad edge = 1.1+1.0/2 = 1.6 <= 1.6; 0.8+0.9/2 = 1.25 <= 1.25; pin 1 now follows NDK/Epson and Addendum 17.2 (top-left); Abracon ABM8G bottom-left kept as a variant.
  
  
  ---
- COSMETIC_PROVISIONAL pad_thickness=0.02: Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged.
- COSMETIC_PROVISIONAL base_fraction=0.7: Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope.
- COSMETIC_PROVISIONAL lid_inset=0.1: Entry lid inset; SAW borrows oscillator seam inset.
- COSMETIC_PROVISIONAL marker_radius=0.1: One twenty-fifth of smaller body dimension; lid corner mark only.
- COSMETIC_PROVISIONAL lid_chamfer=0.25: One tenth of smaller dimension, removes material at marked corner only.
- COSMETIC_PROVISIONAL label_width=1.6: Half of body length, inside lid.
- COSMETIC_PROVISIONAL label_height=0.5: One fifth of body width, inside lid.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-144 — source partial

- terminal_width: 0.8 (DERIVED/L)
- terminal_length: 0.7 (DERIVED/L)
- Restated from PKG-XTAL_SMD: length (X) 2.5, width (Y) 2.0, height default 0.5, max 0.6 (NDK NX2520SA 0.50 +/-0.05; Abracon ABM10W 0.6 max). Tolerance L/W +/-0.1 (NDK). Pads (OHMNI default, DERIVED/UNCERTAIN; real values RESEARCH_REQUIRED): 0.8 (X) x 0.7 (Y), centers X +/-0.85, Y +/-0.65. Basis MFR_DATASHEET for L/W/H max; confidence M for L/W/H, L for pads.
- Ceramic base box 2.5 x 2.0 x ~0.35 (about 70 percent of height, DERIVED) topped by a metal lid 2.3 x 1.8 x ~0.15 (lid inset 0.1 per side, DERIVED, UNCERTAIN) that sits on the ceramic ring. Four metallized pads wrap the bottom corners and appear as small notches or wraparound strips on the side faces (castellation optional at LOD2). Lid has a small chamfer or corner mark; the part-number print reads left to right with pin 1 at the upper-left corner (NDK/Epson; Abracon prints pin 1 at lower-left).
- Dimensions M (L/W/H) / L (pads); Geometry M; Materials/appearance M. Unresolved: pad sizes and exact land pattern (NDK NX2520SA land numbers extracted as '0.8 x 1.7 / 0.65 / 1.3' without a usable label map), lid inset, 2-pad variant dims, numbering direction. Contradiction kept: first-pass pin 1 bottom-left (Abracon) vs adopted top-left (NDK NX2520SA). Validation: pad edge = 0.85+0.8/2 = 1.25 <= 1.25; 0.65+0.7/2 = 1.0 <= 1.0; pin 1 now follows NDK/Epson and Addendum 17.2 (top-left); Abracon ABM8G bottom-left kept as a variant.
  
  
  ---
- COSMETIC_PROVISIONAL pad_thickness=0.02: Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged.
- COSMETIC_PROVISIONAL base_fraction=0.7: Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope.
- COSMETIC_PROVISIONAL lid_inset=0.1: Entry lid inset; SAW borrows oscillator seam inset.
- COSMETIC_PROVISIONAL marker_radius=0.08: One twenty-fifth of smaller body dimension; lid corner mark only.
- COSMETIC_PROVISIONAL lid_chamfer=0.2: One tenth of smaller dimension, removes material at marked corner only.
- COSMETIC_PROVISIONAL label_width=1.25: Half of body length, inside lid.
- COSMETIC_PROVISIONAL label_height=0.4: One fifth of body width, inside lid.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-145 — source partial

- Ceramic base box 2.0 x 1.6 x ~0.28 (about 70 percent of height, DERIVED) topped by a metal lid 1.8 x 1.4 x ~0.12 (lid inset 0.1 per side, DERIVED, UNCERTAIN) that sits on the ceramic ring. Four metallized pads wrap the bottom corners and appear as small notches or wraparound strips on the side faces (castellation optional at LOD2). Lid has a small chamfer or corner mark; the part-number print reads left to right with pin 1 at the upper-left corner (NDK/Epson; Abracon prints pin 1 at lower-left).
- Dimensions M (L/W/H; pads M-/L: single NDK datasheet, consistent with the body size but no second document); Geometry M; Materials/appearance M. Unresolved: lid inset, 2-pad variant dims, numbering direction, second-source pad check (Abracon ABM11W land pattern not extractable). Contradiction kept: first-pass pin 1 bottom-left (Abracon) vs adopted top-left (NDK NX2016SA, text only). Validation: NDK land pitch 1.35 + pad 0.65 = 2.0 = body L and 1.05 + 0.55 = 1.6 = body W; pad edge = 0.675+0.65/2 = 1.0 <= 1.0; 0.525+0.55/2 = 0.8 <= 0.8; pin 1 now follows NDK/Epson and Addendum 17.2 (top-left); Abracon ABM8G bottom-left kept as a variant.
  
  
  ---
- COSMETIC_PROVISIONAL pad_thickness=0.02: Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged.
- COSMETIC_PROVISIONAL base_fraction=0.7: Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope.
- COSMETIC_PROVISIONAL lid_inset=0.1: Entry lid inset; SAW borrows oscillator seam inset.
- COSMETIC_PROVISIONAL marker_radius=0.064: One twenty-fifth of smaller body dimension; lid corner mark only.
- COSMETIC_PROVISIONAL lid_chamfer=0.16: One tenth of smaller dimension, removes material at marked corner only.
- COSMETIC_PROVISIONAL label_width=1.0: Half of body length, inside lid.
- COSMETIC_PROVISIONAL label_height=0.32: One fifth of body width, inside lid.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-146 — source partial

- terminal_width: 1.4 (DERIVED/L)
- terminal_length: 1.2 (DERIVED/L)
- 7.0 x 5.0 mm (Abracon ASV "7.0 x 5.08 x 1.8" as printed, AST3TQ 7.0 x 5.0 x 1.9 with L 7.1 +/-0.2, W 5.0 +/-0.2, H 1.9 +/-0.2; SiTime SiT8008B 7.0 x 5.0 x 0.90). Conflict: width 5.0 vs 5.08 (ASV). Default L 7.0, W 5.0, H 1.8 (ASV ceramic; min 0.9 MEMS, max 1.9). Pad centers 5.08 x 3.81 (SiTime; Abracon AST3TQ land E 5.08, M 3.90). Pad size 1.4 x 1.2 DERIVED/UNCERTAIN (SiTime land pattern lists 2.2 and 2.0 but the mapping is ambiguous in the text extraction). Basis MFR_DATASHEET; confidence M for L/W/H, L for pads.
- Ceramic base box 7.0 x 5.0 x ~1.17 with a metal lid 6.7 x 4.7 x ~0.63 (inset 0.15, DERIVED, UNCERTAIN) and four corner pads wrapping the underside; a lid-corner chamfer or print dot at pin 1. Package is plain rectangular (no rounded corners at LOD1).
- 4 flat pads 1.4 x 1.2 (UNCERTAIN) at pad centers 1 = (-2.54, 1.905), 2 = (-2.54, -1.905), 3 = (2.54, -1.905), 4 = (2.54, 1.905) per Addendum 17.2 (pin 1 top-left, counter-clockwise). Functions: 1 = OE/tri-state/NC, 2 = GND (case), 3 = OUT, 4 = VDD (Abracon ASV, AST3TQ, ASTX-H11; SiTime SiT8008). Material MAT_GOLD.
- Pin 1 dot or chamfer at the top-left corner (-X,+Y); no official corner marking is stated in the opened Abracon/SiTime texts (RESEARCH_REQUIRED). Delta vs Abracon crystals (pin 1 bottom-left) recorded.
- Dimensions M (outline) / L (pads); Geometry M; Materials/appearance M. Unresolved (gap-fill search for a second 7050 source, e.g. Epson SG-8002/SG7050, found only distributor listings, not opened): pad dimensions and pad-to-edge relations, pin-1 corner convention (not stated), lid inset, height variation 0.9-1.9 (still single-vendor values: Abracon ASV 1.8 as printed, AST3TQ 1.9 +/- 0.2, SiTime 0.90). Validation: 2.54 + 0.7 = 3.24 < 3.5 half-length; 1.905 + 0.6 = 2.505 = half-width 2.5 (flush, acceptable); pin function order identical across three vendors.
  
  
  ---
- COSMETIC_PROVISIONAL pad_thickness=0.02: Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged.
- COSMETIC_PROVISIONAL base_fraction=0.65: Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope.
- COSMETIC_PROVISIONAL lid_inset=0.15: Entry lid inset; SAW borrows oscillator seam inset.
- COSMETIC_PROVISIONAL marker_radius=0.2: One twenty-fifth of smaller body dimension; lid corner mark only.
- COSMETIC_PROVISIONAL lid_chamfer=0.5: One tenth of smaller dimension, removes material at marked corner only.
- COSMETIC_PROVISIONAL label_width=3.5: Half of body length, inside lid.
- COSMETIC_PROVISIONAL label_height=1.0: One fifth of body width, inside lid.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-147 — source partial

- terminal_width: 1.0 (DERIVED/L)
- terminal_length: 0.9 (DERIVED/L)
- Default 3.2 x 2.5 x 0.9 (Epson TG3225CEN TCXO: 3.2 +/-0.2 x 2.5 +/-0.2 x 0.9 +/-0.1; first-pass 1.0 from Abracon ASTX-H11 retained as the max, ASTX-H11 not established as a TCXO; SiTime SiT8008 3225 is 0.75; smaller Epson TG2520CEN 2.5 x 2.0 x 0.8 +/-0.1 and TG2016SMN 2.0 x 1.6 x 0.73 exist). Alternative TCXO member 7050: 7.0 x 5.0 x 1.9 (Abracon AST3TQ, pad pitch F 1.27, land E 5.08 / M 3.90 / N 5.08). Pads for 3225: 1.0 x 0.9 at +/-1.1, +/-0.8 (DERIVED/UNCERTAIN). Basis MFR_DATASHEET (outline) / DERIVED (pads). Confidence M for the 3225 outline (Epson TG3225CEN; two hosted copies of one datasheet, plus Abracon ASTX-H11 as an independent 3.2 x 2.5 outline) and for the 7050 TCXO, L for pads.
- Ceramic base box 3.2 x 2.5 x ~0.65 with a metal lid 2.9 x 2.2 x ~0.35 (inset 0.15, DERIVED, UNCERTAIN) and four corner pads wrapping the underside; a lid-corner chamfer or print dot at pin 1. Package is plain rectangular (no rounded corners at LOD1).
- 4 flat pads 1.0 x 0.9 (UNCERTAIN) at pad centers 1 = (-1.1, 0.8), 2 = (-1.1, -0.8), 3 = (1.1, -0.8), 4 = (1.1, 0.8) per Addendum 17.2 (pin 1 top-left, counter-clockwise). Functions: 1 = OE/tri-state/NC, 2 = GND (case), 3 = OUT, 4 = VDD (Abracon ASV, AST3TQ, ASTX-H11; SiTime SiT8008). Material MAT_GOLD.
- SMD pads; body centered on the pad pattern, body_offset (0,0); standoff 0. Pin 1 at (-1.1, 0.8). Pad centers from the crystal-class rule (see PKG-XTAL_SMD); oscillator-specific land pattern RESEARCH_REQUIRED.
- Pin 1 dot or chamfer at the top-left corner (-X,+Y); no official corner marking is stated in the opened Abracon/SiTime texts (RESEARCH_REQUIRED). Delta vs Abracon crystals (pin 1 bottom-left) recorded.
- Dimensions M (outline/height of 3225 and 7050); L (pads); Geometry M; Materials/appearance M. RESEARCH_REQUIRED: pad sizes/land pattern (Epson footprint letters A-D not mapped in extraction), pin-1 corner, lid material. Gap-fill closed: true 3225 TCXO datasheet found (Epson TG3225CEN). Contradiction kept: first-pass height 1.0 vs Epson 0.9 +/-0.1 (adopted 0.9; 1.0 stays the max). Validation: pad edge 1.1 + 0.5 = 1.6 = half-length; 0.8 + 0.45 = 1.25 = half-width; pin function order matches AST3TQ.
- Dimensions M (outline/height of 3225 and 7050); L (pads); Geometry M; Materials/appearance M. RESEARCH_REQUIRED: pad sizes/land pattern (Epson footprint letters A-D not mapped in extraction), pin-1 corner, lid material. Gap-fill closed: true 3225 TCXO datasheet found (Epson TG3225CEN). Contradiction kept: first-pass height 1.0 vs Epson 0.9 +/-0.1 (adopted 0.9; 1.0 stays the max). Validation: pad edge 1.1 + 0.5 = 1.6 = half-length; 0.8 + 0.45 = 1.25 = half-width; pin function order matches AST3TQ.
  
  
  ---
- COSMETIC_PROVISIONAL pad_thickness=0.02: Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged.
- COSMETIC_PROVISIONAL base_fraction=0.65: Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope.
- COSMETIC_PROVISIONAL lid_inset=0.15: Entry lid inset; SAW borrows oscillator seam inset.
- COSMETIC_PROVISIONAL marker_radius=0.1: One twenty-fifth of smaller body dimension; lid corner mark only.
- COSMETIC_PROVISIONAL lid_chamfer=0.25: One tenth of smaller dimension, removes material at marked corner only.
- COSMETIC_PROVISIONAL label_width=1.6: Half of body length, inside lid.
- COSMETIC_PROVISIONAL label_height=0.5: One fifth of body width, inside lid.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-148 — source complete

- Rounded-top resin block 8.0 (X) x 3.5 (Y) wide, 5.5 tall (corner radius ~0.8 on top, UNCERTAIN), flat bottom, with a thin print area on the large face. Three round leads emerge from the bottom at X = -2.5, 0, +2.5 on the Y=0 line.
- Through-hole, 3 holes in a row, pitch 2.5, drill ~0.8 (UNCERTAIN); body_offset (0,0); standoff 0 (UNCERTAIN).
- Dimensions M; Geometry M; Materials/appearance L. Unresolved (not key): body color (blue unverified), exact lead length, top radius, drill. Validation: 2 x 2.5 + 3 = 8.0 equals the body length (fits with pitch 2.5 +/-0.2); Murata L/height match the RS listings for both G and X members; T 3.5 vs RS 3 within tolerance. Contradiction kept: first-pass T 3.0 / lead dia 0.5 / pitch 'unresolved' replaced by Murata 3.5 / 0.48 / 2.5.
  
  
  ---
- COSMETIC_PROVISIONAL radius=0.8: HC49 full-radius ends from half width; resonator 0.8 top radius stated in entry.
- COSMETIC_PROVISIONAL seal_diameter=1.44: Three times stated lead diameter, inside bottom plate.
- COSMETIC_PROVISIONAL seam_width=0.07: One fiftieth of can width; surface seam inside top envelope.
- COSMETIC_PROVISIONAL label_width=4.4: 55 percent of sourced body length; optional identity decal.
- COSMETIC_PROVISIONAL label_height=0.7: One fifth of smaller face dimension.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-149 — source partial

- - Physical package: PKG-SAW_SMD member 3838 (Abracon AFS869S3 class, 3.8 x 3.8 mm; 3030 placeholder and 1109 Murata variants in the family)
- - Aliases: SAW filter, IF/RF SAW. Variants: 3.8x3.8 (default), 3x3 placeholder, 5x5, 1109; 4 to 8 pads.
- - Class A, priority P3, complexity 2. STATUS partial (gap-fill: outline of one real part sourced; pads still placeholders).
- 3.8 x 3.8 x 1.5 (Abracon AFS869S3, S4, no tolerance stated; M-/L single source); first-pass placeholders 3.0 x 3.0 x 1.2 and 5.0 x 5.0 x 1.3 retained as unsourced alternates. Pads (placeholder): 0.8 x 0.6 on 1.1 pitch, rows at X +/-1.5. RESEARCH_REQUIRED: pad size, pitch, height tolerance, lid type (no Murata/TDK/Qorvo 3 mm or 5 mm drawing opened).
- 6 flat pads (placeholder): dual-row rule, rows parallel to Y at X = +/-1.5, Y = +1.1, 0, -1.1; pin 1 at (-1.5, +1.1), pins 1-3 down the -X row, 4-6 up the +X row (pin 4 at (+1.5, -1.1)). Pad 0.8 x 0.6, MAT_GOLD (DERIVED placeholders). Functions per Abracon AFS869S3: pin 2 input, pin 5 output (the two center pads), pins 1, 3, 4, 6 ground; the 6-pin count is inferred (RESEARCH_REQUIRED).
- Dimensions M for the 3.8 x 3.8 x 1.5 outline (single Abracon sheet, no tolerance; SAW sizes are not standardized, so no cross-check); Geometry L (pads placeholders); Materials/appearance L. RESEARCH_REQUIRED: pad size/pitch, pad count confirmation, lid type, a TDK/Qorvo/Murata 3x3 or 5x5 drawing. Validation: 3 pads at 1.1 pitch span 2.2 < 3.8; pad extents 1.5 + 0.4 = 1.9 = half-length (flush). Contradiction kept: brief's 3.0 x 3.0 / 5.0 x 5.0 'de facto' sizes are unsourced; the one sourced ISM SAW part is 3.8 x 3.8.
- Dimensions M for the 3.8 x 3.8 x 1.5 outline (single Abracon sheet, no tolerance; SAW sizes are not standardized, so no cross-check); Geometry L (pads placeholders); Materials/appearance L. RESEARCH_REQUIRED: pad size/pitch, pad count confirmation, lid type, a TDK/Qorvo/Murata 3x3 or 5x5 drawing. Validation: 3 pads at 1.1 pitch span 2.2 < 3.8; pad extents 1.5 + 0.4 = 1.9 = half-length (flush). Contradiction kept: brief's 3.0 x 3.0 / 5.0 x 5.0 'de facto' sizes are unsourced; the one sourced ISM SAW part is 3.8 x 3.8.
  
  
  ---
- COSMETIC_PROVISIONAL pad_thickness=0.02: Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged.
- COSMETIC_PROVISIONAL base_fraction=0.65: Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope.
- COSMETIC_PROVISIONAL lid_inset=0.15: Entry lid inset; SAW borrows oscillator seam inset.
- COSMETIC_PROVISIONAL marker_radius=0.152: One twenty-fifth of smaller body dimension; lid corner mark only.
- COSMETIC_PROVISIONAL lid_chamfer=0.38: One tenth of smaller dimension, removes material at marked corner only.
- COSMETIC_PROVISIONAL label_width=1.9: Half of body length, inside lid.
- COSMETIC_PROVISIONAL label_height=0.76: One fifth of body width, inside lid.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-150 — source complete

- - Common variants: pins per row N = 1..40; tail/mating length options; gold or tin plating; 2.0 mm and 1.27 mm pitch (RESEARCH_REQUIRED, not sourced)
- - Optional LOD2 detail (unsourced common practice): shallow V-notch break grooves across the top face at the boundaries between positions; 0.2 mm base top-edge chamfer; slight draft on base sides is not modeled.
- - Coupled: base length = N x pitch; total pin = pin_above + base_height + tail_below; if pitch changes, other dims are RESEARCH_REQUIRED.
- - Dimensions M / Geometry M / Materials-appearance M.
  - Gap-fill: base width resolved at M (Harwin M20-9990245 1x2 overall 5.08 x 2.54 x 11.64; Harwin pin 6.1/total 11.64 vs Wurth 6.0/11.54 noted). Status stays complete.
  - Unresolved (cosmetic): grooves/chamfer size, pyramid tip size, 2.0 mm and 1.27 mm pitch variants, Amphenol/FCI drawings not opened.
  - Validation: 6.0 + 2.54 + 3.0 = 11.54 matches WE-PHD-PIN total; 2 x 2.54 = 5.08 matches L; yaml pin1 y = (N-1)/2 x 2.54 = 8.89 for N=8; Samtec .025 in = 0.635 agrees with 0.64; Harwin 2.54 + 6.1 + 3.0 = 11.64 matches its 11.64 overall.
  
  ---
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-151 — source complete

- - Common variants: pins per row N = 1..40; tail/mating length options; gold or tin plating; 2.0 mm and 1.27 mm pitch (RESEARCH_REQUIRED, not sourced)
- - Optional LOD2 detail (unsourced common practice): shallow V-notch break grooves across the top face at the boundaries between positions; 0.2 mm base top-edge chamfer; slight draft on base sides is not modeled.
- - Coupled: base length = N x pitch; total pin = pin_above + base_height + tail_below; if pitch changes, other dims are RESEARCH_REQUIRED.
- - Dimensions M / Geometry M / Materials-appearance M.
  - Gap-fill: 1-row base width verified (Harwin M20-9990245: 2.54); 2-row width 5.08 is derived from it (M). Status stays complete.
  - Unresolved (cosmetic): grooves/chamfer size, pyramid tip size, 2.0 mm and 1.27 mm pitch variants, Amphenol/FCI drawings not opened.
  - Validation: 6.0 + 2.54 + 3.0 = 11.54 matches WE-PHD-PIN total; 2 x 2.54 = 5.08 matches L; yaml pin1 y = (N-1)/2 x 2.54 = 5.08 for N=5; Samtec .025 in = 0.635 agrees with 0.64.
  
  ---
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-152 — source complete

- - Common variants: N = 1..40, tail length 2.29 to 7.87 (Samtec), low-profile sockets (not sourced), right-angle (not specified)
- - Break grooves between positions optional at LOD2 (unsourced).
- - Count: 8 contacts (N); tails 0.64 square (UNCERTAIN), gold or tin.
- - Dimensions M / Geometry M / Materials-appearance M.
  - Gap-fill resolved: width conflict (Samtec .100 and Harwin 2.50 agree; Wurth 3.1 treated as outlier), length end allowance 0.4 (Harwin, 2 parts) vs Wurth 0.5, tail 3.0 confirmed by Harwin.
  - Unresolved: 2-row width (4.95 vs 5.08), opening size and chamfer.
  - Validation: pitch and pin-1 checked against the architecture rules; body height three-source agreement (Samtec 8.51, Wurth 8.5, Harwin 8.5); Harwin lengths 8.02 and 51.20 both fit N x 2.54 + 0.40; hole 1.02 consistent with 0.64 tail.
  
  ---
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-153 — source complete

- body_width: 5.08 (UNCERTAIN/L)
- - Common variants: N = 1..40, tail length 2.29 to 7.87 (Samtec), low-profile sockets (not sourced), right-angle (not specified)
- - Break grooves between positions optional at LOD2 (unsourced).
- - Count: 10 contacts (2N); tails 0.64 square (UNCERTAIN), gold or tin.
- - Dimensions M / Geometry M / Materials-appearance M.
  - Gap-fill: length end allowance 0.4 (Harwin) added; tail 3.0 confirmed by Harwin (single-row parts).
  - Unresolved: 2-row body width (4.95 Samtec vs 5.08 nominal; no 2-row Harwin/Wurth drawing opened), opening size and chamfer.
  - Validation: pitch and pin-1 checked against the architecture rules; body height two-source agreement; hole 1.02 consistent with 0.64 tail.
  
  ---
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-154 — source partial

- base_height: 2.54 (UNCERTAIN/L)
- pin_axis_height: 1.27 (UNCERTAIN/L)
- - body height Z = rows x 2.54 (L, UNCERTAIN); horizontal pin axis Z = 1.27 + 2.54 r (L, UNCERTAIN)
- - Black base block, Y length N x 2.54, X depth 2.54, Z height rows x 2.54 (UNCERTAIN), underside at Z = 0. The body is NOT centered on the holes: its rear face is 1.5 mm in front of the nearest tail column (+X side). body_offset X = +2.77 (1xN) or +4.04 (2xN).
- - Bend: mitered elbow at LOD0/1, inner radius about 0.3 at LOD2 (UNCERTAIN, cosmetic).
- - Dimensions M / Geometry M / Materials-appearance M. status: partial.
  - Resolved in gap-fill: mating length 6.0, tail 3.0, body depth 2.54, rear offset 1.5, 2xN tail-column/row assignment, body offset (the first pass centered the body on the tail pattern, which was wrong).
  - Unresolved: body height and pin axis height above the board (assumed 2.54 per row / 1.27 per row), Samtec RA callouts, Amphenol 10129378 (no source found).
  - Validation: pin 1 y for N=8 = 3.5 x 2.54 = 8.89; 2xN body center relative to the tail-pattern center = 5.31 - 1.27 = 4.04 (KiCad 2x02: body 4.04 to 6.58, tails at 0 and 2.54, pattern center 1.27); 1xN body center 2.77 (KiCad 1x02 body 1.5 to 4.04); numbering matches KiCad with Y flipped.
  
  ---
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-155 — source partial

- wall_thickness: 0.5 (DERIVED/L)
- post_square: 0.5 (DERIVED/L)
- - Common variants: S2B-PH-K-S side entry (THT, dims RESEARCH_REQUIRED), B2B-PH-SM4-TB / S2B-PH-SM4-TB (SMT, not modeled), N = 2..16
- - Boxed rectangular shroud (open top) of natural white PA, length B along Y, depth 4.5 along X, height 6.0, Z from 0. Cavity 4.9 (Y) x 3.5 (X) for N=2, walls 0.5 on all four sides (L), cavity floor top at Z = 1.0 (UNCERTAIN).
- - Posts: 0.5 square at the pitch, from Z = -3.0 (tail, UNCERTAIN) to Z = 1.0 + 3.3 = 4.3, about 1.7 below the shroud rim.
- - Polarization details (KICAD-FP silk, L): a 1.0-wide slot in the +X long wall centered on the row; 1.3-wide slots through both end walls centered at X = -0.15; a small 0.2 x 0.5 rib inside the -X wall at the row center. JST text confirms walls on all four sides and a mark for circuit No. 1. Slot depths not known: model them at LOD2 only, 2.0 deep (UNCERTAIN).
- - Side-entry S2B-PH-K-S: same pin pattern, opening faces +X; geometry RESEARCH_REQUIRED.
- - Count N; 0.5 square posts (UNCERTAIN), tin-plated copper alloy; tail below board 3.0 default (UNCERTAIN, override in YAML).
- - RESEARCH_REQUIRED: tail length below the board, cavity floor height, slot depths, post size, S2B side-entry geometry, polarization shape confirmation from the JST drawing.
- - Dimensions M / Geometry L / Materials-appearance M. status: partial.
  - Conflict kept: JST catalog text "mounting height of 8 mm" (first-pass height 8.0) vs Lion Circuits "housing height 6". Adopted 6.0 (distributor listing, plus the 8 mm phrase most likely describes the mated assembly); S2B side-entry extraction suggested about 9.6 (not used).
  - RESEARCH_REQUIRED: tail length below the board, cavity floor height, slot depths, post size, S2B side-entry geometry, polarization shape confirmation from the JST drawing.
  - Validation: A=2.0 and B=5.9 for N=2 from source and KiCad; B formula inferred from endpoints 5.9 and 33.9; KiCad outline x from -1.95 to 3.95 is B; hole 0.7 vs 0.5 post diagonal consistent; OHMNI transform keeps pin 1 at +Y.
  
  ---
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-156 — source partial

- wall_thickness: 0.65 (DERIVED/L)
- - Common variants: N = 2..16 (UNCERTAIN upper), side entry S2B-XH-A (partly read)
- - Cavity floor top Z = 1.0 (UNCERTAIN); post tip at floor + 3.4 = 4.4 (JST-XH-DIST lists 3.4 "mating pin length", meaning not confirmed).
- - Polarization: housing marked for circuit No. 1; the KiCad silk shows the long wall on the +X side broken into three segments with 1.5-wide windows centered at the pins (L). True keying shape not confirmed. LOD2 only.
- - Count N; 0.64 square, tin-plated brass; tail 3.0 default (UNCERTAIN).
- - RESEARCH_REQUIRED: floor height, tail length, polarization shape, max N, side-entry S2B-XH-A geometry (JST extraction hints depth 4.5 and height 6.1, labels unreliable).
- - Dimensions M / Geometry L / Materials-appearance M. status: partial.
  - Conflicts: one extraction labeled 7.4 as height; 7.4 equals B for N=2, so height is 7.0. Depth 5.7 (first pass) vs 5.75 (JST second read and KiCad): 5.75 adopted.
  - RESEARCH_REQUIRED: floor height, tail length, polarization shape, max N, side-entry S2B-XH-A geometry (JST extraction hints depth 4.5 and height 6.1, labels unreliable).
  - Validation: 2.5 + 4.9 = 7.4 matches B for N=2 and the KiCad outline; pins at Y = +-1.25.
  
  ---
- COSMETIC_PROVISIONAL slot_depth=2.0: Borrow OHM-155 PH slot depth; remains inside 7 mm XH body.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-157 — source partial

- pad_length: 1.55 (CONSENSUS/L)
- tab_pad: [1.8, 1.2] (UNCERTAIN/L)
- - Common variants: BM04B-SRSS-TB top entry (dims below, L), N = 2..16 (UNCERTAIN)
- - Front cavity open on the -X face: UNCERTAIN size (default 2 mm tall slot, 4.2 wide, 3.0 deep, 0.4 floor), contacts run along the cavity floor and leave through the rear (+X) face as flat SMD tails.
- - Contact tails: flat strips 0.6 (Y) x 1.55 (X) x 0.15 thick (UNCERTAIN) at Y = +1.5, +0.5, -0.5, -1.5; pad centers X = +2.0, so the tails span X 1.225 to 2.775 and protrude 1.1 beyond the housing rear face.
- - Solder tabs (brass): footprint pads 1.8 (X) x 1.2 (Y) at X = -1.875, Y = +-2.8; the tab strap wraps the housing end face (it spans 0.4 beyond the housing end). Tab body geometry above the pad is UNCERTAIN: model a 1.2-wide, 0.2-thick strip along the housing end, 2.9 tall at LOD2 only.
- - RESEARCH_REQUIRED: front cavity dimensions, contact thickness, tab strap geometry above the pad, max N, BM04B height confirmation.
- - Dimensions M / Geometry L / Materials-appearance M. status: partial.
  - Conflicts kept: JST catalog read gives B = 4.25 (top entry) and 4.0 (side entry); KiCad and openpilot give 4.25 for the SM04B plan depth and 2.9 for the BM04B plan depth. Adopted the plan sizes from KiCad (two documents agree on 4.25 for SM). Height 2.9 (JST A, openpilot, Lion) vs 2.95 (Farnell). The earlier "A = 6.0, B = 5.0" mislabeling in one extraction is dismissed (B = 6.0 consistent across three).
  - Axis change: mating direction moved from +X to -X so that pin 1 at +Y is not a mirror image of the KiCad/JST pin-1 side (coordinator to confirm).
  - RESEARCH_REQUIRED: front cavity dimensions, contact thickness, tab strap geometry above the pad, max N, BM04B height confirmation.
  - Validation: A + 3.0 = 6.0 = B; KiCad fab outline x +-3.0; pads at 1.0 pitch symmetric about Y = 0; pad bounding box centered at X = 0 (-2.775 to +2.775).
  
  ---
- COSMETIC_PROVISIONAL end_wall=0.9: (6.0 mm default body length - 4.2 mm cavity)/2; fixed end allowance for N variants.
- COSMETIC_PROVISIONAL top_wall=0.5: Borrow OHM-155 shroud wall; within BM04B 2.9 mm depth.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-158 — source partial

- housing_length: 5.08 (DERIVED/L)
- housing_depth: 5.8 (DERIVED/L)
- overall_height: 6.0 (UNCERTAIN/L)
- - housing length N x 2.54 = 5.08 for N=2 (L, KiCad outline of sibling 22-27-2021); housing depth 5.8 (L); housing height 6.0 and post 0.64 square (UNCERTAIN placeholders, L)
- - Partially shrouded nylon housing: OHMNI X from -2.88 to +2.92, Y from -N x 1.27 to +N x 1.27, Z from 0 to 6.0 (placeholder). A ramp-side back wall on the -X side, 1.0 thick (X -2.88 to -1.99), full length and height. The long +X side is open except for one wall stub per pin (0.6 thick X 2.32 to 2.92, 1.6 wide in Y, centered on the pin).
- - Friction lock ramp (L): a block on the inside face of the back wall, protruding 0.53 (X -1.99 to -1.46), 2.54 wide at the wall tapering to 2.04 at its top, for a 2-circuit header; ramp height and vertical profile RESEARCH_REQUIRED (placeholder: wedge occupying the upper 2.0 mm of the wall). Ramp count for N > 2 not known.
- - Posts 0.64 square (UNCERTAIN) at X = 0, Y = +-1.27 (N=2); post tip placeholder Z = 9.0.
- - N brass posts, 0.64 square (UNCERTAIN), tin or gold; tail 3.56 below the board.
- - tht_holes pitch 2.54, recommended PCB 1.6 (MOLEX-38006293, Farnell); hole diameter RESEARCH_REQUIRED (KiCad footprint drill 1.19 is a footprint-layer value); FCO hole center; body_offset (0, 0) (the housing is within 0.02 of centered on the pin row).
- - Natural white or cream nylon with bright posts; some KK headers are black (not sourced).
- - Resolved: tail 3.56 vs 10.00 (different part numbers); housing length rule N x 2.54 (first-pass placeholder N x 2.54 + 0.6 withdrawn); depth 5.8; ramp and stub plan layout (L).
- - Dimensions L / Geometry L / Materials-appearance M. status: partial.
  - Resolved: tail 3.56 vs 10.00 (different part numbers); housing length rule N x 2.54 (first-pass placeholder N x 2.54 + 0.6 withdrawn); depth 5.8; ramp and stub plan layout (L).
  - Unresolved: 22-23-2021 (6373) vs 22-27-2021 (6410) envelope equivalence, housing height, ramp height/profile, post size, hole diameter, N range and ramp count.
  - Validation: pins at +-1.27 symmetric; outline x -1.27 to 3.81 = 2 x 2.54; tail four-source agreement.
  
  ---
- COSMETIC_PROVISIONAL floor=1.0: One sixth of the stated 6 mm housing height; connects walls without changing outer envelope.
- COSMETIC_PROVISIONAL end_wall=0.6: Reuse the stated open-side stub thickness for end walls, inside row envelope.
- COSMETIC_PROVISIONAL ramp_count=1: One centered ramp retained for N variants; source gives one for N=2 and no N>2 rule.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-159 — source partial

- - Per position: a screw pocket on the top face centered on the pin axis (X = 0): round, about Ø3.0 (L), with an M3 slotted screw head (slot orientation not confirmed); and a wire entry on a side face. Phoenix data: wire connection direction 0 deg (horizontal, parallel to the board). Entry face OHMNI +X (UNCERTAIN which long face). Entry window default 3.4 (Y) x 3.0 (Z) centered Z = 5.0 (UNCERTAIN, cosmetic).
- - Top profile: RESEARCH_REQUIRED (no height data for steps). Default: flat top at 13.8 with the screw pockets 1.0 deep; the first-pass "front deck 11.0" step is withdrawn as unsupported.
- - Green housing (Phoenix/most 5.08 blocks; blue for 5.0 mm alternatives not sourced), silver screws with a slot. Marking decals optional.
- - Dimensions M / Geometry L / Materials-appearance M. status: partial.
  - Resolved: wire connection direction 0 deg (horizontal), pin 0.9 x 0.9 (three documents), tail 3.5, hole 1.3, body depth 9.8 (four documents).
  - Conflict kept: 13.8 total height. PXC-MKDS-BD lists 17.3 for the same family with 3.5 solder pin, which fits 13.8 + 3.5; if the 13.8 listings include the pin, body height would be 10.3 (the lower MKDSN series is 10.0 body). 13.8 adopted, 10.3 stored as min.
  - Unresolved: which long face is the wire entry, top profile and step heights, screw head diameter and slot orientation, entry window size, 5.0 mm pitch variants, Weidmuller/Camdenboss/Kuxin not opened.
  - Validation: pitch x N length; pin spacing 5.08 between outer pins; KiCad outline x -2.54 to 7.62 = 10.16.
  
  ---
- COSMETIC_PROVISIONAL window_depth=3.266666666666667: One third of stated housing depth; internal recess only.
- COSMETIC_PROVISIONAL screw_head_height=0.5: Half the pocket depth; head stays recessed.
- COSMETIC_PROVISIONAL slot_width=0.375: One eighth of specified/placeholder 3 mm head diameter.
- COSMETIC_PROVISIONAL slot_length=2.4000000000000004: 80 percent of head diameter; slot stays inside head.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-160 — source partial

- - Per position: screw pocket on the top face centered on the pin axis (X = 0), round about Ø3.0 (L), M3 slotted screw head; a wire entry on a side face (Phoenix: wire connection direction 0 deg, horizontal), OHMNI +X (UNCERTAIN which long face); entry window default 3.4 (Y) x 3.0 (Z) centered Z = 5.0 (UNCERTAIN, cosmetic).
- - Top profile: RESEARCH_REQUIRED; default flat top at 13.8 with 1.0-deep screw pockets (first-pass front-deck step withdrawn).
- - Dimensions M / Geometry L / Materials-appearance M. status: partial.
  - Same resolved items and open items as OHM-159 (height 13.8 vs 10.3 conflict, entry face, top profile).
  - Validation: pitch x N length; pin spacing 10.16 between outer pins; Farnell "a" for 3 positions = 15.24.
  
  ---
- COSMETIC_PROVISIONAL window_depth=3.266666666666667: One third of stated housing depth; internal recess only.
- COSMETIC_PROVISIONAL screw_head_height=0.5: Half the pocket depth; head stays recessed.
- COSMETIC_PROVISIONAL slot_width=0.375: One eighth of specified/placeholder 3 mm head diameter.
- COSMETIC_PROVISIONAL slot_length=2.4000000000000004: 80 percent of head diameter; slot stays inside head.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-161 — source partial

- plug_length: 18.3 (UNCERTAIN/L)
- plug_height: 15.0 (UNCERTAIN/L)
- - Two sub-bodies: (1) header: green shroud 12.16 x 12.0 x 8.6 open on the +X face, with the contact pins inside and 1.0 square solder pins dropping to Z = -3.5 (the X position of the pin row inside the shroud is UNCERTAIN: placeholder row 3.0 mm from the rear face, so the shroud spans X from -3.0 to +9.0, body_offset X = +3.0); (2) plug: green body, screw heads on top and the wire entry on the +X rear end (in-line with the plug-in direction, screw M3, strip 7 mm), placeholder envelope X from +0.7 to +19.0 (18.3 long, seated about 8.3 inside the header), Y +-5.08, Z up to 15.0.
- - Assembled state is the default; separated-state offset (along +X) is a parameter. The plug-to-shroud interlocking profile is not read, so the placeholder solids overlap; the LOD0 model uses the union.
- - Vertical MSTBVA option: shroud 8.6 (X) x 12.16 (Y) x 12.0 (Z), plug inserted from +Z, wire entry then pointing +Z (UNCERTAIN). Coding feature: not read.
- - tht_holes diameter 1.4 (PXC-MSTBA-2/10 and datasheet copies), pitch 5.08; FCO hole center; body_offset (+3.0, 0) (UNCERTAIN).
- 3. Plug box 18.3 x (N x 5.08) x 15.0 seated into the shroud (placeholder offset).
- - Resolved in gap-fill: header shroud 12.16 x 12.0 x 8.6, solder pin 3.5 (3.9 vertical), both orientations consistent; first-pass placeholders 9.8 deep and 13.8 high for the assembly are withdrawn. The default header is now the right-angle MSTBA, so the plug direction is +X (the first pass said plug seats from +Z, which belongs to the vertical MSTBVA).
- - Dimensions M (header) / L (plug) / Geometry L / Materials-appearance M. status: partial.
  - Resolved in gap-fill: header shroud 12.16 x 12.0 x 8.6, solder pin 3.5 (3.9 vertical), both orientations consistent; first-pass placeholders 9.8 deep and 13.8 high for the assembly are withdrawn. The default header is now the right-angle MSTBA, so the plug direction is +X (the first pass said plug seats from +Z, which belongs to the vertical MSTBVA).
  - Unresolved: plug dimensions per axis and seated depth, pin row position in the shroud, coding, plug-to-shroud profile, Wurth WR-TBL pluggable and Camdenboss not opened.
  - Validation: a = (N-1) x 5.08: 9 x 5.08 = 45.72 matches N=10; 12.16 = 10.16 + 2.0 consistent across MSTBA and MSTBVA; 12.1 - 3.5 = 8.6 and 15.9 - 3.9 = 12.0 total/body relations hold.
  
  
  ---
- COSMETIC_PROVISIONAL wall=0.5: Borrow OHM-155 0.5 mm shroud wall; keep header outer envelope fixed.
- COSMETIC_PROVISIONAL internal_pin_z=4.3: Half of 8.6 mm header height; PCB pin axes unchanged.
- COSMETIC_PROVISIONAL internal_pin_end=8.5: Header front X=9.0 minus cosmetic wall; inside header.
- COSMETIC_PROVISIONAL screw_x=9.85: Center of specified plug X extent; Y positions follow pitch.
- COSMETIC_PROVISIONAL pocket_depth=1.075: One eighth of header height, recessed into plug.
- COSMETIC_PROVISIONAL window_width=3.3866666666666667: Two thirds of sourced contact pitch, centered on each row position.
- COSMETIC_PROVISIONAL window_height=2.8666666666666667: One third of header height, inside 15 mm plug.
- COSMETIC_PROVISIONAL window_z=5.0: One third of plug height; does not alter plug envelope.
- COSMETIC_PROVISIONAL window_depth=3.0: One quarter of header depth, recessed from plug +X face.
- COSMETIC_PROVISIONAL screw_head_height=0.5375: Half the pocket depth; head stays recessed.
- COSMETIC_PROVISIONAL slot_width=0.375: One eighth of specified/placeholder 3 mm head diameter.
- COSMETIC_PROVISIONAL slot_length=2.4000000000000004: 80 percent of head diameter; slot stays inside head.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-162 — source partial

- overall_length: 15.26 (UNCERTAIN/L)
- overall_height: 5.8 (UNCERTAIN/L)
- | shell height Z | 5.8 | 5.5 | 6.2 | UNCERTAIN (coordinator brief, RECALLED_UNVERIFIED) | L |
- | overhang beyond board edge | 0 (default, edge flush with mating face) | 0 | 1.0 | UNCERTAIN: RESEARCH_REQUIRED | L |
- Hollow rectangular shell, 4 walls ~0.3 thick (RECALLED_UNVERIFIED), open at +Y. Inside: a plastic tongue plate spanning most of the width (~12.0 wide, ~1.9-2.0 thick, RECALLED_UNVERIFIED), positioned in the lower half of the cavity so contacts face the PCB for the normal right-angle orientation, carrying 4 gold contact strips about 1.0 wide, recessed ~1 mm from the front of the tongue. Rear wall closes the shell. Seam: a visible butt seam along the top face centerline or a lap seam at the bottom (varies). Small spring dimples (3-4 raised rectangles) on the top and bottom outer faces within ~2 mm of the front lip. Shell rear tab/flange: 2 side legs bend down at the rear corners.
- - 4 signal pins, square 0.5 x 0.5 (RECALLED_UNVERIFIED) tin/gold-flash, bend 90° out of the rear-bottom, tails to Z=-2.6 default (hole 0.95).
- - Pin 1 = VBUS (RECALLED_UNVERIFIED function; position from KC), FCO position (3.5, -1.355). Pins 2 (1.0, -1.355), 3 (-1.0, -1.355), 4 (-3.5, -1.355). Numbering runs toward -X (this is KC rotated 180°: OHMNI x = -KC x).
- FCO center = bbox center of 4 pins + 2 shield holes (pad centers). Through holes Ø0.95 x4 at the pin coordinates; Ø2.3 x2 at shield positions. Body offset (0, +4.0) (fab -3.625..+11.635 in Y, center 4.005). Mating face at Y=+11.6; overhang default 0 (the footprint's board edge is not given in KC; RESEARCH_REQUIRED). Shell underside Z=0 (RESEARCH_REQUIRED standoff; plastic standoffs 0-0.5 typical).
- Shell MAT_NICKEL (or MAT_STEEL_STAINLESS); tongue MAT_PLASTIC_WHITE or MAT_PLASTIC_BLACK (white common for USB 2.0 A in many mfrs, RECALLED_UNVERIFIED), contacts MAT_GOLD, pins MAT_TIN_BRIGHT, rear insulator MAT_PLASTIC_BLACK.
- 2. Cut cavity 12.5 x 4.9 from +Y face, depth ~13.5 (RECALLED_UNVERIFIED).
- Dimensions M (pads/legs/pitch/tail) / L (height, depth, overhang). Geometry M. Materials M. Second pass: pitch and 2.6 tail now confirmed by a second document (Molex product page); height/depth searches (Molex drawing, USB-IF) did not yield readable numbers, so status stays partial. Unresolved: shell height, wall thickness, tongue thickness, overhang, leg shape, USB 2.0 spec numbers (not opened). Validation: pitch pattern 2.5+2.0+2.5=7.0 matches pad x 0..7; shield span 13.14 matches shell 13.1; pin 1 sign checked against 180° rotation.
  
  ---
- COSMETIC_PROVISIONAL wall=0.29: One twentieth of smaller shell face dimension, inward from sourced outer envelope.
- COSMETIC_PROVISIONAL tongue_recess=0.5: Front recess bounded by one tenth of sourced length and 0.5 mm.
- COSMETIC_PROVISIONAL contact_visual_height=0.057999999999999996: One hundredth shell height; internal mating strips only.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-163 — source partial

- overall_length: 16.4 (UNCERTAIN/L)
- overall_height: 10.9 (UNCERTAIN/L)
- | height Z | 10.9 | 10 | 11.5 | UNCERTAIN, RECALLED_UNVERIFIED | L |
- | overhang | 0 | 0 | 1.0 | RESEARCH_REQUIRED | L |
- Bent-sheet shell, nearly square profile with top corners chamfered (key). Open at +Y. Inside: an insulator block hanging from the top with a tongue-less 4-contact arrangement (2 contacts on upper face, 2 on lower, RECALLED_UNVERIFIED). Seam on the bottom/rear. Rear skirt closes. 2 side legs at rear.
- Dims M/L, geometry M, materials M. Second pass: searches for a readable Lumberg 2411 02 / USB-B drawing returned only Digikey listing pages (no dimensions); no change, status stays partial. Unresolved: shell height, chamfer size, pin positions function mapping, depth vs shell depth. Validation: shield span 12.0 = fab width; pin pitch 2.5 x 2.0 matches USB-B; transform checked.
  
  ---
- COSMETIC_PROVISIONAL wall=0.545: One twentieth of smaller shell face dimension, inward from sourced outer envelope.
- COSMETIC_PROVISIONAL cavity=[10.91, 9.81, 13.12]: Outer face minus twice cosmetic wall; cavity depth 80 percent of body length.
- COSMETIC_PROVISIONAL tongue=[8.728, 2.4525]: 80 percent of cavity width and one quarter of cavity height, inside opening.
- COSMETIC_PROVISIONAL tongue_recess=0.5: Front recess bounded by one tenth of sourced length and 0.5 mm.
- COSMETIC_PROVISIONAL contact_visual_height=0.109: One hundredth shell height; internal mating strips only.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-164 — source partial

- overall_width: 7.3 (MFR_DRAWING/L)
- overall_length: 5.0 (MFR_DRAWING/L)
- overall_height: 2.86 (MFR_DATASHEET/L)
- | height Z | 2.86 | 2.4 | 3.0 | Wurth 629105150521 listing "height 2.86 mm" (lioncircuits.com/parts/629105150521, S4) and Wurth 629105136821 "height 2.9 mm, length 5.9 mm" (S4). First-pass value 2.6 (RECALLED_UNVERIFIED) superseded; Amphenol 10118194 height itself not found | M for Wurth member, L for Amphenol default |
- | mating opening | ~6.85 x 1.8 | | | RECALLED_UNVERIFIED | L |
- Flat trapezoid-profile shell (bottom corners chamfered ~45°, top flat), open at +Y, tongue-less 5-contact insulator at the rear of the cavity (contacts exposed as small gold strips on the cavity ceiling at 0.65 pitch, RECALLED_UNVERIFIED), shell with 2 front and 2 rear stamped tabs/legs. Rear tail pads protrude behind.
- FCO = bbox center of all pad/hole centers (center shifted -0.05 in Y vs KC). Body offset (0, +1.0), body 7.3 x 5.0, mating face Y=+3.5. Shell bottom Z=0. Overhang default 0 (RESEARCH_REQUIRED).
- Trapezoid chamfers define the bottom (chamfered side faces PCB for the standard orientation, RECALLED_UNVERIFIED). Pin 1 at +X (after rotation).
- Dims L (width/depth are footprint-author outlines, height and opening recalled), geometry M, materials M. Validation: pitch 0.65 x 4 = 2.6 span matches ±1.3; mirrored x checked.
  Second pass: height 2.86 adopted from the Wurth distributor listing (first pass 2.6 was recalled, 2.9 seen on a sibling Wurth part, so 2.86 sits inside the 2.6-2.9 spread); WIKI-USBHW (weak S5) lists a Micro-B receptacle opening of 6.85 x 1.8, agreeing with the recalled value, but it is not a primary source so the opening stays L. Amphenol drawing again not readable. Status stays partial. Unresolved: Amphenol shell height, true shell depth, primary opening dims.
  
  ---
- COSMETIC_PROVISIONAL wall=0.143: One twentieth of smaller shell face dimension, inward from sourced outer envelope.
- COSMETIC_PROVISIONAL tongue=[5.48, 0.45]: 80 percent of cavity width and one quarter of cavity height, inside opening.
- COSMETIC_PROVISIONAL tongue_recess=0.5: Front recess bounded by one tenth of sourced length and 0.5 mm.
- COSMETIC_PROVISIONAL contact_visual_height=0.0286: One hundredth shell height; internal mating strips only.
- COSMETIC_PROVISIONAL pad_thickness=0.143: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-165 — source partial

- overall_length: 7.35 (MFR_DRAWING/L)
- Stadium/rounded-rectangle outer shell 8.94 x 3.26 (corner R ~1.0, RECALLED_UNVERIFIED) with a 8.34 x 2.56 cavity whose corners are rounded; a thin center tongue (~0.7 thick, RECALLED_UNVERIFIED) spans the cavity (12 contacts per side visible as flat gold strips at 0.5 pitch, near the tongue front; USB 2.0 16-pin version omits the signal contacts A2/A3/A10/A11 and mirror). Shell: stamped stainless/brass, seam at rear bottom, 4 THT legs and 2 plastic NPTH pegs (one oval, one round) at rear-bottom.
- Footprint FCO center = bbox center of all pad/hole pattern (shell legs, signal pads, pegs) = (0, KC y -1.09). Body offset (0, +1.1) for the 10.45-deep fab outline; shell front face at Y=+6.3. Top-mount: shell underside Z=0 (RESEARCH_REQUIRED: whether mid-mount cutout is needed), shell top at Z=3.26, tails flush. Overhang default 2.5 beyond the board edge line (the board edge is at Y = front-legs + ~0 in this convention, ~Y +3.9; RESEARCH_REQUIRED).
- Second pass: the shell dimensions are now tied to ONE named drawing, GCT USB4105-GF-A (Rev B, Farnell-hosted, see PKG-USB_C): width 8.94, depth 7.35, height 3.31 vs 3.26, mating depth 6.5 max, stake 0.95; height is cross-checked by two more documents (3.21 Wurth, 3.26 GCT USB4240), depth is not (L). Pad coordinates remain the Amphenol 12401610E4-2A KiCad pattern; the GCT USB4105 footprint could not be fetched, so the pad pattern is NOT the GCT part's (flagged). Status stays partial because depth label, pad/leg coordinates of the GCT part, Type-C spec corner radius, tongue thickness and overhang are unverified. Sources contradict: first pass 7.3 vs drawing 7.35 (adopted 7.35, 7.3 kept as min); first pass 3.26 vs drawing 3.31 (kept 3.26, range widened). Dimensions M (opening/width/height), L (depth/overhang); geometry M; materials M. Conflict: USB4105 summary 8.64 x 5.78 (likely footprint) vs 8.94; the Amphenol part is listed 24-pad in KC while the coordinator brief calls it 16-pin: ambiguity left as `contact_set`. Validation: A row 12 x 0.5 spans 5.5 = ±2.75 matches; B row offset 0.25; transform checked.
  
  
  ---
- COSMETIC_PROVISIONAL wall=0.16299999999999998: One twentieth of smaller shell face dimension, inward from sourced outer envelope.
- COSMETIC_PROVISIONAL tongue_recess=0.5: Front recess bounded by one tenth of sourced length and 0.5 mm.
- COSMETIC_PROVISIONAL contact_visual_height=0.0326: One hundredth shell height; internal mating strips only.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-166 — source partial

- overall_width: 7.7 (MFR_DRAWING/L)
- overall_length: 9.25 (MFR_DRAWING/L)
- overall_height: 4.0 (UNCERTAIN/L)
- | height Z | 4.0 | 3.8 | 4.5 | UNCERTAIN, RECALLED_UNVERIFIED | L |
- FCO center from pad centers (KC center shift y +0.15). Body offset (0, +1.125), face Y=+5.75, shell bottom Z=0. Overhang 0 (RESEARCH_REQUIRED).
- Dims L, geometry M, materials M. Second pass: the Wurth 65100516121 datasheet mirror (https://www.zeuthen.desy.de/~sulanke/Projects/ICECUBE/ICM/datasheets/con_USB-B_mini_WE_65100516121.pdf) was opened: title "MINI USB SMT TYPE B 5 CONTACTS", 2 sheets, general tolerances .X ±0.2 / .XX ±0.15 only; dimensions not readable. Wurth/Lioncircuits listing has no dimensions. WIKI-USBHW (weak, inconsistent) not used. Status stays partial. Validation: 0.8 x 4 = 3.2 span matches ±1.6. Unresolved: height, true shell dims.
  
  ---
- COSMETIC_PROVISIONAL wall=0.2: One twentieth of smaller shell face dimension, inward from sourced outer envelope.
- COSMETIC_PROVISIONAL chamfer=0.8: One fifth face height, inward corner removal.
- COSMETIC_PROVISIONAL cavity=[7.3, 3.6, 7.4]: Outer face minus twice cosmetic wall; cavity depth 80 percent of body length.
- COSMETIC_PROVISIONAL tongue=[5.84, 0.9]: 80 percent of cavity width and one quarter of cavity height, inside opening.
- COSMETIC_PROVISIONAL tongue_recess=0.5: Front recess bounded by one tenth of sourced length and 0.5 mm.
- COSMETIC_PROVISIONAL contact_visual_height=0.04: One hundredth shell height; internal mating strips only.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-167 — source partial

- overall_length: 14.9 (UNCERTAIN/L)
- overall_height: 6.5 (MFR_DATASHEET/L)
- FCO center from 2 outermost pins and 2 shield pads. Body offset (0, +6.5), mating face at Y=+13.95. Pads reach ±6.775 in X. Overhang: the straddle type sits partly over the board edge; RESEARCH_REQUIRED (not in KC).
- Dims L (envelope), H (pitch), geometry M, materials M. Second pass: pitch upgraded to consensus (Molex, TE, FCI/Foxconn pages). Contact Technology HDMI-19APL2 drawing (contactswitch.com URL in the KC file) was not reachable; shell depth, height, overhang remain unsourced. Several HDMI drawings (Foxconn sheet, TE 1-1747981-4, Molex 500254-1931 page) were opened and contain no readable outline dimensions. Status stays partial. Validation: 19 pins at 0.5 pitch: 9.0 span matches ±4.5. Unresolved: cavity height, shell height, overhang, wall thickness, contact pad width, pin-1 side per HDMI spec.
- Dims L (envelope), H (pitch), geometry M, materials M. Second pass: pitch upgraded to consensus (Molex, TE, FCI/Foxconn pages). Contact Technology HDMI-19APL2 drawing (contactswitch.com URL in the KC file) was not reachable; shell depth, height, overhang remain unsourced. Several HDMI drawings (Foxconn sheet, TE 1-1747981-4, Molex 500254-1931 page) were opened and contain no readable outline dimensions. Status stays partial. Validation: 19 pins at 0.5 pitch: 9.0 span matches ±4.5. Unresolved: cavity height, shell height, overhang, wall thickness, contact pad width, pin-1 side per HDMI spec.
  
  ---
- COSMETIC_PROVISIONAL wall=0.325: One twentieth of smaller shell face dimension, inward from sourced outer envelope.
- COSMETIC_PROVISIONAL chamfer=1.3: One fifth face height, inward corner removal.
- COSMETIC_PROVISIONAL cavity=[13.35, 5.85, 11.920000000000002]: Outer face minus twice cosmetic wall; cavity depth 80 percent of body length.
- COSMETIC_PROVISIONAL tongue=[10.68, 1.4625]: 80 percent of cavity width and one quarter of cavity height, inside opening.
- COSMETIC_PROVISIONAL tongue_recess=0.5: Front recess bounded by one tenth of sourced length and 0.5 mm.
- COSMETIC_PROVISIONAL contact_visual_height=0.065: One hundredth shell height; internal mating strips only.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-168 — source partial

- overall_width: 11.0 (DERIVED/L)
- overall_length: 10.0 (UNCERTAIN/L)
- overall_height: 3.0 (DERIVED/L)
- | shell width X | 11.0 | DERIVED: 10.42 + 2 x 0.3 assumed wall (wall RECALLED_UNVERIFIED) | L |
- | shell depth Y | 10.0 | UNCERTAIN placeholder, RESEARCH_REQUIRED | L |
- Second-pass status: mating size and pitch sourced, outer shell and depth still placeholders. Placeholder statement kept for items marked UNCERTAIN.
- 19 contacts at 0.4 pitch (TE 2013978-1 listing); positions x = 3.6 - 0.4(n-1) (n=1 at +X), DERIVED from pitch x 18/2 = 3.6 (centered). Whether the 19 contacts share one row at 0.4 or split into two staggered rows at 0.8 (odd/even) is RESEARCH_REQUIRED (HDMI Type A uses 10/9 in two rows; Type C is the same 19-pin layout per WIKI-HDMI); pin 1 (3.6, 0) is a placeholder row position, contact tail length 0.5 mm per Heilind "tail length .021 in, 5 mm" text is also unclear.
- Placeholder FCO from outermost pins and 2 shield pads at x=±5.0. Body offset (0, +5) placeholder, mating face +Y. RESEARCH_REQUIRED.
- Trapezoid key; pin 1 at +X placeholder.
- pin1_indicator: "placeholder"
- Dims L (outer shell/depth placeholders) / M (mating size, pitch), geometry L, materials M. Status raised research_required to partial because the mating size and pitch are now sourced; do not implement outer shell, depth or tail geometry without a drawing. RESEARCH_REQUIRED: mfr drawing (e.g. Amphenol 10042618, Molex 500254, Hirose) with shell dims, pad coordinates, tail layout, pin-1 position. Validation: only internal consistency (19 x 0.4 span 7.2).
- Dims L (outer shell/depth placeholders) / M (mating size, pitch), geometry L, materials M. Status raised research_required to partial because the mating size and pitch are now sourced; do not implement outer shell, depth or tail geometry without a drawing. RESEARCH_REQUIRED: mfr drawing (e.g. Amphenol 10042618, Molex 500254, Hirose) with shell dims, pad coordinates, tail layout, pin-1 position. Validation: only internal consistency (19 x 0.4 span 7.2).
  
  ---
- COSMETIC_PROVISIONAL contact_visual_width=0.2: Half stated 0.4 pitch; visual terminal width only, no footprint binding; row positions unchanged.
- COSMETIC_PROVISIONAL wall=0.15: One twentieth of smaller shell face dimension, inward from sourced outer envelope.
- COSMETIC_PROVISIONAL chamfer=0.6: One fifth face height, inward corner removal.
- COSMETIC_PROVISIONAL tongue=[8.336, 0.605]: 80 percent of cavity width and one quarter of cavity height, inside opening.
- COSMETIC_PROVISIONAL tongue_recess=0.5: Front recess bounded by one tenth of sourced length and 0.5 mm.
- COSMETIC_PROVISIONAL contact_visual_height=0.03: One hundredth shell height; internal mating strips only.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-169 — source partial

- Black thermoplastic housing; front face with plug opening about 11.7 wide x 7 tall (RECALLED_UNVERIFIED) with the small rectangular latch notch cut in the (downward, for tab-down) side; 8 gold contact wires visible in the cavity roof; sides flat; rear closed. Shielded variant: nickel shell wrapping top/sides/rear with a front lip, shield legs 2 (or 4), and 2 front-side spring fingers; LED variant adds 2 rectangular windows in the front face above the opening (left and right) and 4 extra pins.
- Default FCO from the 8 pins and 2 NPTH. Body offset (0, +3.2), housing from y=-5.67 to +12.07 (17.74 deep, default part Amphenol 54602-908LF). Mating face Y=+12.07. Overhang default 0 (RESEARCH_REQUIRED, RJ45 jacks often have the face flush or up to ~1 mm over). Housing underside Z=0 (stand-off RESEARCH_REQUIRED).
- 1. Housing 15.3 x 17.74 x 12.70, bottom Z=0. 2. Cut cavity 11.7 x 7 x 14 from +Y. 3. Latch notch 4.5 x 1.5 (RECALLED_UNVERIFIED). 4. Contacts. 5. Pins (staggered). 6. Optional shell and LEDs. 7. NPTH pegs below.
- Pass 2: depth and height conflict resolved by choosing ONE named part (Amphenol 54602-908LF: 15.30 x 17.74 x 12.70; width and depth confirmed by two documents, height by one listing). Status stays partial because the plug cavity (11.7 x ~7, WIKI-MOD plug width 11.68 only weakly agrees), latch notch, contact geometry and shell/standoff are recalled, and the mfr drawing itself was not readable. Dims M (pin/post/envelope), L (cavity); geometry M; materials M. Validation: 8.89 span; post spacing 11.43 matches RJE7M layout width; transform checked. Unresolved: cavity dims, latch notch, LED window size (RJHSE538X member), mfr drawing dimensions (not readable). Resolved: depth conflict (default part is 54602-908LF, 17.74), height 12.70.
  
  ---
- COSMETIC_PROVISIONAL tail_visual_width=0.45: Visual tail stock below the stated 0.76 mm RJ45 hole; RJ11 borrows sibling stock. Hole positions unchanged, no drill inference.
- COSMETIC_PROVISIONAL latch=[4.446, 1.5875]: Latch width 38 percent cavity width, depth one eighth housing height; inward removal.
- COSMETIC_PROVISIONAL internal_contact=[0.4875, 0.127]: Internal spring strip width from cavity/contact count; height 1 percent envelope.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-170 — source partial

- overall_width: 12.7 (MFR_DRAWING/L)
- overall_length: 18.0 (MFR_DRAWING/L)
- overall_height: 13.2 (MFR_DRAWING/L)
- Values superseded from first pass: width 13.4 -> 12.70, depth 14 -> 18.00, height 13 -> 13.20, cavity 9.7 -> 10.0. Pin and NPTH coordinates below are STILL placeholders (no readable pad layout), so this entry is envelope-only.
- Placeholder: 4 pins at x = 1.53, 0.51, -0.51, -1.53 (pitch 1.02), alternate rows y=-1.5 / -3.5 (UNCERTAIN); pin 1 at +X (1.53,-1.5); 6P6C: 6 pins at x = 2.55..-2.55. NPTH at (±4.0, +3.5) placeholder.
- Placeholder FCO from pins + NPTH; body offset (0, +3), mating face +Y.
- Pass 2: status raised research_required to partial because a named part (Amphenol 54601 series) now gives an envelope, but at confidence L because the two drawing summaries conflict on which of 13.2 / 12.7 / 18.0 is width, depth or height (18.0 as depth is the majority reading). Pin coordinates, row spacing and NPTH positions remain PLACEHOLDERS (RESEARCH_REQUIRED): do not use them as a footprint. Dims L, geometry L, materials M. Needed: a readable 54601 / Wayconn MJ179P / Bel Stewart drawing image with pad layout.
- Pass 2: status raised research_required to partial because a named part (Amphenol 54601 series) now gives an envelope, but at confidence L because the two drawing summaries conflict on which of 13.2 / 12.7 / 18.0 is width, depth or height (18.0 as depth is the majority reading). Pin coordinates, row spacing and NPTH positions remain PLACEHOLDERS (RESEARCH_REQUIRED): do not use them as a footprint. Dims L, geometry L, materials M. Needed: a readable 54601 / Wayconn MJ179P / Bel Stewart drawing image with pad layout.
  
  ---
- COSMETIC_PROVISIONAL tail_visual_width=0.45: Visual tail stock below the stated 0.76 mm RJ45 hole; RJ11 borrows sibling stock. Hole positions unchanged, no drill inference.
- COSMETIC_PROVISIONAL latch=[3.8, 1.65]: Latch width 38 percent cavity width, depth one eighth housing height; inward removal.
- COSMETIC_PROVISIONAL internal_contact=[0.8333333333333334, 0.132]: Internal spring strip width from cavity/contact count; height 1 percent envelope.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-171 — source partial

- overall_width: 11.6 (UNCERTAIN/L)
- overall_length: 17.9 (UNCERTAIN/L)
- overall_height: 6.0 (UNCERTAIN/L)
- | body height Z, default KB3SPRS | 6.0 placeholder | 5.0 | 7.0 | UNCERTAIN: no KB3SPRS height found; 6.0 chosen because the nose is 6.0 wide; RESEARCH_REQUIRED | L |
- | mating hole Ø | 3.5 mating plug (SJ1-352xN datasheet "Ø3.5 mating plug"); opening ~Ø6 on the front boss RECALLED_UNVERIFIED | | | | L |
- Black rectangular plastic housing with a round front aperture and a short cylindrical collar/boss (RECALLED_UNVERIFIED) projecting about 1-1.5 mm from the face; metal contact springs inside; 5 flat solder pins (tip, ring, sleeve, and 2 switch contacts) exit bottom, plus locating pegs on some parts (not in the KiCad KB3SPRS/SJ1-3535NG footprints). Metal sleeve tab on one side.
- 5 THT solder pins (tip T, tip-switch TN, ring R, ring-switch RN, sleeve S), flat tails about 0.3 x 0.9 (RECALLED_UNVERIFIED) in oval holes Ø1.3 (pad 4.0 x 2.2).
- Alternate member PJ-307: pin positions RESEARCH_REQUIRED (NOT footprint-valid; do not reuse the KB3SPRS pads). SMD analogue evidence: KC PJ311 6-pad, pads 2.0 x 1.5 at x=±3.5 with NPTH Ø1.5 at (0,-4.3) and (0, 2.7) (KC axes); KC PJ320D 4-pad 1.2 x 2.5 pads with NPTH Ø1.5.
- FCO = bbox center of the 5 pad centers (no peg holes in the KiCad footprint). Body offset: body Y -6.9..+7.4 (center +0.25) plus nose to +11.0; mating face Y=+11.0. Through holes: oval Ø1.3 (KB3SPRS) at the five coordinates above. Overhang default 0 (the footprint's board edge is not given; many jacks sit flush or overhang about 1 mm; RESEARCH_REQUIRED).
- 1. Body box X ±5.8, Y -6.9..+7.4, Z 0..6.0 (height placeholder). 2. Nose box 6.0 wide (X -3.3..+2.7) Y +7.4..+11.0, same height (or Ø6 round boss; nose shape in plan only is sourced). 3. Bore Ø3.8 along Y at X=-0.3, Z=height/2 (bore size recalled: 3.5 mm plug per SJ1-352xN "Ø3.5 mating plug"), depth about 8. 4. 5 pins at the coordinates above. 5. Springs (LOD2).
- Pass 2: pin coordinates are no longer placeholders: the default switched from the PJ-307 envelope (pins unresolved) to the Ledino KB3SPRS because it has a real, footprint-valid KiCad pad pattern (re-centered and rotated, transform stated). Trade-off: KB3SPRS is a different, larger jack than PJ-307 (17.9 vs 14.2 long incl. nose), its dimensions come from the footprint author's fab outline (L), and its height is unknown (placeholder 6.0). PJ-307 stays an alternate member with envelope M and pins unresolved. Status partial. Dims L (default) / M (PJ-307 envelope), geometry M (pins), materials M. Validation: pad bbox centered (X ±4.9, Y ±5.6); body X ±5.8 symmetric; nose center X=-0.3 equals pad S X (bore axis), consistent; SJ1-3535NG body Y ±7.0 symmetric after the same method. RESEARCH_REQUIRED: KB3SPRS and PJ-307 body height, nose/boss shape (round vs rectangular), bore diameter, PJ-307 pin coordinates, peg positions, tail lengths.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-172 — source partial

- overall_height: 11.0 (MFR_DATASHEET/L)
- barrel_bore_diameter: 5.5 (UNCERTAIN/L)
- insertion_depth: 9.0 (MFR_DATASHEET/L)
- Default (PKG-DC_JACK, CUI PJ-102A/PJ-002A envelope): L (Y) 14.4 [14.4-14.5] (M: Oregon State, UConn and KiCad PJ-102AH outline agree), W (X) 10.7 [9.0 KiCad main-body alt, 11.1 Switchcraft] (M-L: Oregon State PJ-002A and UConn PJ-102A both read 10.7), H (Z) 11.0 (L: PJ-002A only; UConn lists 6.5, not adopted), barrel bore OD 5.5 (standard barrel; not read in an opened document, L), center pin dia 2.0 (alt 2.5; M), insertion depth 9.0 (9.5 alt). First-pass default W 9.0 was superseded by 10.7 (see family Conflicts); the brief's 14.0 x 9.0 x 11.0 was not confirmed.
- Rectangular housing, vertical sides, flat top. A circular bore (dia 5.5, depth 9.0) opens in the +Y face with its axis at x=+2.35 (the body centerline, FCO frame) and z=5.5 (PLACEHOLDER: mid-height; UConn lists a 6.5 value that may be the axis height; RESEARCH_REQUIRED). Center pin cylinder dia 2.0 on axis, rising from the bore floor to 0.5 below the face. Rear and bottom corners square; optional 0.3 mm edge chamfers at LOD2. Two small bottom pegs are RESEARCH_REQUIRED (omit).
- 3 THT terminals: P1 center pin, P2 sleeve, P3 switch. Rectangular tails 0.5 x 1.0 (PLACEHOLDER thickness; UConn lists a 1.0 x 1.6 hole). Layout (second pass, M-L): KiCad CUI PJ-102AH footprint (S5) gives P1 (0,0), P2 (0,6.0), P3 (4.7,3.0) in KiCad coordinates, matching the UConn PJ-102A callouts 3.0 / 4.7. Transformed to the OHMNI frame (Y flipped to Y-up, rotated 180 deg so the bore opens toward +Y, then bbox-centered per FCO), centers are: P1 center pin (+2.35,-3.0), P2 sleeve (+2.35,+3.0), P3 switch (-2.35, 0). P1 is nearest the rear, P2 nearest the opening, P3 sits on the side of the body. The earlier placeholder (pitch 3.5, P1 (0,-1.75), P2/P3 at +-3.0) is replaced; the Oregon State "terminal spacing 3.5, holes 2.0" belongs to the PJ-002A layout and is kept as an alternate, not modeled. Tails to Z=-2.6 default.
- Dimensions L-M (length M, width M-L, height L), geometry L, materials M. Unresolved: height 11.0 only from PJ-002A (PJ-102A 6.5 unexplained); bore OD 5.5 not read in an opened document; bore axis height; pin tail thickness; mounting pegs; PJ-002A vs PJ-102A layout differences (a PJ-002A layout is not modeled). Validation: four sources agree on 14.4; width 10.7 from two datasheets, 9.0 only from the KiCad outline; layout reproduces 6.0 / 4.7 / 3.0 in two KiCad footprints and the UConn callouts; FCO bbox of hole pattern centered on origin (X +-2.35 holes, Y +-3.0).
  
  
  
  ---
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-173 — source partial

- overall_height: 5.0 (UNCERTAIN/L)
- Nylon housing as a keyed rounded rectangle prism 9.9 wide (X) by 5.0 high (Z) extruded along Y for 13.95, two corners chamfered (XT signature; XT30 chamfer size RESEARCH_REQUIRED, placeholder 1.0). Two locating pegs dia 1.0 project down from the housing underside near the mating end. Male: two gold pins visible in the +Y mating face inside a shroud. Pins bend down through the housing rear.
- 2 power pins, pitch 5.0, along X; FCO centers pin1 (-2.5,-4.825), pin2 (+2.5,-4.825). Tail dia about 1.5 (PLACEHOLDER; the hole is 1.7, KiCad drill 1.9). Tails to Z=-2.6 default. The KiCad footprint numbers the square pad (pad 1) at +X; OHMNI keeps pin 1 at -X per Section 6 (mirror delta recorded; importers map by pad name). + / - assignment RESEARCH_REQUIRED. 2 locating pegs dia 1.0 at (+-5.5, +5.175) (not electrical).
- Housing MAT_PLASTIC_NATURAL default (XT is commonly yellow; yellow is not sourced and not a token, propose MAT_PLASTIC_YELLOW #E0B81F rough 0.5 if desired); pins MAT_GOLD.
- body: {shape: keyed chamfered prism, material: MAT_PLASTIC_NATURAL, color: yellow-or-natural, features: ["two chamfered corners 1.0 placeholder", "two locating pegs dia 1.0"]}
- Dimensions M-L (X, Y, pitch, holes M-L; height L), geometry L, materials L. Resolved: 9.90 = width, 10.00 = pin-to-peg distance, 11.00 = peg spacing, 1.7 = power pin hole, 1.0 = peg hole, 13.30 vs 13.95 (rear step). Unresolved: height 5.0 is an interpretation (no explicit label), chamfer size, pin tail diameter, polarity, whether the rear step is 0.65. Validation: callout list matches the KiCad footprint on five independent numbers (5.0, 9.9, 9.0, 11.0, 10.0, hole sizes); 13.1+0.85=13.95 closes the length; pin x=+-2.5 and pegs x=+-5.5 fit within the 9.9 body plus peg overhang (pegs lie outside the pin span but inside the 11.0 spacing).
  
  
  
  ---
- COSMETIC_PROVISIONAL wall=0.625: One eighth body height inward, leaves keyed shroud within sourced body.
- COSMETIC_PROVISIONAL bullet_diameter=1.6666666666666667: Internal mating bullet diameter one third body height; board tail shape and coordinates unchanged.
- COSMETIC_PROVISIONAL recess_depth=4.6499999999999995: Front recess one third sourced length, within housing.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-174 — source partial

- XT60PW-M: X 15.5, Y 18.2, Z 8.4, pitch 7.2 (now read twice in the Amass sheet, M-L), features 2-0.6 x 1.7 and 2-dia 2.7 (assignment L). Basis MFR_DATASHEET (hosted), confidence M-L (hole assignment L). The first-pass chamfer 1.85 is not confirmed (1.85, 2.5, 6 and 13.5 are unassigned callouts). XT60PW-F length is 17.2 (callout).
- Same keyed rounded-rectangle nylon housing as XT30, scaled; two chamfered corners (size RESEARCH_REQUIRED; placeholder 1.85). Male shroud holds two gold bullet-style pins (diameter RESEARCH_REQUIRED).
- 2 pins pitch 7.2 along X: pin1 (-3.6, 0), pin2 (+3.6, 0). Callouts 2-0.6*1.7 (flat tails or locating tabs) and 2-dia 2.7 (holes) are both present; which belongs to the power pins is not established (L). PLACEHOLDER: power pins modeled as flat 0.6 x 1.7 tails to Z=-2.6 as in the first pass. Polarity RESEARCH_REQUIRED.
- Holes at pin positions (+-3.6,0): slot 0.6 x 1.7 (callout) or dia 2.7 (callout), RESEARCH_REQUIRED which; second feature pair positions not read. Origin = center between pins (pattern incomplete, so FCO is provisional). body_offset_mm = (0,+7.75) PLACEHOLDER derived by analogy with XT30PW-M (body rear edge at the pin-hole outer edge: -1.35 for a 2.7 hole, so center = -1.35 + 18.2/2 = 7.75). Overhang 0.
- body: {shape: keyed chamfered prism, material: MAT_PLASTIC_NATURAL, color: yellow-or-natural, features: ["corner chamfer 1.85 placeholder"]}
- Dimensions M-L, geometry L, materials L. Resolved: pitch 7.2 read in an opened document (twice). Unresolved: whether 0.6 x 1.7 or dia 2.7 is the power-pin hole, locating-feature positions, chamfer size, polarity, pin diameter. Validation: pitch 7.2 < width 15.5; XT60 profile ratio 15.5:8.4 matches the XT30 9.9:5.0 interpretation (0.54 vs 0.51). Sheet not cross-checked by a second document (KiCad XT60PW footprint URLs 404), so confidence capped at M-L.
  
  
  
  ---
- COSMETIC_PROVISIONAL wall=1.05: One eighth body height inward, leaves keyed shroud within sourced body.
- COSMETIC_PROVISIONAL bullet_diameter=2.8000000000000003: Internal mating bullet diameter one third body height; board tail shape and coordinates unchanged.
- COSMETIC_PROVISIONAL recess_depth=6.066666666666666: Front recess one third sourced length, within housing.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-175 — source partial

- 3 terminals. Pad centers (FCO, M): SIG (-1.05, 0) size 1.05 x 1.0; GND1 (+0.475, +1.475) and GND2 (+0.475, -1.475) size 2.2 x 1.05. Replaces the first-pass placeholders (GND at +-1.1 X, SIG at -Y). Terminal tails are the flat pad undersides at Z=0.
- Dimensions M, geometry M-L, materials M. Resolved: pad coordinates (two sources agree on 2.2, 1.9 gap, 4.0 span), 1.9 = mated height, 4.0x2.2 = land pattern. Unresolved: body orientation relative to pads comes from KiCad (Hirose drawing not viewed); body X offset +0.475 is derived, not drawn; mask opening assignment; shell fillets. Validation: ground pad inner gap 2*0.95 = 1.9 and outer span 4.0 match two callouts; pad bbox centered on origin; body 3.0 x 2.6 fits between land edges.
  
  
  
  ---
- COSMETIC_PROVISIONAL base_fraction=0.25: Base/flange occupies lower quarter of sourced height; total height unchanged.
- COSMETIC_PROVISIONAL dielectric_ratio=0.6: Dielectric opening 60 percent of interface diameter, inside metal ring.
- COSMETIC_PROVISIONAL socket_ratio=0.2: Female recess 20 percent of interface diameter, inside dielectric.
- COSMETIC_PROVISIONAL thread_depth=0.025: Cosmetic thread recess one eightieth diameter, never outside barrel envelope.
- COSMETIC_PROVISIONAL pad_thickness=0.0625: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-176 — source partial

- overall_height: 9.52 (MFR_DATASHEET/L)
- flange_square: 7.0 (UNCERTAIN/L)
- Thread dia 6.35 (1/4-36 UNS, DERIVED, M); hex across flats 7.87 (Molex drawing; Cinch listing 7.92) (M-L); overall height 9.52 (Cinch 142-0701-201 listing "9.52 x 7.92", interpretation, L-M; first-pass placeholder was 9.0); flange/body 7.0 x 7.0 (KiCad Amphenol 132134 fab outline, L); no vertical-SMA drawing text could be read (image-only). Basis S4/S5, confidence L-M.
- 5 pins: center signal (0,0), hole dia 1.5, and 4 ground legs at (+-2.54,+-2.54), hole dia 1.7 (two KiCad Amphenol footprints agree, M-L). Pin/leg tail shape: round dia 1.0 PLACEHOLDER (tail cross-section not read).
- Dimensions L-M, geometry L, materials M. Resolved: leg pattern (+-2.54 square, two KiCad files), hole sizes 1.5/1.7, thread, hex, height (single retailer figure). Unresolved: no opened drawing (image-only PDFs); height 9.52 and flange 7.0 are interpretations of a retailer string and a KiCad fab outline; leg cross-section; which manufacturer part the default represents (Cinch 142-0701-201 height vs Amphenol 132134 pattern: cross-manufacturer mixing flagged). Validation: 4 legs inside the 7.0 flange; hex 7.87 > thread 6.35; pattern identical in two KiCad files.
  
  
  
  ---
- COSMETIC_PROVISIONAL base_fraction=0.25: Base/flange occupies lower quarter of sourced height; total height unchanged.
- COSMETIC_PROVISIONAL dielectric_ratio=0.6: Dielectric opening 60 percent of interface diameter, inside metal ring.
- COSMETIC_PROVISIONAL socket_ratio=0.2: Female recess 20 percent of interface diameter, inside dielectric.
- COSMETIC_PROVISIONAL thread_depth=0.079375: Cosmetic thread recess one eightieth diameter, never outside barrel envelope.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-177 — source partial

- overall_height: 7.87 (UNCERTAIN/L)
- Board edge at Y=+2.7825 (FCO frame), equal to the front edge of the pads and of the rear block. Barrel overhang = 12.45 (derived, L-M; replaces the placeholder 11). Origin = bbox center of pad pattern (X +-4.825; before the shift the pad Y extent was -3.47..+2.095, center -0.6875; all coordinates shown are already shifted). Body spans Y -1.0275..+15.2325, body_offset (0,+7.10). Board thickness slot 1.57 (2.13 on another Molex part). Board top at Z=0, so the body is centered in Z about the board center: slot axis Z about -0.79 (RESEARCH_REQUIRED, the center contact lies on top copper so the barrel axis height above Z=0 is not read).
- Dimensions M-L, geometry M-L, materials M. Resolved: pad pattern and center tab width 1.78 (two sources), overhang 12.45, block depth 3.81. Unresolved: Z height/axis height (no callout identified; 7.87 envelope is a placeholder), 4.32 reference, mixing of Molex 73251-2120 footprint with the EWR-2074 drawing of 0732512121 (same series, flagged). Validation: KiCad outline reproduces 16.26 and 6.35; block front = pad front edge = board edge closes the 12.45 overhang; pad bbox centered on origin.
- Dimensions M-L, geometry M-L, materials M. Resolved: pad pattern and center tab width 1.78 (two sources), overhang 12.45, block depth 3.81. Unresolved: Z height/axis height (no callout identified; 7.87 envelope is a placeholder), 4.32 reference, mixing of Molex 73251-2120 footprint with the EWR-2074 drawing of 0732512121 (same series, flagged). Validation: KiCad outline reproduces 16.26 and 6.35; block front = pad front edge = board edge closes the 12.45 overhang; pad bbox centered on origin.
  
  
  
  ---
- COSMETIC_PROVISIONAL base_fraction=0.25: Base/flange occupies lower quarter of sourced height; total height unchanged.
- COSMETIC_PROVISIONAL dielectric_ratio=0.6: Dielectric opening 60 percent of interface diameter, inside metal ring.
- COSMETIC_PROVISIONAL socket_ratio=0.2: Female recess 20 percent of interface diameter, inside dielectric.
- COSMETIC_PROVISIONAL thread_depth=0.079375: Cosmetic thread recess one eightieth diameter, never outside barrel envelope.
- COSMETIC_PROVISIONAL pad_thickness=0.15: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-178 — source complete

- Dimensions M, geometry L-M, materials M. Resolved: pad row Y offset, pad length 1.3, tab pads 1.8 x 2.2 at +-4.15 (N=10), body depth. Unresolved (not blocking): actuator/tab 3D detail not read; pin-1 side from library convention, not the Hirose drawing; tab-pad x rule for N other than 10 is one data point. Validation: A,B,C formulas reproduce every opened value (N=6,10,16,20); KiCad outline +-4.05 = B/2 and 5.6 depth agree with datasheet values; pad bbox centered on origin; 10 pads x 0.5 pitch span 4.5 inside B=8.1.
  
  
  
  ---
- COSMETIC_PROVISIONAL slot_height=0.5: FPC opening one quarter body height, inside housing.
- COSMETIC_PROVISIONAL actuator_depth=1.4: Rear flip bar occupies one quarter body depth, separate sub-body.
- COSMETIC_PROVISIONAL pad_thickness=0.1: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-179 — source partial

- overall_length: 30.5 (MFR_DATASHEET/L)
- overall_width: 27.9 (MFR_DATASHEET/L)
- Molex 67600-8001: 27.9 (X, across) x 30.5 (Y, insertion axis; assignment of the two RS figures to axes is an assumption) x 2.8 (Z). Basis S4 (RS listing), confidence L-M. Slot opening is not sourced: PLACEHOLDER 24.5 wide x 2.3 high (derived from the 24 x 2.1 mm card, common knowledge, not an opened document). First-pass placeholders 27.0 x 31.0 x 3.0 superseded.
- 9 contacts in one row near the rear, 0.8 (X) x 2.0 (Y) pads. X pattern (FCO, L; exemplar from the Kyocera 145638009211859+ KiCad footprint, S5, because the card pad layout is fixed by the card standard; Molex pad geometry not read): pad 1..9 at X = -7.065, -4.565, -1.265, +0.435, +2.935, +5.435, +7.865, +9.565, -9.565, Y=0. Pad 9 is the outer pad on the -X side. Molex RS listing pitch strings "1.625 x 2 mm, 2.5 x 7 mm" are not reconciled. Shell ground tabs/locator posts: RESEARCH_REQUIRED (Molex lists "locator posts"); detect/write-protect switch pads not modeled.
- SMD; origin here = bbox center of the 9-contact row only (shell tabs and locator posts are not included, so FCO is provisional). body_offset (0, +13.75) PLACEHOLDER: body rear edge assumed 1.5 behind the contact row (Kyocera exemplar: 1.25), body center = -1.5 + 30.5/2; overhang 0.
- Dimensions L-M (height M, X/Y L-M with an axis assumption), geometry L, materials M. Resolved: a genuine full-size SD part (Molex 67600-8001) with envelope 27.9 x 30.5 x 2.8 and 9 circuits. Unresolved: axis assignment of 27.9/30.5; Molex pad geometry and positions (exemplar from Kyocera); shell tabs, locator posts, slot opening; drawing PDF image-only. Validation: 9 pads span 19.1 inside 27.9; height 2.8 > 2.1 mm card plus shell; 24 mm card fits across 27.9.
  
  
  
  ---
- COSMETIC_PROVISIONAL wall=0.2333333333333333: Sheet stock one twelfth envelope height, entirely inward.
- COSMETIC_PROVISIONAL base_height=0.7: Plastic support lower quarter of envelope.
- COSMETIC_PROVISIONAL contact_reach=10.166666666666666: Internal spring reach one third envelope length; PCB pad centers unchanged.
- COSMETIC_PROVISIONAL pad_thickness=0.13999999999999999: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

### OHM-180 — source partial

- overall_width: 11.4 (MFR_DATASHEET/L)
- overall_length: 11.95 (MFR_DATASHEET/L)
- SMD; origin bbox center of pads and shell tabs (X +-6.34, Y -5.45..+5.45 after shift: contact row at Y=-4.9, shield pads to Y=+4.95). body_offset (0, +1.0) PLACEHOLDER: rear edge location relative to the contact row not read; overhang 0.
- Dimensions L-M, geometry L-M, materials M. Resolved: pad coordinates (KiCad, same part), default part now single-manufacturer-part consistent, height conflict 1.42 vs 1.57 documented. Unresolved: body 11.4 x 11.95 vs KiCad 13.68 x 16.25 outline (shield tabs/card overhang), rear edge position, mirrored shield pads, drawing PDFs image-only. Validation: 8 pads at 1.1 pitch fit within 11.4; pad bbox centered on origin; pin-1 rotation delta recorded.
  
  
  
  ---
- COSMETIC_PROVISIONAL wall=0.11833333333333333: Sheet stock one twelfth envelope height, entirely inward.
- COSMETIC_PROVISIONAL base_height=0.355: Plastic support lower quarter of envelope.
- COSMETIC_PROVISIONAL contact_reach=3.983333333333333: Internal spring reach one third envelope length; PCB pad centers unchanged.
- COSMETIC_PROVISIONAL pad_thickness=0.071: Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged.
- COSMETIC_PROVISIONAL detail_ratios={'shield_stock': 0.8, 'locator_tail': 0.5, 'tongue_strip_width': 0.45, 'tongue_strip_length': 0.7, 'tongue_strip_center': 0.4, 'jack_cavity_center': 0.55, 'jack_strip_length': 0.75, 'bullet_length': 0.8, 'bullet_center': 0.6, 'zif_slot_width': 0.8, 'zif_slot_depth': 0.5, 'actuator_height': 0.4}: Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged.
- Spec-only dimensional and appearance defaults; unsourced cosmetic details remain provisional.

## Every COSMETIC_PROVISIONAL value

| Entry | Feature | Value used (mm unless a count, color or ratio) | Derivation |
|---|---|---|---|
| OHM-015 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-015 | mark_diameter | 1.2 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-016 | mark_height_fraction | 0.65 | Front-face pin1 dot at 65 percent of body height, within sourced envelope. |
| OHM-016 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-016 | mark_diameter | 0.22 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-017 | pad_stock | 0.03 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-017 | mark_diameter | 0.10666666666666667 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-018 | rotor_depth | 0.73 | Recess within upper fifth of housing, limited by rotor diameter/3. |
| OHM-018 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-018 | mark_diameter | 0.322 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-019 | rotor_depth | 0.51 | Recess within upper fifth of housing, limited by rotor diameter/3. |
| OHM-019 | slot_depth | 0.255 | One tenth housing height; inward rotor slot only. |
| OHM-019 | pad_stock | 0.1275 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-019 | mark_diameter | 0.3 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-020 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-020 | mark_diameter | 1.0666666666666667 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-044 | pad_stock | 0.051000000000000004 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-044 | marker_diameter | 0.2 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-044 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-044 | label_size | [0.9,0.28] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-045 | pad_stock | 0.13999999999999999 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-045 | marker_diameter | 0.44666666666666666 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-045 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-045 | label_size | [3.65,1.675] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-046 | visual_terminal_size | [2,2] | Use stated width (2.0, 1.25 or 0.30); remaining visual extent uses square width for drum/CMC or twice width for LAN foot. Contact centers unchanged; no land-pattern claim. |
| OHM-046 | flange_height | 0.7999999999999999 | Each flange occupies one sixth sourced height. |
| OHM-046 | barrel_diameter | 3.77 | 65 percent sourced flange diameter, inside envelope. |
| OHM-046 | winding_diameter | 4.93 | 85 percent flange diameter, inside sourced cylinder. |
| OHM-046 | pad_stock | 0.2 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-046 | marker_diameter | 0.38666666666666666 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-046 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-046 | label_size | [2.9,1.45] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-048 | dome_height | 0.6 | Shallow rounded cap inside final 12 mm height, one twentieth height. |
| OHM-048 | pad_stock | 0.2 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-048 | marker_diameter | 0.58 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-048 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-048 | label_size | [4.35,2.175] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-049 | pad_stock | 0.2 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-049 | marker_diameter | 1.456 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-049 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-049 | label_size | [10.92,5.46] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-050 | visual_terminal_size | [1.25,1.25] | Use stated width (2.0, 1.25 or 0.30); remaining visual extent uses square width for drum/CMC or twice width for LAN foot. Contact centers unchanged; no land-pattern claim. |
| OHM-050 | pad_stock | 0.2 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-050 | marker_diameter | 0.58 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-050 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-050 | label_size | [5,2.175] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-051 | pad_stock | 0.2 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-051 | marker_diameter | 0.52 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-051 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-051 | label_size | [7.9,1.95] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-052 | pad_stock | 0.2 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-052 | marker_diameter | 1.1866666666666668 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-052 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-052 | label_size | [8.9,5.15] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-053 | visual_pin_diameter | 0.5 | One fifth of stated provisional 2.5 mm pitch, visual stock only; no hole diameter or footprint claim. Within body XY envelope. |
| OHM-053 | bobbin_base | 1.71125 | Lower eighth of sourced height; full sourced plan envelope. |
| OHM-053 | flange_stock | 1.6155000000000002 | One twentieth sourced X envelope; two inner flanges, do not move pin rows. |
| OHM-053 | core_width | 24.2325 | 75 percent X envelope, bounded by bobbin flanges; no EFD core datasheet dimension asserted. |
| OHM-053 | core_length | 24.327 | 90 percent Y envelope, inside sourced envelope. |
| OHM-053 | core_stock | 2.738 | Core rails and center leg stock one fifth overall height. |
| OHM-053 | tape_width | 12.1635 | Tape winding band 45 percent body Y span, inside core window. |
| OHM-053 | pad_stock | 0.2 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-053 | marker_diameter | 1.802 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-053 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-053 | label_size | [16.155,6.7575] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-054 | pad_stock | 0.2 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-054 | marker_diameter | 0.6353333333333333 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-054 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-054 | label_size | [8.6,2.3825] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-055 | visual_terminal_size | [0.6,0.3] | Use stated width (2.0, 1.25 or 0.30); remaining visual extent uses square width for drum/CMC or twice width for LAN foot. Contact centers unchanged; no land-pattern claim. |
| OHM-055 | pad_stock | 0.2 | Metal visual stock one twentieth height capped0.2, contact plane unchanged. |
| OHM-055 | marker_diameter | 0.6353333333333333 | OHM-044 stated0.2; otherwise one fifteenth smaller face dimension for library pin1 decal. |
| OHM-055 | winding_turns | 8 | Eight purely visual winding stripes within existing winding envelope; no electrical turn-count claim. |
| OHM-055 | label_size | [4.765,3.175] | Optional separate label decal occupies half X and quarter Y of top face. |
| OHM-087 | face_depth | 0.1 | Entry approximate 0.1 recess; plate partition within sourced body height. |
| OHM-087 | digit_layout | {"horizontal_bias":-0.06,"dp_x":0.38,"dp_y":-0.43,"bar_y":0.43,"vertical_x":0.24,"vertical_y":0.215,"bar_length":0.48,"vertical_length":0.32} | Dimensionless proportions of sourced digit height, inside digit cell; preserves entry UP=+X and lower-right DP. Bias leaves room for DP inside 12.7 mm single-digit face. |
| OHM-087 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-087 | mark_diameter | 0.8466666666666666 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-088 | face_depth | 0.1 | Entry approximate 0.1 recess; plate partition within sourced body height. |
| OHM-088 | digit_layout | {"horizontal_bias":-0.06,"dp_x":0.38,"dp_y":-0.43,"bar_y":0.43,"vertical_x":0.24,"vertical_y":0.215,"bar_length":0.48,"vertical_length":0.32} | Dimensionless proportions of sourced digit height, inside digit cell; preserves entry UP=+X and lower-right DP. Bias leaves room for DP inside 12.7 mm single-digit face. |
| OHM-088 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-088 | mark_diameter | 1.27 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-089 | face_depth | 0.1 | Entry approximate 0.1 recess; plate partition within sourced body height. |
| OHM-089 | digit_layout | {"horizontal_bias":-0.06,"dp_x":0.38,"dp_y":-0.43,"bar_y":0.43,"vertical_x":0.24,"vertical_y":0.215,"bar_length":0.48,"vertical_length":0.32} | Dimensionless proportions of sourced digit height, inside digit cell; preserves entry UP=+X and lower-right DP. Bias leaves room for DP inside 12.7 mm single-digit face. |
| OHM-089 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-089 | mark_diameter | 1.2666666666666666 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-090 | face_depth | 0.1 | Entry approximate 0.1 recess; plate partition within sourced body height. |
| OHM-090 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-090 | mark_diameter | 2.1333333333333333 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-091 | bezel_stock | 0.32999999999999996 | Inward bezel stock one fortieth total height, top remains13.2. |
| OHM-091 | polarizer_inset | 0.132 | Polarizer recessed one hundredth total height below bezel. |
| OHM-091 | pcb_color | #2F4F3A | Section7 FR4 color is variable; borrow supplied BGA substrate green / supplied plastic blue hue, keeping FR4 roughness0.5. Appearance default only. |
| OHM-091 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-091 | mark_diameter | 2.4 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-092 | pcb_color | #1E5AA8 | Section7 FR4 color is variable; borrow supplied BGA substrate green / supplied plastic blue hue, keeping FR4 roughness0.5. Appearance default only. |
| OHM-092 | pad_stock | 0.15 | Visual metal stock no more than 5 percent height or0.15; contact planes unchanged. |
| OHM-092 | mark_diameter | 1.8 | Optional pin1 dot one fifteenth smaller body dimension, within face. |
| OHM-141 | radius | 2.325 | HC49 full-radius ends from half width; resonator 0.8 top radius stated in entry. |
| OHM-141 | seal_diameter | 1.29 | Three times stated lead diameter, inside bottom plate. |
| OHM-141 | seam_width | 0.09300000000000001 | One fiftieth of can width; surface seam inside top envelope. |
| OHM-141 | label_width | 5.940000000000001 | 55 percent of sourced body length; optional identity decal. |
| OHM-141 | label_height | 0.93 | One fifth of smaller face dimension. |
| OHM-142 | radius | 2.325 | HC49 full-radius ends from half width; resonator 0.8 top radius stated in entry. |
| OHM-142 | seal_diameter | 1.29 | Three times stated lead diameter, inside bottom plate. |
| OHM-142 | seam_width | 0.09300000000000001 | One fiftieth of can width; surface seam inside top envelope. |
| OHM-142 | label_width | 6.077500000000001 | 55 percent of sourced body length; optional identity decal. |
| OHM-142 | label_height | 0.7 | One fifth of smaller face dimension. |
| OHM-143 | pad_thickness | 0.02 | Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged. |
| OHM-143 | base_fraction | 0.7 | Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope. |
| OHM-143 | lid_inset | 0.1 | Entry lid inset; SAW borrows oscillator seam inset. |
| OHM-143 | marker_radius | 0.1 | One twenty-fifth of smaller body dimension; lid corner mark only. |
| OHM-143 | lid_chamfer | 0.25 | One tenth of smaller dimension, removes material at marked corner only. |
| OHM-143 | label_width | 1.6 | Half of body length, inside lid. |
| OHM-143 | label_height | 0.5 | One fifth of body width, inside lid. |
| OHM-144 | pad_thickness | 0.02 | Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged. |
| OHM-144 | base_fraction | 0.7 | Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope. |
| OHM-144 | lid_inset | 0.1 | Entry lid inset; SAW borrows oscillator seam inset. |
| OHM-144 | marker_radius | 0.08 | One twenty-fifth of smaller body dimension; lid corner mark only. |
| OHM-144 | lid_chamfer | 0.2 | One tenth of smaller dimension, removes material at marked corner only. |
| OHM-144 | label_width | 1.25 | Half of body length, inside lid. |
| OHM-144 | label_height | 0.4 | One fifth of body width, inside lid. |
| OHM-145 | pad_thickness | 0.02 | Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged. |
| OHM-145 | base_fraction | 0.7 | Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope. |
| OHM-145 | lid_inset | 0.1 | Entry lid inset; SAW borrows oscillator seam inset. |
| OHM-145 | marker_radius | 0.064 | One twenty-fifth of smaller body dimension; lid corner mark only. |
| OHM-145 | lid_chamfer | 0.16 | One tenth of smaller dimension, removes material at marked corner only. |
| OHM-145 | label_width | 1 | Half of body length, inside lid. |
| OHM-145 | label_height | 0.32 | One fifth of body width, inside lid. |
| OHM-146 | pad_thickness | 0.02 | Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged. |
| OHM-146 | base_fraction | 0.65 | Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope. |
| OHM-146 | lid_inset | 0.15 | Entry lid inset; SAW borrows oscillator seam inset. |
| OHM-146 | marker_radius | 0.2 | One twenty-fifth of smaller body dimension; lid corner mark only. |
| OHM-146 | lid_chamfer | 0.5 | One tenth of smaller dimension, removes material at marked corner only. |
| OHM-146 | label_width | 3.5 | Half of body length, inside lid. |
| OHM-146 | label_height | 1 | One fifth of body width, inside lid. |
| OHM-147 | pad_thickness | 0.02 | Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged. |
| OHM-147 | base_fraction | 0.65 | Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope. |
| OHM-147 | lid_inset | 0.15 | Entry lid inset; SAW borrows oscillator seam inset. |
| OHM-147 | marker_radius | 0.1 | One twenty-fifth of smaller body dimension; lid corner mark only. |
| OHM-147 | lid_chamfer | 0.25 | One tenth of smaller dimension, removes material at marked corner only. |
| OHM-147 | label_width | 1.6 | Half of body length, inside lid. |
| OHM-147 | label_height | 0.5 | One fifth of body width, inside lid. |
| OHM-148 | radius | 0.8 | HC49 full-radius ends from half width; resonator 0.8 top radius stated in entry. |
| OHM-148 | seal_diameter | 1.44 | Three times stated lead diameter, inside bottom plate. |
| OHM-148 | seam_width | 0.07 | One fiftieth of can width; surface seam inside top envelope. |
| OHM-148 | label_width | 4.4 | 55 percent of sourced body length; optional identity decal. |
| OHM-148 | label_height | 0.7 | One fifth of smaller face dimension. |
| OHM-149 | pad_thickness | 0.02 | Use stated 0.02 mm on 143-145; same family cosmetic metal depth on remaining SMD entries. PCB-contact XY and Z=0 unchanged. |
| OHM-149 | base_fraction | 0.65 | Entry ceramic/lid split: 70 percent for crystals, 65 percent for oscillators; SAW borrows oscillator construction within envelope. |
| OHM-149 | lid_inset | 0.15 | Entry lid inset; SAW borrows oscillator seam inset. |
| OHM-149 | marker_radius | 0.152 | One twenty-fifth of smaller body dimension; lid corner mark only. |
| OHM-149 | lid_chamfer | 0.38 | One tenth of smaller dimension, removes material at marked corner only. |
| OHM-149 | label_width | 1.9 | Half of body length, inside lid. |
| OHM-149 | label_height | 0.76 | One fifth of body width, inside lid. |
| OHM-156 | slot_depth | 2 | Borrow OHM-155 PH slot depth; remains inside 7 mm XH body. |
| OHM-157 | end_wall | 0.9 | (6.0 mm default body length - 4.2 mm cavity)/2; fixed end allowance for N variants. |
| OHM-157 | top_wall | 0.5 | Borrow OHM-155 shroud wall; within BM04B 2.9 mm depth. |
| OHM-158 | floor | 1 | One sixth of the stated 6 mm housing height; connects walls without changing outer envelope. |
| OHM-158 | end_wall | 0.6 | Reuse the stated open-side stub thickness for end walls, inside row envelope. |
| OHM-158 | ramp_count | 1 | One centered ramp retained for N variants; source gives one for N=2 and no N>2 rule. |
| OHM-159 | window_depth | 3.266666666666667 | One third of stated housing depth; internal recess only. |
| OHM-159 | screw_head_height | 0.5 | Half the pocket depth; head stays recessed. |
| OHM-159 | slot_width | 0.375 | One eighth of specified/placeholder 3 mm head diameter. |
| OHM-159 | slot_length | 2.4000000000000004 | 80 percent of head diameter; slot stays inside head. |
| OHM-160 | window_depth | 3.266666666666667 | One third of stated housing depth; internal recess only. |
| OHM-160 | screw_head_height | 0.5 | Half the pocket depth; head stays recessed. |
| OHM-160 | slot_width | 0.375 | One eighth of specified/placeholder 3 mm head diameter. |
| OHM-160 | slot_length | 2.4000000000000004 | 80 percent of head diameter; slot stays inside head. |
| OHM-161 | wall | 0.5 | Borrow OHM-155 0.5 mm shroud wall; keep header outer envelope fixed. |
| OHM-161 | internal_pin_z | 4.3 | Half of 8.6 mm header height; PCB pin axes unchanged. |
| OHM-161 | internal_pin_end | 8.5 | Header front X=9.0 minus cosmetic wall; inside header. |
| OHM-161 | screw_x | 9.85 | Center of specified plug X extent; Y positions follow pitch. |
| OHM-161 | pocket_depth | 1.075 | One eighth of header height, recessed into plug. |
| OHM-161 | window_width | 3.3866666666666667 | Two thirds of sourced contact pitch, centered on each row position. |
| OHM-161 | window_height | 2.8666666666666667 | One third of header height, inside 15 mm plug. |
| OHM-161 | window_z | 5 | One third of plug height; does not alter plug envelope. |
| OHM-161 | window_depth | 3 | One quarter of header depth, recessed from plug +X face. |
| OHM-161 | screw_head_height | 0.5375 | Half the pocket depth; head stays recessed. |
| OHM-161 | slot_width | 0.375 | One eighth of specified/placeholder 3 mm head diameter. |
| OHM-161 | slot_length | 2.4000000000000004 | 80 percent of head diameter; slot stays inside head. |
| OHM-162 | wall | 0.29 | One twentieth of smaller shell face dimension, inward from sourced outer envelope. |
| OHM-162 | tongue_recess | 0.5 | Front recess bounded by one tenth of sourced length and 0.5 mm. |
| OHM-162 | contact_visual_height | 0.057999999999999996 | One hundredth shell height; internal mating strips only. |
| OHM-162 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-162 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-163 | wall | 0.545 | One twentieth of smaller shell face dimension, inward from sourced outer envelope. |
| OHM-163 | cavity | [10.91,9.81,13.12] | Outer face minus twice cosmetic wall; cavity depth 80 percent of body length. |
| OHM-163 | tongue | [8.728,2.4525] | 80 percent of cavity width and one quarter of cavity height, inside opening. |
| OHM-163 | tongue_recess | 0.5 | Front recess bounded by one tenth of sourced length and 0.5 mm. |
| OHM-163 | contact_visual_height | 0.109 | One hundredth shell height; internal mating strips only. |
| OHM-163 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-163 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-164 | wall | 0.143 | One twentieth of smaller shell face dimension, inward from sourced outer envelope. |
| OHM-164 | tongue | [5.48,0.45] | 80 percent of cavity width and one quarter of cavity height, inside opening. |
| OHM-164 | tongue_recess | 0.5 | Front recess bounded by one tenth of sourced length and 0.5 mm. |
| OHM-164 | contact_visual_height | 0.0286 | One hundredth shell height; internal mating strips only. |
| OHM-164 | pad_thickness | 0.143 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-164 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-165 | wall | 0.16299999999999998 | One twentieth of smaller shell face dimension, inward from sourced outer envelope. |
| OHM-165 | tongue_recess | 0.5 | Front recess bounded by one tenth of sourced length and 0.5 mm. |
| OHM-165 | contact_visual_height | 0.0326 | One hundredth shell height; internal mating strips only. |
| OHM-165 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-165 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-166 | wall | 0.2 | One twentieth of smaller shell face dimension, inward from sourced outer envelope. |
| OHM-166 | chamfer | 0.8 | One fifth face height, inward corner removal. |
| OHM-166 | cavity | [7.3,3.6,7.4] | Outer face minus twice cosmetic wall; cavity depth 80 percent of body length. |
| OHM-166 | tongue | [5.84,0.9] | 80 percent of cavity width and one quarter of cavity height, inside opening. |
| OHM-166 | tongue_recess | 0.5 | Front recess bounded by one tenth of sourced length and 0.5 mm. |
| OHM-166 | contact_visual_height | 0.04 | One hundredth shell height; internal mating strips only. |
| OHM-166 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-166 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-167 | wall | 0.325 | One twentieth of smaller shell face dimension, inward from sourced outer envelope. |
| OHM-167 | chamfer | 1.3 | One fifth face height, inward corner removal. |
| OHM-167 | cavity | [13.35,5.85,11.920000000000002] | Outer face minus twice cosmetic wall; cavity depth 80 percent of body length. |
| OHM-167 | tongue | [10.68,1.4625] | 80 percent of cavity width and one quarter of cavity height, inside opening. |
| OHM-167 | tongue_recess | 0.5 | Front recess bounded by one tenth of sourced length and 0.5 mm. |
| OHM-167 | contact_visual_height | 0.065 | One hundredth shell height; internal mating strips only. |
| OHM-167 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-167 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-168 | contact_visual_width | 0.2 | Half stated 0.4 pitch; visual terminal width only, no footprint binding; row positions unchanged. |
| OHM-168 | wall | 0.15 | One twentieth of smaller shell face dimension, inward from sourced outer envelope. |
| OHM-168 | chamfer | 0.6 | One fifth face height, inward corner removal. |
| OHM-168 | tongue | [8.336,0.605] | 80 percent of cavity width and one quarter of cavity height, inside opening. |
| OHM-168 | tongue_recess | 0.5 | Front recess bounded by one tenth of sourced length and 0.5 mm. |
| OHM-168 | contact_visual_height | 0.03 | One hundredth shell height; internal mating strips only. |
| OHM-168 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-168 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-169 | tail_visual_width | 0.45 | Visual tail stock below the stated 0.76 mm RJ45 hole; RJ11 borrows sibling stock. Hole positions unchanged, no drill inference. |
| OHM-169 | latch | [4.446,1.5875] | Latch width 38 percent cavity width, depth one eighth housing height; inward removal. |
| OHM-169 | internal_contact | [0.4875,0.127] | Internal spring strip width from cavity/contact count; height 1 percent envelope. |
| OHM-169 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-169 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-170 | tail_visual_width | 0.45 | Visual tail stock below the stated 0.76 mm RJ45 hole; RJ11 borrows sibling stock. Hole positions unchanged, no drill inference. |
| OHM-170 | latch | [3.8,1.65] | Latch width 38 percent cavity width, depth one eighth housing height; inward removal. |
| OHM-170 | internal_contact | [0.8333333333333334,0.132] | Internal spring strip width from cavity/contact count; height 1 percent envelope. |
| OHM-170 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-170 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-171 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-171 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-172 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-172 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-173 | wall | 0.625 | One eighth body height inward, leaves keyed shroud within sourced body. |
| OHM-173 | bullet_diameter | 1.6666666666666667 | Internal mating bullet diameter one third body height; board tail shape and coordinates unchanged. |
| OHM-173 | recess_depth | 4.6499999999999995 | Front recess one third sourced length, within housing. |
| OHM-173 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-173 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-174 | wall | 1.05 | One eighth body height inward, leaves keyed shroud within sourced body. |
| OHM-174 | bullet_diameter | 2.8000000000000003 | Internal mating bullet diameter one third body height; board tail shape and coordinates unchanged. |
| OHM-174 | recess_depth | 6.066666666666666 | Front recess one third sourced length, within housing. |
| OHM-174 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-174 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-175 | base_fraction | 0.25 | Base/flange occupies lower quarter of sourced height; total height unchanged. |
| OHM-175 | dielectric_ratio | 0.6 | Dielectric opening 60 percent of interface diameter, inside metal ring. |
| OHM-175 | socket_ratio | 0.2 | Female recess 20 percent of interface diameter, inside dielectric. |
| OHM-175 | thread_depth | 0.025 | Cosmetic thread recess one eightieth diameter, never outside barrel envelope. |
| OHM-175 | pad_thickness | 0.0625 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-175 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-176 | base_fraction | 0.25 | Base/flange occupies lower quarter of sourced height; total height unchanged. |
| OHM-176 | dielectric_ratio | 0.6 | Dielectric opening 60 percent of interface diameter, inside metal ring. |
| OHM-176 | socket_ratio | 0.2 | Female recess 20 percent of interface diameter, inside dielectric. |
| OHM-176 | thread_depth | 0.079375 | Cosmetic thread recess one eightieth diameter, never outside barrel envelope. |
| OHM-176 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-176 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-177 | base_fraction | 0.25 | Base/flange occupies lower quarter of sourced height; total height unchanged. |
| OHM-177 | dielectric_ratio | 0.6 | Dielectric opening 60 percent of interface diameter, inside metal ring. |
| OHM-177 | socket_ratio | 0.2 | Female recess 20 percent of interface diameter, inside dielectric. |
| OHM-177 | thread_depth | 0.079375 | Cosmetic thread recess one eightieth diameter, never outside barrel envelope. |
| OHM-177 | pad_thickness | 0.15 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-177 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-178 | slot_height | 0.5 | FPC opening one quarter body height, inside housing. |
| OHM-178 | actuator_depth | 1.4 | Rear flip bar occupies one quarter body depth, separate sub-body. |
| OHM-178 | pad_thickness | 0.1 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-178 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-179 | wall | 0.2333333333333333 | Sheet stock one twelfth envelope height, entirely inward. |
| OHM-179 | base_height | 0.7 | Plastic support lower quarter of envelope. |
| OHM-179 | contact_reach | 10.166666666666666 | Internal spring reach one third envelope length; PCB pad centers unchanged. |
| OHM-179 | pad_thickness | 0.13999999999999999 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-179 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |
| OHM-180 | wall | 0.11833333333333333 | Sheet stock one twelfth envelope height, entirely inward. |
| OHM-180 | base_height | 0.355 | Plastic support lower quarter of envelope. |
| OHM-180 | contact_reach | 3.983333333333333 | Internal spring reach one third envelope length; PCB pad centers unchanged. |
| OHM-180 | pad_thickness | 0.071 | Visual metal thickness no more than 5 percent body height or 0.15; pad contact planes and XY unchanged. |
| OHM-180 | detail_ratios | {"shield_stock":0.8,"locator_tail":0.5,"tongue_strip_width":0.45,"tongue_strip_length":0.7,"tongue_strip_center":0.4,"jack_cavity_center":0.55,"jack_strip_length":0.75,"bullet_length":0.8,"bullet_center":0.6,"zif_slot_width":0.8,"zif_slot_depth":0.5,"actuator_height":0.4} | Dimensionless appearance ratios applied only inside sourced housing or supplied mounting-hole outline. Internal metal X coordinates follow the terminal records; PCB coordinates and pin numbering remain unchanged. |

## Coverage

| Entry | Family | Member | Generator | LOD | Source status | Implementation | Provisional |
|---|---|---|---|---|---|---|---|
| OHM-001 | PKG-CHIP2T | 01005I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-002 | PKG-CHIP2T | 0201I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-003 | PKG-CHIP2T | 0402I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-004 | PKG-CHIP2T | 0603I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-005 | PKG-CHIP2T | 0805I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-006 | PKG-CHIP2T | 1206I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-007 | PKG-CHIP2T | 1210I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-008 | PKG-CHIP2T | 2010I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-009 | PKG-CHIP2T | 2512I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-010 | PKG-AXIAL_RES | AX_1_4W | GEN-AXIAL | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-011 | PKG-AXIAL_RES | AX_1_4W | GEN-AXIAL | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-012 | PKG-POWER_RES | CEM_5W | GEN-AXIAL | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-013 | PKG-POWER_RES | RS005 | GEN-AXIAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-014 | PKG-CHIP2T | 2512I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-015 | PKG-SHUNT | BOLT_ON_60 | GEN-SIP | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-016 | PKG-SIP_NET | SIP_8 | GEN-SIP | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-017 | PKG-CHIP_ARRAY | YC164 | GEN-CHIP_ARRAY | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-018 | PKG-TRIMMER | 3296W | GEN-POT | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-019 | PKG-TRIMMER_SMD | 3314G | GEN-POT | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-020 | PKG-POT_ROTARY | RV16 | GEN-POT | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-021 | PKG-CHIP2T | 0201I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-022 | PKG-CHIP2T | 0402I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-023 | PKG-CHIP2T | 0603I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-024 | PKG-CHIP2T | 0805I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-025 | PKG-CHIP2T | 1206I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-026 | PKG-CHIP2T | 1210I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-027 | PKG-CHIP2T | 1812I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-028 | PKG-DISC_CAP | D7_P5_placeholder | GEN-RADIAL_FILM | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-029 | PKG-RADIAL_CAN | 10x16 | GEN-RADIAL_CAN | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-030 | PKG-SMD_CAN | D8 | GEN-SMD_CAN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-031 | PKG-SNAPIN_CAN | 25x40_2pin | GEN-RADIAL_CAN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-032 | PKG-SMD_CAN | D8_polymer | GEN-SMD_CAN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-033 | PKG-TANT_MOLDED | A | GEN-TANT_MOLDED | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-034 | PKG-TANT_MOLDED | B | GEN-TANT_MOLDED | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-035 | PKG-TANT_MOLDED | C | GEN-TANT_MOLDED | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-036 | PKG-TANT_MOLDED | D | GEN-TANT_MOLDED | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-037 | PKG-FILM_BOX | P10.0 | GEN-RADIAL_FILM | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-038 | PKG-FILM_BOX | P15.0 | GEN-RADIAL_FILM | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-039 | PKG-MICA | CD15 | GEN-RADIAL_FILM | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-040 | PKG-SUPERCAP | AVX_SCC_10x20 | GEN-RADIAL_CAN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-041 | PKG-CHIP2T | 0603I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-042 | PKG-CHIP2T | 0805I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-043 | PKG-CHIP2T | 1206I | GEN-CHIP_2T | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-044 | PKG-SMD_IND_WW | 0603CS | GEN-SMD_INDUCTOR | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-045 | PKG-SMD_POWER_IND | SRP7028A | GEN-SMD_INDUCTOR | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-046 | PKG-SMD_POWER_IND | SDR0604 | GEN-SMD_INDUCTOR | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-047 | PKG-AXIAL_IND | 78F | GEN-AXIAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-048 | PKG-DRUM_IND | RLB0914 | GEN-SMD_INDUCTOR | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-049 | PKG-TOROID | 2107 | GEN-SMD_INDUCTOR | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-050 | PKG-CMC_SMD | WE-SL5 | GEN-SMD_INDUCTOR | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-051 | PKG-CMC_THT | 744821240 | GEN-SMD_INDUCTOR | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-052 | PKG-XFMR_SIGNAL | TY-145P | GEN-TRANSFORMER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-053 | PKG-XFMR_EE | EFD25_WE-FB | GEN-TRANSFORMER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-054 | PKG-XFMR_CT | AS | GEN-TRANSFORMER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-055 | PKG-MAGNETICS_SMD | H1102 | GEN-TRANSFORMER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-056 | PKG-DO_AXIAL | DO-35 | GEN-AXIAL | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-057 | PKG-DO_AXIAL | DO-41 | GEN-AXIAL | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-058 | PKG-DO_AXIAL | DO-201AD | GEN-AXIAL | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-059 | PKG-MELF | MiniMELF | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-060 | PKG-MELF | MELF | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-061 | PKG-SOD | SOD123 | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-062 | PKG-SOD | SOD323 | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-063 | PKG-SOD | SOD523 | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-064 | PKG-SMX | SMA | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-065 | PKG-SMX | SMB | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-066 | PKG-SMX | SMC | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-067 | PKG-SOD | SOD123 | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-068 | PKG-SOD | SOD123 | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-069 | PKG-SMX | SMB | GEN-SMD_DIODE | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-070 | PKG-SOT23 | SOT23-3 (owned by G07) | GEN-SMD_POWER | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-071 | PKG-BRIDGE_DIP | DB-1/DFM | GEN-BRIDGE | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-072 | PKG-BRIDGE_ROUND | WOG/WOM | GEN-BRIDGE | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-073 | PKG-LED_THT | 3MM | GEN-LED_THT | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-074 | PKG-LED_THT | 5MM | GEN-LED_THT | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-075 | PKG-LED_THT | 10MM | GEN-LED_THT | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-076 | PKG-LED_THT | RECT | GEN-LED_THT | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-077 | PKG-LED_CHIP | 0402I | GEN-LED_CHIP | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-078 | PKG-LED_CHIP | 0603I | GEN-LED_CHIP | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-079 | PKG-LED_CHIP | 0805I | GEN-LED_CHIP | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-080 | PKG-LED_CHIP | 1206I | GEN-LED_CHIP | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-081 | PKG-PLCC_LED | PLCC2_3528 | GEN-LED_CHIP | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-082 | PKG-PLCC_LED | PLCC4_3528_RGB | GEN-LED_CHIP | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-083 | PKG-LED_5050 | RGB5050_PLCC6 | GEN-LED_CHIP | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-084 | PKG-LED_5050 | WS2812B | GEN-LED_CHIP | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-085 | PKG-LED_POWER | XP-E2 | GEN-LED_POWER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-086 | PKG-LED_STAR | STAR20 | GEN-LED_STAR | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-087 | PKG-7SEG | 7SEG.056x1 | GEN-7SEG | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-088 | PKG-7SEG | 7SEG.056x2 | GEN-7SEG | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-089 | PKG-7SEG | 7SEG.056x4 | GEN-7SEG | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-090 | PKG-LED_MATRIX | 8x8_32 | GEN-7SEG | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-091 | PKG-LCD_CHARACTER | LCM1602.std | GEN-MODULE | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-092 | PKG-OLED_MODULE | OLED096.27 | GEN-MODULE | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-093 | PKG-TO92 | TO92_straight | GEN-TO_LEADED | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-094 | PKG-SOT23 | SOT23-3 | GEN-SMD_POWER | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-095 | PKG-SOT89 | SOT89-3 | GEN-SMD_POWER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-096 | PKG-SOT223 | SOT223-4 | GEN-SMD_POWER | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-097 | PKG-TO126 | TO126-3 | GEN-TO_LEADED | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-098 | PKG-TO220 | TO220-3 | GEN-TO_LEADED | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-099 | PKG-TO247 | TO247-3 | GEN-TO_LEADED | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-100 | PKG-DPAK | DPAK-3 | GEN-SMD_POWER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-101 | PKG-D2PAK | D2PAK-3 | GEN-SMD_POWER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-102 | PKG-POWERPAK | PowerPAK_SO8_single | GEN-SMD_POWER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-103 | PKG-DIP | DIP-6 | GEN-DIP | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-104 | PKG-DIP | DIP-8 | GEN-DIP | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-105 | PKG-DIP | DIP-14 | GEN-DIP | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-106 | PKG-DIP | DIP-16 | GEN-DIP | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-107 | PKG-DIP | DIP-20 | GEN-DIP | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-108 | PKG-DIP | DIP-28 | GEN-DIP | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-109 | PKG-DIP | DIP-40 | GEN-DIP | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-110 | PKG-SOIC | SOIC-8 | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-111 | PKG-SOIC | SOIC-14 | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-112 | PKG-SOIC | SOIC-16 | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-113 | PKG-SOIC | SOIC-20W | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-114 | PKG-TSSOP | TSSOP-8 | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-115 | PKG-TSSOP | TSSOP-14 | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-116 | PKG-TSSOP | TSSOP-16 | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-117 | PKG-TSSOP | TSSOP-20 | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-118 | PKG-SSOP | SSOP-16 5.3mm | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-119 | PKG-MSOP | MSOP-8 | GEN-DUAL_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-120 | PKG-SOT23 | SOT-23-5 | GEN-SMD_POWER | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-121 | PKG-SOT23 | SOT-23-6 | GEN-SMD_POWER | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-122 | PKG-QFP | QFP-32 | GEN-QUAD_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-123 | PKG-QFP | TQFP-44 | GEN-QUAD_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-124 | PKG-QFP | TQFP-64 | GEN-QUAD_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-125 | PKG-QFP | TQFP-100 | GEN-QUAD_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-126 | PKG-QFP | LQFP-144 | GEN-QUAD_GULLWING | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-127 | PKG-QFN | QFN-16 | GEN-QFN | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-128 | PKG-QFN | QFN-20 | GEN-QFN | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-129 | PKG-QFN | QFN-24 | GEN-QFN | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-130 | PKG-QFN | QFN-32 | GEN-QFN | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-131 | PKG-QFN | QFN-48 | GEN-QFN | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-132 | PKG-DFN | DFN-6 | GEN-QFN | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-133 | PKG-DFN | DFN-8 | GEN-QFN | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-134 | PKG-DFN | WSON-8 | GEN-QFN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-135 | PKG-PLCC | PLCC28 | GEN-PLCC | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-136 | PKG-BGA | BGA-64 | GEN-BGA | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-137 | PKG-BGA | BGA-100 | GEN-BGA | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-138 | PKG-BGA | BGA-256 | GEN-BGA | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-139 | PKG-WLCSP | WLCSP-9 | GEN-BGA | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-140 | PKG-WLCSP | WLCSP-16 | GEN-BGA | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | no |
| OHM-141 | PKG-XTAL_HC49 | HC49.U | GEN-XTAL | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-142 | PKG-XTAL_HC49 | HC49.S | GEN-XTAL | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-143 | PKG-XTAL_SMD | 3225 | GEN-XTAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-144 | PKG-XTAL_SMD | 2520 | GEN-XTAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-145 | PKG-XTAL_SMD | 2016 | GEN-XTAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-146 | PKG-OSC_SMD | 7050 | GEN-XTAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-147 | PKG-OSC_SMD | 3225 | GEN-XTAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-148 | PKG-RESONATOR_3PIN | CSTLS_G | GEN-XTAL | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-149 | PKG-SAW_SMD | 3838 | GEN-XTAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-150 | PKG-HDR_PIN | 1xN_STRAIGHT_2.54 | GEN-HEADER | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-151 | PKG-HDR_PIN | 2xN_STRAIGHT_2.54 | GEN-HEADER | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-152 | PKG-HDR_SOCKET | 1xN_2.54 | GEN-HEADER | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-153 | PKG-HDR_SOCKET | 2xN_2.54 | GEN-HEADER | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-154 | PKG-HDR_PIN | RA_1xN_2.54 | GEN-HEADER | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-155 | PKG-JST_PH | B2B-PH-K-S | GEN-WIRE_CONN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-156 | PKG-JST_XH | B2B-XH-A | GEN-WIRE_CONN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-157 | PKG-JST_SH | SM04B-SRSS-TB | GEN-WIRE_CONN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-158 | PKG-MOLEX_KK | 22-23-2021 | GEN-WIRE_CONN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-159 | PKG-SCREW_TERM | MKDS_1.5_2P_5.08 | GEN-TERMINAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-160 | PKG-SCREW_TERM | MKDS_1.5_3P_5.08 | GEN-TERMINAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-161 | PKG-PLUG_TERM | MSTBA_2.5_2P_5.08 | GEN-TERMINAL | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-162 | PKG-USB_A | RA_THT | GEN-USB | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-163 | PKG-USB_B | RA_THT | GEN-USB | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-164 | PKG-USB_MICRO | AMPH_10118194 | GEN-USB | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-165 | PKG-USB_C | AMPH_12401610E4 | GEN-USB | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-166 | PKG-USB_MINI | WURTH_65100516121 | GEN-USB | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-167 | PKG-HDMI | CT_19APL2 | GEN-HDMI | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-168 | PKG-HDMI_MINI | TYPE_C_SMT_RA | GEN-HDMI | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-169 | PKG-RJ45 | AMPH_54602 | GEN-MODULAR_JACK | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-170 | PKG-RJ11 | 6P4C_TAB_DOWN | GEN-MODULAR_JACK | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-171 | PKG-AUDIO_JACK | LEDINO_KB3SPRS | GEN-AUDIO_DC | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-172 | PKG-DC_JACK | PJ-102A | GEN-AUDIO_DC | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-173 | PKG-XT | XT30PW-M | GEN-POWER_CONN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-174 | PKG-XT | XT60PW-M | GEN-POWER_CONN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-175 | PKG-UFL | U.FL-R-SMT-1 | GEN-RF_CONN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-176 | PKG-SMA_RF | vertical_jack | GEN-RF_CONN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-177 | PKG-SMA_EDGE | EWR-2074 | GEN-RF_CONN | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-178 | PKG-FFC_ZIF | FH12-10S-0.5SH | GEN-CARD_FFC | LOD0/LOD1/LOD2 | complete | IMPLEMENTED | yes |
| OHM-179 | PKG-SD_SOCKET | Molex_67600-8001 | GEN-CARD_FFC | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |
| OHM-180 | PKG-MICROSD_SOCKET | 104031-0811 | GEN-CARD_FFC | LOD0/LOD1/LOD2 | partial | IMPLEMENTED | yes |

