// Reference-inspired art direction, never CircuitIR, board geometry or electrical evidence.
// Source image coordinates are private-reference locators; all scene positions below
// are separately authored normalized composition choices. No pixel deprojection.
import { VISUAL_SOURCE_HASH } from './visual-version.js';

export const REFERENCE_LABEL = "Reference-inspired educational model · not an electrically verified design";
export const REFERENCE_EDUCATION_NOTICE = "General educational explanation; this image does not establish the part's electrical function.";
export const REFERENCE_INVENTORY_METADATA = Object.freeze({
    schemaVersion: 1,
    namespace: "ohmni:illustrative-reference:v1",
    visualProvenance: "ILLUSTRATIVE_ONLY",
    sourceImageSha256: "30cc966fcc367d91563782b3b411cd941daf181d174447e17dbbe0f18c37e207",
    sourceInventorySha256: "0f1b3518a71d8300d119b5c38b8c95f225f0a198857ed4794a67b8c4410bcf31",
    sourceSizePx: Object.freeze([1500, 853]),
    inventoryEntryCount: 158,
    illustrativeBodyCount: 124,
    independentPassiveBodyCount: 54,
    passiveSubdetailCount: 9,
    sourceImageDistribution: "PRIVATE_REFERENCE_ONLY",
    sourceIdentity: "UNKNOWN",
    layoutBasis: "Artist-authored normalized positions; no image-to-PCB transformation",
    dimensionalSource: "ARTISTIC_SAMPLE_DIMENSIONS",
    modelSource: "Original procedural project source in visual-assets.js",
    modelLicense: "UNSPECIFIED",
});

export const VISUAL_REGIONS = Object.freeze([
    { id: "rear", name: "Rear: tall components", description: "Navy cans, metal blocks, a coil-like form and orange coating.", bounds: [0.20, 0.03, 0.88, 0.36] },
    { id: "left", name: "Left: chips and small parts", description: "Several leaded packages, silver cans and a blue passive bank.", bounds: [0.03, 0.10, 0.38, 0.77] },
    { id: "center", name: "Center: the largest chip", description: "A dominant square package and surrounding leaded components.", bounds: [0.34, 0.34, 0.74, 0.78] },
    { id: "right", name: "Right: connector details", description: "Black strips, a metal shell and grouped blue and beige bodies.", bounds: [0.69, 0.16, 0.97, 0.94] },
    { id: "front", name: "Front: contacts and colored parts", description: "Long contact strips, silver cans and a row of banded bodies.", bounds: [0.04, 0.70, 0.86, 0.97] },
]);

function freezeDeep(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
        Object.values(value).forEach(freezeDeep);
        Object.freeze(value);
    }
    return value;
}

// Lessons explain families, not the unknown reference circuit's behavior.
export const FAMILY_LESSONS = freezeDeep({
    qfp: { name: "Leaded integrated-circuit package", general: "An integrated circuit puts many electronic elements inside one package. Bent metal leads connect the package to a board.", inspect: "Look for the resin edge, individual bent leads, their flat feet and the small mold mark.", unknown: "The device identity, electrical function, pin count and pin assignments in the source image are unknown." },
    small_outline: { name: "Two-sided leaded package", general: "Small-outline packages place metal leads along two sides of an insulated body. Many different circuits use this shape.", inspect: "Follow a lead from its shoulder through the bend to its solder foot.", unknown: "This silhouette does not identify a processor, memory, amplifier or other electrical role." },
    few_terminal: { name: "Unidentified small package", general: "Small semiconductor packages can hold different electronic devices. The terminals connect the enclosed device to a board.", inspect: "Compare the dark package body with its separate metallic terminals.", unknown: "Device type and terminal function are unknown; the displayed terminal count is an illustration choice." },
    leadless_block: { name: "Unidentified flat package", general: "Some electronic packages place large terminals at their edges or underneath, so they show few visible leads.", inspect: "Look at the low body and edge terminals rather than assuming a particular component type.", unknown: "The source does not establish whether this form is a diode, oscillator, IC or another device." },
    header: { name: "Multiway connector strip", general: "A connector housing holds separated metal contacts so a board can connect to other hardware.", inspect: "Look inside the recessed housing for the individual gold-colored contacts and their spacing.", unknown: "Mating type, gender, contact count, pitch and signal assignments are not established by the source image." },
    white_connector: { name: "White connector-like housing", general: "Insulated connector housings organize contacts and help guide a mating part into place.", inspect: "Find the cavity, sidewalls, molded retention details and inner contacts.", unknown: "Connector series, mating interface and electrical purpose remain unknown." },
    shielded_connector: { name: "Unidentified metal connector shell", general: "A metal shell can protect a mating interface and can provide shielding when designed and connected for that purpose.", inspect: "Find the two top apertures, folded shell, dark front opening and mounting feet.", unknown: "The protocol, connector identity, grounding and electrical shielding behavior are unknown. This is not identified as USB or HDMI." },
    rear_metal_block: { name: "Unidentified rear metal body", general: "Metal enclosures can have mechanical, thermal or electrical roles; a silhouette alone cannot establish which applies.", inspect: "Compare the silver outside face and inset panel with the nearby plastic packages.", unknown: "Whether the original is a port, shield, heatsink or other object is unknown; hidden fins and pins have not been invented." },
    aluminum_can: { name: "Silver capacitor-like can", general: "Capacitors store electric charge. Some capacitor packages use metal cans, but a can's appearance does not establish its value or circuit role.", inspect: "Find the aluminum wall, rolled rim, inset top and dark base; compare the different sizes.", unknown: "Capacitance, voltage rating, chemistry, polarity and actual electrical identity are not known from this source." },
    electrolytic_can: { name: "Navy sleeved capacitor-like can", general: "Many electrolytic capacitors use a colored sleeve around a metal can and are used where a circuit needs charge storage.", inspect: "Notice the separate sleeve, exposed lid, top rim and height variation.", unknown: "The reference value, polarity, rating and function are unknown. Any sample sleeve marks are illustrative." },
    wound_inductor: { name: "Coil-like component", general: "A wound inductor stores energy in a magnetic field when current flows through its winding.", inspect: "Look for the individual winding turns and how their material differs from the core.", unknown: "This object's actual type, inductance, current rating and circuit role are unknown." },
    coated_radial: { name: "Unidentified orange radial form", general: "An insulating coating protects some small two-terminal components. Shape and color alone cannot settle their function.", inspect: "Look at the rounded coated body and the supporting leads below it.", unknown: "The component subtype, value, polarity and function are unknown; orange does not establish tantalum chemistry." },
    gold_post: { name: "Unidentified gold-colored post", general: "Post-like hardware can form terminals, mechanical features or parts of a connector, depending on the actual design.", inspect: "Find the stem, collar and dark base as separate shapes.", unknown: "No test-point, signal, voltage, ground or adjustment role is established for this post." },
    axial_resistor: { name: "Banded resistor-like body", general: "A resistor opposes current flow. Some axial resistor families encode resistance with colored bands, when the actual bands and coding standard are known.", inspect: "Inspect the cylindrical body, circumferential bands, two bent wires and solder feet.", unknown: "These sample bands are illustrative and must not be decoded as a value. The reference value and circuit role are unknown." },
    coated_axial: { name: "Unidentified blue coated body", general: "Axial parts have connections emerging from opposite ends. Different electrical components can share a coated axial shape.", inspect: "Compare its unbanded blue coating and rounded body with the neighboring banded forms.", unknown: "Color and shape do not establish whether this reference part is a resistor, capacitor or another device." },
    ceramic_chip: { name: "Unidentified beige two-terminal body", general: "Ceramic or coated two-terminal packages can have several functions. Metal ends or wires attach the body to a circuit.", inspect: "Compare flat chip forms and rounded beige forms, including their metal terminations.", unknown: "The source does not establish exact component type, value or role for this beige form." },
    coated_red: { name: "Unidentified red coated body", general: "A colored coating protects an electronic body. Red coating does not by itself mean a component emits light.", inspect: "Find the non-glowing red coating, dark sides and metallic connections.", unknown: "Diode, capacitor, indicator and polarity interpretations remain unresolved." },
    unresolved_patch: { name: "Unresolved small-detail region", general: "At this image resolution, small bodies, leads, solder and printed marks can overlap.", inspect: "This patch is represented approximately without inventing extra components.", unknown: "The number, identity, boundaries and electrical purpose of the tiny source features are unknown." },
});

const SOURCE_ITEMS = [
    {"id":"IC01","observation":"Large central square black package with fine silver leads around its perimeter and circular orientation marks","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[779,292],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"IC02","observation":"Horizontal rectangular multi-lead package below the short rear-left header","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[529,229],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"IC03","observation":"Horizontal multi-lead package immediately in front of the tall blue capacitors","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[692,169],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"IC04","observation":"Rectangular multi-lead package inside the upper-right headers","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[956,211],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"IC05","observation":"Upright rectangular multi-lead package directly left of the large central package","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[607,315],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"IC06","observation":"Horizontal multi-lead package below the central package","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[717,437],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"IC07","observation":"Horizontal multi-lead package above the front-right long header","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[972,434],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"IC08","observation":"Upright multi-lead package in the upper-left interior","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[365,286],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"IC09","observation":"Upright multi-lead package halfway down the left interior","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[425,387],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"IC10","observation":"Upright multi-lead package in the lower-left interior","familyInference":"Integrated-circuit package; exact device, lead count and function unknown","confidence":"High for body; unknown electrical identity","sourceFamily":"qfp_or_small_outline","imagePointPx":[542,496],"sourceNotes":"Use separate leaded-package families; do not label every IC a processor."},
    {"id":"S01","observation":"Small black package behind the upper-left main IC, left of its neighboring small black package","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[296,213],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S02","observation":"Small black package beside IC-small 01 near the white rear-left connector","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[338,201],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S03","observation":"Small horizontal black package between left header and upper-left main IC","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[245,291],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S04","observation":"Small black horizontal body below the left header, just above the left silver-can trio","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[323,420],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S05","observation":"Partly obscured small black body behind/left of the silver-can cluster","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[252,442],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S06","observation":"Small square black body between the left silver cans","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[350,444],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S07","observation":"Small multi-lead package near the front-left mounting hole, farther from the hole","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[440,676],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S08","observation":"Small multi-lead package near the front-left mounting hole, nearer the hole","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[473,726],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S09","observation":"Small multi-lead package immediately right of the large white front-left connector","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[482,608],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S10","observation":"Larger lead-poor black rectangle above the front-left silver can","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[550,604],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S11","observation":"Small multi-lead package between the front silver-can pair and long front header","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[711,543],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S12","observation":"Small multi-lead package above the right end of the long front header","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[887,515],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S13","observation":"Small low black body below the coil, inward from rear-right header","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[866,129],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S14","observation":"Small black body between coil-side passives and rear-right header","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[878,99],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S15","observation":"Adjacent small elongated black body along the rear-right header support cluster","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[887,111],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S16","observation":"Horizontal black package below the long right header","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[1029,281],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S17","observation":"Small multi-lead black package inward from the metal connector, upper one","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[967,302],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S18","observation":"Small multi-lead black package inward from the metal connector, lower one","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[992,327],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S19","observation":"Flat rectangular black package between front-right header and right corner","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[1240,432],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"S20","observation":"Long narrow marked black package directly behind the left end of the long front header","familyInference":"Small IC / transistor / diode / oscillator-like package; function unresolved","confidence":"Medium; partly occluded for S05","sourceFamily":"small_semiconductor","imagePointPx":[654,620],"sourceNotes":"Do not infer amplifier, memory, regulator, crystal or protection role from body alone."},
    {"id":"H01","observation":"Long black shrouded pin strip along the left edge","familyInference":"Multiway shrouded pin-header/connector form; exact mating type and pin count unknown","confidence":"High for six connector bodies","sourceFamily":"shrouded_header","imagePointPx":[205,337],"sourceNotes":"Visible gold contacts inside black walls; do not claim female sockets or a particular pin count."},
    {"id":"H02","observation":"Short black shrouded pin strip on the rear-left edge","familyInference":"Multiway shrouded pin-header/connector form; exact mating type and pin count unknown","confidence":"High for six connector bodies","sourceFamily":"shrouded_header","imagePointPx":[477,154],"sourceNotes":"Visible gold contacts inside black walls; do not claim female sockets or a particular pin count."},
    {"id":"H03","observation":"Medium black pin strip on the rear-right edge, closer to rear corner","familyInference":"Multiway shrouded pin-header/connector form; exact mating type and pin count unknown","confidence":"High for six connector bodies","sourceFamily":"shrouded_header","imagePointPx":[967,107],"sourceNotes":"Visible gold contacts inside black walls; do not claim female sockets or a particular pin count."},
    {"id":"H04","observation":"Long black pin strip farther down the right edge","familyInference":"Multiway shrouded pin-header/connector form; exact mating type and pin count unknown","confidence":"High for six connector bodies","sourceFamily":"shrouded_header","imagePointPx":[1126,226],"sourceNotes":"Visible gold contacts inside black walls; do not claim female sockets or a particular pin count."},
    {"id":"H05","observation":"Longest foreground pin strip across the lower edge","familyInference":"Multiway shrouded pin-header/connector form; exact mating type and pin count unknown","confidence":"High for six connector bodies","sourceFamily":"shrouded_header","imagePointPx":[803,620],"sourceNotes":"Visible gold contacts inside black walls; do not claim female sockets or a particular pin count."},
    {"id":"H06","observation":"Separate long pin strip across the lower-right edge","familyInference":"Multiway shrouded pin-header/connector form; exact mating type and pin count unknown","confidence":"High for six connector bodies","sourceFamily":"shrouded_header","imagePointPx":[1103,493],"sourceNotes":"Visible gold contacts inside black walls; do not claim female sockets or a particular pin count."},
    {"id":"J01","observation":"Small white connector body at the rear-left edge","familyInference":"White wire-to-board connector-like housing","confidence":"Medium","sourceFamily":"white_connector","imagePointPx":[237,210],"sourceNotes":""},
    {"id":"J02","observation":"Large white/light-gray rectangular connector at the lower-left edge","familyInference":"Shrouded connector-like housing; protocol and receptacle type unknown","confidence":"Medium","sourceFamily":"white_connector","imagePointPx":[375,576],"sourceNotes":""},
    {"id":"J03","observation":"Large silver rectangular shell with two dark circular apertures on top and a dark front opening","familyInference":"Metal-shielded connector-like body; not positively USB/HDMI/Ethernet/audio","confidence":"Medium for shell; low for function","sourceFamily":"shielded_connector","imagePointPx":[1109,395],"sourceNotes":""},
    {"id":"J04","observation":"Tall silver rectangular body at rear edge, left of matching tall silver body","familyInference":"Metal-bodied port/shield/heatsink-like object; silhouette insufficient to decide","confidence":"Low for function","sourceFamily":"ambiguous_metal_block","imagePointPx":[580,96],"sourceNotes":""},
    {"id":"J05","observation":"Second tall silver rectangular body at rear edge","familyInference":"Metal-bodied port/shield/heatsink-like object; silhouette insufficient to decide","confidence":"Low for function","sourceFamily":"ambiguous_metal_block","imagePointPx":[660,71],"sourceNotes":""},
    {"id":"C01","observation":"Upper-left large silver can beside rear-left white connector","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[211,235],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C02","observation":"Smaller silver can just right of the upper-left large can","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[282,249],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C03","observation":"Rear silver can of a close pair beside the short rear-left header","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[371,167],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C04","observation":"Front silver can of that close pair","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[393,200],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C05","observation":"Silver can beside upper-left main IC and left header","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[352,336],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C06","observation":"Leftmost can of the mid-left lower trio","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[295,452],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C07","observation":"Lower/front can of the mid-left trio","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[383,469],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C08","observation":"Right can of the mid-left trio","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[435,446],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C09","observation":"Left/front can of the pair beside IC10","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[602,573],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C10","observation":"Right/rear can of the pair beside IC10","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[654,544],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C11","observation":"Left/front can under IC06","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[758,508],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C12","observation":"Right/rear can under IC06","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[808,482],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C13","observation":"Small silver can behind the metal connector","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[1152,322],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C14","observation":"Larger silver can to the right of the metal connector","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[1270,346],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"C15","observation":"Large silver can near the front-left mounting hole","familyInference":"Aluminum-can capacitor form; chemistry, value and rating unknown","confidence":"High for visible can; medium for capacitor class","sourceFamily":"aluminum_can","imagePointPx":[555,705],"sourceNotes":"Black base, silver sidewall/top, pale top markings; some top patches may be markings rather than vents."},
    {"id":"E01","observation":"Nearest/front tall navy can beside J04","familyInference":"Sleeved radial electrolytic-style capacitor","confidence":"High for capacitor-like form; value unknown","sourceFamily":"radial_electrolytic","imagePointPx":[583,151],"sourceNotes":"Dark navy/purple sleeve, silver top, cylindrical wall and bottom lip."},
    {"id":"E02","observation":"Second tall navy can beside J05","familyInference":"Sleeved radial electrolytic-style capacitor","confidence":"High for capacitor-like form; value unknown","sourceFamily":"radial_electrolytic","imagePointPx":[679,100],"sourceNotes":"Dark navy/purple sleeve, silver top, cylindrical wall and bottom lip."},
    {"id":"E03","observation":"Third tall navy can toward the rear edge","familyInference":"Sleeved radial electrolytic-style capacitor","confidence":"High for capacitor-like form; value unknown","sourceFamily":"radial_electrolytic","imagePointPx":[743,49],"sourceNotes":"Dark navy/purple sleeve, silver top, cylindrical wall and bottom lip."},
    {"id":"E04","observation":"Fourth tall navy can, cropped by the top edge","familyInference":"Sleeved radial electrolytic-style capacitor","confidence":"High for capacitor-like form; value unknown","sourceFamily":"radial_electrolytic","imagePointPx":[801,25],"sourceNotes":"Dark navy/purple sleeve, silver top, cylindrical wall and bottom lip."},
    {"id":"L01","observation":"Single reddish-brown ribbed cylinder at the far/rear corner","familyInference":"Wound inductor/choke-like form, not electrically identified","confidence":"Medium","sourceFamily":"wound_inductor","imagePointPx":[852,37],"sourceNotes":"Visible stacked winding-like ridges; do not label voltage/current/function."},
    {"id":"O01","observation":"Orange upright cylindrical/rounded body in front of rear blue capacitors","familyInference":"Capacitor-like or other coated radial component; exact type unresolved","confidence":"Low","sourceFamily":"coated_radial","imagePointPx":[775,102],"sourceNotes":"Must remain unknown radial part in reference inspection, not definitely tantalum/electrolytic."},
    {"id":"T01","observation":"Slender gold post between rear capacitor group","familyInference":"Gold post / test terminal / adjustable hardware-like form; role unknown","confidence":"Medium for form; low for function","sourceFamily":"gold_post","imagePointPx":[718,107],"sourceNotes":"Some silhouettes could be contacts or adjusters. No testpoint net/name can be recovered from the screenshot."},
    {"id":"T02","observation":"Lower gold post in front of the same group","familyInference":"Gold post / test terminal / adjustable hardware-like form; role unknown","confidence":"Medium for form; low for function","sourceFamily":"gold_post","imagePointPx":[723,132],"sourceNotes":"Some silhouettes could be contacts or adjusters. No testpoint net/name can be recovered from the screenshot."},
    {"id":"T03","observation":"Gold post above the upper-right main IC","familyInference":"Gold post / test terminal / adjustable hardware-like form; role unknown","confidence":"Medium for form; low for function","sourceFamily":"gold_post","imagePointPx":[885,174],"sourceNotes":"Some silhouettes could be contacts or adjusters. No testpoint net/name can be recovered from the screenshot."},
    {"id":"T04","observation":"Gold post beside upper-left main IC","familyInference":"Gold post / test terminal / adjustable hardware-like form; role unknown","confidence":"Medium for form; low for function","sourceFamily":"gold_post","imagePointPx":[397,335],"sourceNotes":"Some silhouettes could be contacts or adjusters. No testpoint net/name can be recovered from the screenshot."},
    {"id":"T05","observation":"Gold post beside mid-left main IC","familyInference":"Gold post / test terminal / adjustable hardware-like form; role unknown","confidence":"Medium for form; low for function","sourceFamily":"gold_post","imagePointPx":[490,423],"sourceNotes":"Some silhouettes could be contacts or adjusters. No testpoint net/name can be recovered from the screenshot."},
    {"id":"T06","observation":"Gold post next to front-left white connector","familyInference":"Gold post / test terminal / adjustable hardware-like form; role unknown","confidence":"Medium for form; low for function","sourceFamily":"gold_post","imagePointPx":[468,575],"sourceNotes":"Some silhouettes could be contacts or adjusters. No testpoint net/name can be recovered from the screenshot."},
    {"id":"T07","observation":"Gold post between front-center can cluster and small IC","familyInference":"Gold post / test terminal / adjustable hardware-like form; role unknown","confidence":"Medium for form; low for function","sourceFamily":"gold_post","imagePointPx":[848,486],"sourceNotes":"Some silhouettes could be contacts or adjusters. No testpoint net/name can be recovered from the screenshot."},
    {"id":"T08","observation":"Gold post next to right metal connector and silver can","familyInference":"Gold post / test terminal / adjustable hardware-like form; role unknown","confidence":"Medium for form; low for function","sourceFamily":"gold_post","imagePointPx":[1208,379],"sourceNotes":"Some silhouettes could be contacts or adjusters. No testpoint net/name can be recovered from the screenshot."},
    {"id":"P01","observation":"blue small passive body near (432, 197)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[432,197],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P02","observation":"tan small passive body near (456, 191)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[456,191],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P03","observation":"blue small passive body near (480, 184)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[480,184],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P04","observation":"tan small passive body near (503, 177)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[503,177],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P05","observation":"blue small passive body near (526, 171)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[526,171],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P06","observation":"banded blue small passive body near (307, 239)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[307,239],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P07","observation":"banded blue small passive body near (348, 225)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[348,225],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P08","observation":"banded blue small passive body near (263, 309)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[263,309],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P09","observation":"banded blue small passive body near (280, 328)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[280,328],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P10","observation":"banded blue small passive body near (293, 346)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[293,346],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P11","observation":"banded blue small passive body near (300, 362)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[300,362],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P12","observation":"red small passive body near (320, 352)","familyInference":"Red coated small two-terminal component; diode/capacitor/indicator role unresolved","confidence":"Low for subtype","sourceFamily":"coated_red","imagePointPx":[320,352],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P13","observation":"tan small passive body near (572, 269)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[572,269],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P14","observation":"blue small passive body near (593, 255)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[593,255],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P15","observation":"tan small passive body near (616, 241)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[616,241],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P16","observation":"tan small passive body near (659, 226)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[659,226],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P17","observation":"blue small passive body near (703, 226)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[703,226],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P18","observation":"banded blue small passive body near (722, 215)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[722,215],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P19","observation":"blue small passive body near (766, 205)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[766,205],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P20","observation":"blue small passive body near (856, 68)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[856,68],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P21","observation":"banded blue small passive body near (877, 80)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[877,80],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P22","observation":"blue small passive body near (904, 144)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[904,144],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P23","observation":"banded blue small passive body near (923, 153)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[923,153],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P24","observation":"blue small passive body near (854, 229)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[854,229],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P25","observation":"banded blue small passive body near (878, 246)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[878,246],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P26","observation":"tan small passive body near (896, 264)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[896,264],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P27","observation":"banded blue small passive body near (1026, 315)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[1026,315],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P28","observation":"banded blue small passive body near (1043, 308)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[1043,308],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P29","observation":"banded blue small passive body near (1058, 301)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[1058,301],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P30","observation":"banded blue small passive body near (1075, 295)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[1075,295],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P31","observation":"tan small passive body near (1066, 330); body/end-pad separation is ambiguous in this patch","familyInference":"Small passive or its terminal/band; not safe to count independently","confidence":"Unresolved body boundary","sourceFamily":"passive_subdetail","imagePointPx":[1066,330],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P32","observation":"tan small passive body near (1016, 329); body/end-pad separation is ambiguous in this patch","familyInference":"Small passive or its terminal/band; not safe to count independently","confidence":"Unresolved body boundary","sourceFamily":"passive_subdetail","imagePointPx":[1016,329],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P33","observation":"tan small passive body near (918, 317)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[918,317],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P34","observation":"blue small passive body near (931, 328)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[931,328],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P35","observation":"tan small passive body near (941, 338)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[941,338],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P36","observation":"tan small passive body near (949, 348)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[949,348],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P37","observation":"banded blue small passive body near (1218, 326)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[1218,326],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P38","observation":"banded blue small passive body near (1233, 318); body/end-pad separation is ambiguous in this patch","familyInference":"Small passive or its terminal/band; not safe to count independently","confidence":"Unresolved body boundary","sourceFamily":"passive_subdetail","imagePointPx":[1233,318],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P39","observation":"red small passive body near (1262, 305)","familyInference":"Red coated small two-terminal component; diode/capacitor/indicator role unresolved","confidence":"Low for subtype","sourceFamily":"coated_red","imagePointPx":[1262,305],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P40","observation":"banded blue small passive body near (1293, 415)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[1293,415],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P41","observation":"blue small passive body near (897, 361)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[897,361],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P42","observation":"tan small passive body near (856, 379)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[856,379],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P43","observation":"tan small passive body near (768, 374)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[768,374],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P44","observation":"red small passive body near (529, 351)","familyInference":"Red coated small two-terminal component; diode/capacitor/indicator role unresolved","confidence":"Low for subtype","sourceFamily":"coated_red","imagePointPx":[529,351],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P45","observation":"tan small passive body near (642, 398)","familyInference":"Tan/beige small two-terminal passive; capacitor/resistor subtype unresolved","confidence":"Medium for form; low for subtype","sourceFamily":"ceramic_or_axial","imagePointPx":[642,398],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P46","observation":"blue small passive body near (669, 382)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[669,382],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P47","observation":"banded blue small passive body near (696, 378)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[696,378],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P48","observation":"Tan end/band area adjacent to P47; may belong to the same axial body","familyInference":"Passive-body end/band detail; not counted as a separate component","confidence":"Unresolved body boundary","sourceFamily":"passive_subdetail","imagePointPx":[719,380],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P49","observation":"blue small passive body near (417, 522)","familyInference":"Blue axial/coated passive, possibly resistor or capacitor; function unknown","confidence":"Medium for form; low for subtype","sourceFamily":"coated_axial","imagePointPx":[417,522],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P50","observation":"banded blue small passive body near (438, 543)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[438,543],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P51","observation":"banded blue small passive body near (449, 560)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[449,560],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P52","observation":"banded tan small passive body near (503, 658)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[503,658],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P53","observation":"banded tan small passive body near (512, 682)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[512,682],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P54","observation":"banded blue small passive body near (738, 581)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[738,581],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P55","observation":"banded blue small passive body near (763, 570)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[763,570],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P56","observation":"banded blue small passive body near (789, 559)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[789,559],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P57","observation":"banded blue small passive body near (815, 548)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[815,548],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P58","observation":"banded blue small passive body near (840, 537)","familyInference":"Banded axial resistor-like passive; exact value unreadable","confidence":"Medium for resistor family; bands not decodable","sourceFamily":"axial_resistor","imagePointPx":[840,537],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P59","observation":"Tan/light terminal or band detail at the front end of P54; not a separately established component","familyInference":"End/band/solder detail associated with the resistor row, not an extra capacitor","confidence":"Visible detail; separate component NOT established","sourceFamily":"passive_subdetail","imagePointPx":[748,594],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P60","observation":"Tan/light terminal or band detail at the front end of P55; not a separately established component","familyInference":"End/band/solder detail associated with the resistor row, not an extra capacitor","confidence":"Visible detail; separate component NOT established","sourceFamily":"passive_subdetail","imagePointPx":[775,583],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P61","observation":"Tan/light terminal or band detail at the front end of P56; not a separately established component","familyInference":"End/band/solder detail associated with the resistor row, not an extra capacitor","confidence":"Visible detail; separate component NOT established","sourceFamily":"passive_subdetail","imagePointPx":[801,572],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P62","observation":"Tan/light terminal or band detail at the front end of P57; not a separately established component","familyInference":"End/band/solder detail associated with the resistor row, not an extra capacitor","confidence":"Visible detail; separate component NOT established","sourceFamily":"passive_subdetail","imagePointPx":[827,561],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"P63","observation":"Tan/light terminal or band detail at the front end of P58; not a separately established component","familyInference":"End/band/solder detail associated with the resistor row, not an extra capacitor","confidence":"Visible detail; separate component NOT established","sourceFamily":"passive_subdetail","imagePointPx":[852,550],"sourceNotes":"This is a feature-level marker, not a guaranteed extra BOM component. Some markers locate bands, terminals, or overlapping bodies; no electrical value is recovered."},
    {"id":"X01","observation":"Sub-pixel/occluded parts and shiny terminations in the row beneath the short rear-left header","familyInference":"Unresolved microdetail group; exact object count and types not recoverable","confidence":"Unresolved","sourceFamily":"unresolved_microdetail","imagePointPx":[473,205],"sourceNotes":"Do not invent a definitive component count. Render known pads/leads; keep unknown bodies explicitly illustrative in the showcase only."},
    {"id":"X02","observation":"Tiny pads, leads and possible chip passives between rear-left silver cans and small black packages","familyInference":"Unresolved microdetail group; exact object count and types not recoverable","confidence":"Unresolved","sourceFamily":"unresolved_microdetail","imagePointPx":[334,218],"sourceNotes":"Do not invent a definitive component count. Render known pads/leads; keep unknown bodies explicitly illustrative in the showcase only."},
    {"id":"X03","observation":"Tiny green/black/tan objects under coil and behind rear-right support ICs","familyInference":"Unresolved microdetail group; exact object count and types not recoverable","confidence":"Unresolved","sourceFamily":"unresolved_microdetail","imagePointPx":[855,91],"sourceNotes":"Do not invent a definitive component count. Render known pads/leads; keep unknown bodies explicitly illustrative in the showcase only."},
    {"id":"X04","observation":"Overlapping small passives above central IC fanout","familyInference":"Unresolved microdetail group; exact object count and types not recoverable","confidence":"Unresolved","sourceFamily":"unresolved_microdetail","imagePointPx":[711,222],"sourceNotes":"Do not invent a definitive component count. Render known pads/leads; keep unknown bodies explicitly illustrative in the showcase only."},
    {"id":"X05","observation":"Interleaved tiny tan parts and metallic pads in right-hand resistor bank","familyInference":"Unresolved microdetail group; exact object count and types not recoverable","confidence":"Unresolved","sourceFamily":"unresolved_microdetail","imagePointPx":[1050,317],"sourceNotes":"Do not invent a definitive component count. Render known pads/leads; keep unknown bodies explicitly illustrative in the showcase only."},
    {"id":"X06","observation":"Interleaved tiny bodies, solder fillets and printed marks beside foreground resistor bank","familyInference":"Unresolved microdetail group; exact object count and types not recoverable","confidence":"Unresolved","sourceFamily":"unresolved_microdetail","imagePointPx":[784,568],"sourceNotes":"Do not invent a definitive component count. Render known pads/leads; keep unknown bodies explicitly illustrative in the showcase only."},
    {"id":"X07","observation":"Occluded small passive/lead regions behind the large front silver can","familyInference":"Unresolved microdetail group; exact object count and types not recoverable","confidence":"Unresolved","sourceFamily":"unresolved_microdetail","imagePointPx":[528,678],"sourceNotes":"Do not invent a definitive component count. Render known pads/leads; keep unknown bodies explicitly illustrative in the showcase only."},
    {"id":"X08","observation":"Small plated holes and terminations between central lower passive trio and main IC","familyInference":"Unresolved microdetail group; exact object count and types not recoverable","confidence":"Unresolved","sourceFamily":"unresolved_microdetail","imagePointPx":[726,397],"sourceNotes":"Do not invent a definitive component count. Render known pads/leads; keep unknown bodies explicitly illustrative in the showcase only."},
    {"id":"M01","observation":"Rear-left gold-rimmed mounting hole","familyInference":"Large mechanical hole with gold-colored annulus; plating/grounding not established","confidence":"High for first three; partial for fourth","sourceFamily":"mounting_hole","imagePointPx":[137,245],"sourceNotes":"Hole diameter and electrical connection unknown. Gold color is not proof of a specified finish."},
    {"id":"M02","observation":"Front-left gold-rimmed mounting hole","familyInference":"Large mechanical hole with gold-colored annulus; plating/grounding not established","confidence":"High for first three; partial for fourth","sourceFamily":"mounting_hole","imagePointPx":[495,797],"sourceNotes":"Hole diameter and electrical connection unknown. Gold color is not proof of a specified finish."},
    {"id":"M03","observation":"Right-corner gold-rimmed mounting hole","familyInference":"Large mechanical hole with gold-colored annulus; plating/grounding not established","confidence":"High for first three; partial for fourth","sourceFamily":"mounting_hole","imagePointPx":[1358,390],"sourceNotes":"Hole diameter and electrical connection unknown. Gold color is not proof of a specified finish."},
    {"id":"M04","observation":"Partly occluded/cropped rear-corner gold-rimmed hole","familyInference":"Large mechanical hole with gold-colored annulus; plating/grounding not established","confidence":"High for first three; partial for fourth","sourceFamily":"mounting_hole","imagePointPx":[875,17],"sourceNotes":"Hole diameter and electrical connection unknown. Gold color is not proof of a specified finish."},
    {"id":"B01","observation":"Green rectangular board slab with visible near-edge thickness","familyInference":"Board substrate and solder-mask surfaces","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"board_slab","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"B02","observation":"Dark green/brown near-edge band","familyInference":"Board sidewall/substrate cross-section, not a wire","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"board_edge","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"B03","observation":"Lighter green branching fine lines between component terminals","familyInference":"Trace-like surface network; exact electrical netlist cannot be recovered","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"trace_layers","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"B04","observation":"Numerous small round holes/dots along traces","familyInference":"Via/test-pad-like features; individual connectivity unknown","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"via_and_pad","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"B05","observation":"Silver rectangular attachment lands under metal component feet","familyInference":"Solder pads and modeled solder/terminal highlights","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"solder_joint","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"B06","observation":"White/light-gray component labels, outlines and orientation marks","familyInference":"Silkscreen-style printed layer; text mostly unreadable","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"silkscreen","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"B07","observation":"Dark circles/chamfers on IC tops","familyInference":"Package orientation/mold marks, not automatically pin-1 proof","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"package_marking","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"B08","observation":"Numerous silver bent feet along black packages","familyInference":"Individual metallic leads; not separate components","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"gullwing_lead","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"B09","observation":"Recesses, gold contacts and white solder toes around headers","familyInference":"Connector subparts, not separate BOM components","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"connector_subpart","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"B10","observation":"Dark halos and grounding shadows under parts","familyInference":"Lighting/contact-shadow cues rather than engineering objects","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"contact_shadow","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"V01","observation":"Gray grid around board","familyInference":"3D editor viewport ground grid, not PCB copper","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"viewport_grid","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"V02","observation":"Axis/corner widget at lower left","familyInference":"Editor navigation overlay, not board hardware","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"viewport_axis","imagePointPx":[null,null],"sourceNotes":""},
    {"id":"V03","observation":"Orientation cube at top right","familyInference":"Editor camera gizmo, not a board component","confidence":"Visible; many repeated subfeatures cannot be counted from screenshot","sourceFamily":"viewport_gizmo","imagePointPx":[null,null],"sourceNotes":""}
];

// [ID, family, region, u, v, rotation degrees, body width, body depth,
//  total body height, options]. These are explicit illustration parameters.
const BODY_LAYOUT = [
    ["IC01","qfp","center",.575,.525,0,17,17,2.4,{leadCount:96}],
    ["IC02","small_outline","rear",.35,.33,0,16,7.5,2,{leadCount:32}],
    ["IC03","small_outline","rear",.58,.325,0,17,6.5,1.7,{leadCount:32}],
    ["IC04","small_outline","right",.78,.405,90,14,8.5,2,{leadCount:28}],
    ["IC05","small_outline","center",.405,.525,90,14,8,1.8,{leadCount:28}],
    ["IC06","small_outline","center",.555,.72,0,17,8,2.1,{leadCount:32}],
    ["IC07","small_outline","right",.72,.755,0,16,9,2.1,{leadCount:32}],
    ["IC08","small_outline","left",.205,.325,90,14,8,2,{leadCount:28}],
    ["IC09","small_outline","left",.25,.505,90,15,9,2.2,{leadCount:32}],
    ["IC10","qfp","front",.305,.69,90,15,11,2.3,{leadCount:48}],
    ["S01","few_terminal","left",.145,.115,0,3.6,2.2,1.2,{leadCount:6}],
    ["S02","small_outline","left",.20,.115,0,4.1,2.4,1.2,{leadCount:8}],
    ["S03","few_terminal","left",.105,.267,0,3.5,2.1,1.2,{leadCount:6}],
    ["S04","small_outline","left",.105,.535,0,4.4,2.5,1.3,{leadCount:8}],
    ["S05","leadless_block","left",.07,.665,90,3,2.3,1.1,{}],
    ["S06","leadless_block","left",.155,.585,0,3.7,3.1,1.3,{}],
    ["S07","small_outline","front",.085,.855,90,4.8,2.8,1.3,{leadCount:10}],
    ["S08","small_outline","front",.085,.915,90,5.1,2.8,1.4,{leadCount:10}],
    ["S09","small_outline","front",.19,.87,90,5.2,3,1.5,{leadCount:10}],
    ["S10","leadless_block","front",.255,.835,90,4.5,3.4,2,{}],
    ["S11","small_outline","front",.425,.872,0,4.6,2.8,1.4,{leadCount:8}],
    ["S12","small_outline","front",.68,.85,0,4.8,2.8,1.4,{leadCount:10}],
    ["S13","few_terminal","rear",.785,.255,0,4,2.5,1.2,{leadCount:6}],
    ["S14","few_terminal","rear",.85,.25,90,3,2,1.1,{leadCount:3}],
    ["S15","small_outline","rear",.83,.295,90,4.2,2.2,1.2,{leadCount:8}],
    ["S16","small_outline","right",.83,.525,0,7,3.3,1.5,{leadCount:14}],
    ["S17","small_outline","right",.735,.565,90,4.8,2.8,1.4,{leadCount:8}],
    ["S18","small_outline","right",.775,.61,90,5,2.8,1.4,{leadCount:8}],
    ["S19","leadless_block","right",.945,.875,90,4.5,3.8,1.4,{}],
    ["S20","small_outline","front",.35,.889,0,9,3.5,1.6,{leadCount:14}],
    ["H01","header","left",.045,.37,90,31,5,6,{contactCount:24,rows:2}],
    ["H02","header","rear",.335,.065,0,20,5,6,{contactCount:16,rows:2}],
    ["H03","header","right",.915,.205,90,23,5.2,6.7,{contactCount:18,rows:2}],
    ["H04","header","right",.915,.52,90,31,5.2,6.5,{contactCount:26,rows:2}],
    ["H05","header","front",.47,.9615,0,48,5.6,7,{contactCount:40,rows:2}],
    ["H06","header","right",.805,.925,0,31,5.6,7,{contactCount:26,rows:2}],
    ["J01","white_connector","left",.09,.095,0,9,4.5,5,{contactCount:6,rows:1}],
    ["J02","white_connector","front",.075,.755,90,12,8.5,8.5,{contactCount:8,rows:2}],
    ["J03","shielded_connector","right",.855,.755,0,13,10.5,5.5,{}],
    ["J04","rear_metal_block","rear",.465,.07,0,9,5.5,14,{}],
    ["J05","rear_metal_block","rear",.565,.07,0,9,5.5,15,{}],
    ["C01","aluminum_can","left",.105,.185,0,5.8,5.8,7,{}],
    ["C02","aluminum_can","left",.20,.205,0,4.5,4.5,5.2,{}],
    ["C03","aluminum_can","rear",.24,.115,0,4.8,4.8,6,{}],
    ["C04","aluminum_can","rear",.285,.18,0,4.5,4.5,5.8,{}],
    ["C05","aluminum_can","left",.175,.425,0,5.2,5.2,6.2,{}],
    ["C06","aluminum_can","left",.075,.59,0,5.8,5.8,6.8,{}],
    ["C07","aluminum_can","left",.15,.65,0,6,6,7.2,{}],
    ["C08","aluminum_can","left",.225,.625,0,5.8,5.8,6.8,{}],
    ["C09","aluminum_can","front",.35,.82,0,5.8,5.8,6.8,{}],
    ["C10","aluminum_can","front",.43,.805,0,6.2,6.2,7.4,{}],
    ["C11","aluminum_can","front",.52,.818,0,5.8,5.8,7,{}],
    ["C12","aluminum_can","front",.61,.818,0,6,6,7.4,{}],
    ["C13","aluminum_can","right",.93,.715,0,4.5,4.5,5.6,{}],
    ["C14","aluminum_can","right",.95,.79,0,7,7,8.6,{}],
    ["C15","aluminum_can","front",.25,.955,0,7,7,9.5,{}],
    ["E01","electrolytic_can","rear",.465,.215,0,6.8,6.8,13,{}],
    ["E02","electrolytic_can","rear",.57,.21,0,6.6,6.6,14.5,{}],
    ["E03","electrolytic_can","rear",.66,.075,0,6.8,6.8,16,{}],
    ["E04","electrolytic_can","rear",.745,.075,0,7,7,17,{}],
    ["L01","wound_inductor","rear",.835,.075,0,6.8,6.8,10.5,{}],
    ["O01","coated_radial","rear",.735,.235,0,4,3.5,8.5,{}],
    ["T01","gold_post","rear",.65,.185,0,1.8,1.8,5.3,{}],
    ["T02","gold_post","rear",.655,.265,0,2.1,2.1,5,{}],
    ["T03","gold_post","center",.72,.345,0,2.1,2.1,4.2,{}],
    ["T04","gold_post","left",.245,.415,0,2.2,2.2,4,{}],
    ["T05","gold_post","left",.32,.59,0,2.2,2.2,4.5,{}],
    ["T06","gold_post","front",.185,.83,0,2.3,2.3,4.4,{}],
    ["T07","gold_post","front",.65,.81,0,2.1,2.1,4.4,{}],
    ["T08","gold_post","right",.92,.843,0,2.2,2.2,4.5,{}],
];

// Independent P bodies only. Terminal/band IDs are attached below, never duplicated.
// [ID,u,v,rotation,family,bodywidth,diameter/depth,height,color/variant]
const PASSIVE_LAYOUT = [
    ["P01",.295,.24,90,"coated_axial",3.5,1.5,2.5],
    ["P02",.325,.24,90,"ceramic_chip",2.6,1.4,1.4],
    ["P03",.355,.24,90,"coated_axial",3.5,1.5,2.5],
    ["P04",.385,.24,90,"ceramic_chip",2.5,1.4,1.5],
    ["P05",.415,.24,90,"coated_axial",3.4,1.5,2.4],
    ["P06",.145,.245,90,"axial_resistor",3.3,1.4,2.4],
    ["P07",.235,.22,90,"axial_resistor",3.2,1.3,2.3],
    ["P08",.105,.325,0,"axial_resistor",3.3,1.4,2.4],
    ["P09",.112,.37,0,"axial_resistor",3.3,1.4,2.4],
    ["P10",.117,.415,0,"axial_resistor",3.3,1.4,2.4],
    ["P11",.122,.46,0,"axial_resistor",3.3,1.4,2.4],
    ["P12",.16,.49,90,"coated_red",3.5,1.6,2.6],
    ["P13",.35,.425,90,"ceramic_chip",3,1.5,2.5,{bodyShape:"axial"}],
    ["P14",.39,.415,0,"coated_axial",4,1.7,2.7],
    ["P15",.43,.405,90,"ceramic_chip",2.6,1.3,1.4],
    ["P16",.448,.395,90,"ceramic_chip",3.2,1.5,2.5,{bodyShape:"axial"}],
    ["P17",.485,.397,0,"coated_axial",3.6,1.5,2.5],
    ["P18",.54,.397,0,"axial_resistor",3.5,1.5,2.5],
    ["P19",.605,.397,0,"coated_axial",4.3,1.8,2.8],
    ["P20",.80,.165,0,"coated_axial",3.8,1.5,2.5],
    ["P21",.835,.19,0,"axial_resistor",3.4,1.4,2.4],
    ["P22",.77,.305,0,"coated_axial",3.5,1.5,2.5],
    ["P23",.848,.345,0,"axial_resistor",3.3,1.4,2.4],
    ["P24",.685,.425,15,"coated_axial",4.7,1.9,3],
    ["P25",.70,.47,15,"axial_resistor",3.9,1.6,2.6],
    ["P26",.72,.51,15,"ceramic_chip",3.5,1.6,2.6,{bodyShape:"axial"}],
    ["P27",.80,.595,90,"axial_resistor",3.5,1.4,2.4],
    ["P28",.827,.595,90,"axial_resistor",3.5,1.4,2.4],
    ["P29",.854,.595,90,"axial_resistor",3.5,1.4,2.4],
    ["P30",.881,.595,90,"axial_resistor",3.5,1.4,2.4],
    ["P33",.72,.63,0,"ceramic_chip",2.8,1.5,1.5],
    ["P34",.72,.665,0,"coated_axial",3.4,1.5,2.5],
    ["P35",.76,.665,0,"ceramic_chip",2.8,1.4,1.4],
    ["P36",.795,.67,0,"ceramic_chip",2.8,1.4,1.4],
    ["P37",.965,.70,90,"axial_resistor",3.8,1.5,2.5],
    ["P39",.963,.635,0,"coated_red",3.2,1.7,2.7],
    ["P40",.967,.875,90,"axial_resistor",4.2,1.6,2.6],
    ["P41",.68,.645,90,"coated_axial",4.3,1.7,2.7],
    ["P42",.635,.665,0,"ceramic_chip",3.4,1.5,1.7],
    ["P43",.595,.65,0,"ceramic_chip",3.2,1.5,2.5,{bodyShape:"axial"}],
    ["P44",.32,.52,90,"coated_red",4.5,1.9,3],
    ["P45",.425,.65,0,"ceramic_chip",3.2,1.6,2.6,{bodyShape:"axial"}],
    ["P46",.475,.65,0,"coated_axial",3.8,1.6,2.6],
    ["P47",.535,.65,0,"axial_resistor",3.5,1.5,2.5],
    ["P49",.185,.73,0,"coated_axial",4.8,1.9,3],
    ["P50",.185,.77,0,"axial_resistor",3.7,1.6,2.6],
    ["P51",.185,.807,0,"axial_resistor",3.5,1.5,2.5],
    ["P52",.245,.88,0,"axial_resistor",3.9,1.6,2.6,"#cba77b"],
    ["P53",.235,.904,0,"axial_resistor",3.5,1.5,2.5,"#cba77b"],
    ["P54",.48,.889,90,"axial_resistor",3.5,1.5,2.5],
    ["P55",.52,.889,90,"axial_resistor",3.5,1.5,2.5],
    ["P56",.56,.889,90,"axial_resistor",3.5,1.5,2.5],
    ["P57",.60,.889,90,"axial_resistor",3.5,1.5,2.5],
    ["P58",.64,.889,90,"axial_resistor",3.5,1.5,2.5],
];

const REGION_IDS = {
    rear: "P01 P02 P03 P04 P05 P16 P17 P18 P19 P20 P21 P22 P23",
    left: "P06 P07 P08 P09 P10 P11 P12 P44",
    center: "P13 P14 P15 P24 P25 P26 P41 P42 P43 P45 P46 P47",
    right: "P27 P28 P29 P30 P33 P34 P35 P36 P37 P39 P40",
    front: "P49 P50 P51 P52 P53 P54 P55 P56 P57 P58",
};
const passiveRegion = new Map(Object.entries(REGION_IDS).flatMap(([region, ids]) => ids.split(" ").map(id => [id, region])));
for (const [id,u,v,rotation,family,width,depth,height,style] of PASSIVE_LAYOUT) {
    BODY_LAYOUT.push([id,family,passiveRegion.get(id),u,v,rotation,width,depth,height,typeof style === "string" ? {color:style} : style ?? {}]);
}
const PARENT_DETAILS = freezeDeep({
    P31: { ownerId: "P30", association: "APPROXIMATE", detail: "Ambiguous terminal / solder boundary" },
    P32: { ownerId: "P27", association: "APPROXIMATE", detail: "Ambiguous terminal / solder boundary" },
    P38: { ownerId: "P37", association: "APPROXIMATE", detail: "Ambiguous body-end / band detail" },
    P48: { ownerId: "P47", association: "APPROXIMATE", detail: "Adjacent band / terminal detail" },
    P59: { ownerId: "P54", association: "SOURCE_DESCRIBED", detail: "Front-row terminal / band / solder detail" },
    P60: { ownerId: "P55", association: "SOURCE_DESCRIBED", detail: "Front-row terminal / band / solder detail" },
    P61: { ownerId: "P56", association: "SOURCE_DESCRIBED", detail: "Front-row terminal / band / solder detail" },
    P62: { ownerId: "P57", association: "SOURCE_DESCRIBED", detail: "Front-row terminal / band / solder detail" },
    P63: { ownerId: "P58", association: "SOURCE_DESCRIBED", detail: "Front-row terminal / band / solder detail" },
});
const PATCH_LAYOUT = [
    ["X01","rear",.35,.272,4.2,1.2,["P01","P02","P03","P04","P05"]],
    ["X02","left",.175,.252,2.8,1.2,["S01","S02","P06","P07"]],
    ["X03","rear",.825,.22,3,1.3,["L01","S13","S14","S15"]],
    ["X04","center",.54,.367,3,1.1,["P16","P17","P18","P19"]],
    ["X05","right",.85,.636,4,1,["P27","P28","P29","P30"]],
    ["X06","front",.56,.935,5.5,1.1,["P54","P55","P56","P57","P58"]],
    ["X07","front",.26,.91,2.5,1,["P52","P53","C15"]],
    ["X08","center",.525,.671,3.5,1.2,["P45","P46","P47"]],
];
const HOLE_LAYOUT = [["M01",.045,.045],["M02",.045,.97],["M03",.97,.96],["M04",.96,.045]];
const bodyById = new Map(BODY_LAYOUT.map(row => [row[0], row]));
const patchById = new Map(PATCH_LAYOUT.map(row => [row[0], row]));

function disposition(item) {
    if (bodyById.has(item.id)) return "ILLUSTRATIVE_BODY";
    if (PARENT_DETAILS[item.id]) return "PARENT_SUBDETAIL";
    if (patchById.has(item.id)) return "UNRESOLVED_PATCH";
    if (item.id.startsWith("M")) return "BOARD_FEATURE";
    if (item.id.startsWith("B")) return "SHARED_RENDER_FEATURE";
    return "VIEWPORT_ONLY";
}

export const VISUAL_INVENTORY = freezeDeep(SOURCE_ITEMS.map(item => {
    const row = bodyById.get(item.id), detail = PARENT_DETAILS[item.id], patch = patchById.get(item.id);
    const family = row?.[1] ?? (detail ? bodyById.get(detail.ownerId)[1] : patch ? "unresolved_patch" : item.sourceFamily);
    return { ...item, disposition: disposition(item), family,
        region: row?.[2] ?? (detail ? bodyById.get(detail.ownerId)[2] : patch?.[1] ?? "shared"),
        ownerId: row ? item.id : detail?.ownerId ?? null,
        ownershipBasis: detail?.association ?? (row ? "ILLUSTRATIVE_BODY" : "NOT_A_COMPONENT"),
        subdetail: detail?.detail ?? null,
        normalizedPosition: row ? [row[3],row[4]] : null,
        modelAssetId: row || detail || patch ? `ohmni-procedural/${family}@reference-packages-v1` : null,
        visualProvenance: "ILLUSTRATIVE_ONLY", circuitRole: "UNKNOWN", roleEvidenceId: null,
        sourceComponentId: null, sourceFootprintId: null,
    };
}));
const inventoryById = new Map(VISUAL_INVENTORY.map(item => [item.id, item]));

// Preserve all coverage IDs while making independent-body count unambiguous.
if (VISUAL_INVENTORY.length !== 158 || bodyById.size !== 124 || PASSIVE_LAYOUT.length !== 54
    || Object.keys(PARENT_DETAILS).length !== 9 || new Set(VISUAL_INVENTORY.map(item => item.id)).size !== 158) {
    throw new Error("Reference visual inventory coverage mismatch");
}

const world = (u, v) => [(u - .5) * 140, (.5 - v) * 100];
function knownSourceFacts(item) {
    return { observation: item.observation, familyInference: item.familyInference,
        confidence: item.confidence, imagePointPx: item.imagePointPx,
        identity: "UNKNOWN", circuitRole: "UNKNOWN", componentValue: "UNKNOWN" };
}
function buildInstance(row, order) {
    const [id,family,region,u,v,rotation,width,depth,height,extras] = row;
    const item = inventoryById.get(id), lesson = FAMILY_LESSONS[family];
    const [x,y] = world(u,v), radians = rotation * Math.PI / 180;
    const options = {width,depth,height,...extras};
    if (["qfp","small_outline","leadless_block","aluminum_can","electrolytic_can"].includes(family)) options.label = `OHMNI\n${id}`;
    return { id, instanceId: id, family, region, x, y, rotation, order, options,
        name: id === "IC01" ? "Largest leaded IC" : lesson.name,
        description: lesson.general, lesson, educationNotice: REFERENCE_EDUCATION_NOTICE,
        knownSourceFacts: knownSourceFacts(item),
        unknownFacts: lesson.unknown,
        modelAssetId: item.modelAssetId, sourceComponentId: null, sourceFootprintId: null,
        roleLabel: "UNKNOWN", roleEvidenceId: null, visualProvenance: "ILLUSTRATIVE_ONLY",
        dimensionalSource: "ARTISTIC_SAMPLE_DIMENSIONS", selectable: true,
        normalizedPosition: [u,v],
        transform: { position: [x,y,.8], quaternion: [0,0,Math.sin(radians/2),Math.cos(radians/2)] },
        modelAssumptions: { dimensions: {width,depth,height}, units: "artist-selected mm",
            leadCount: extras.leadCount ?? null, contactCount: extras.contactCount ?? null,
            countsAreIllustrative: true, bandsAreIllustrative: family === "axial_resistor",
            bodyShape: extras.bodyShape ?? null,
            geometrySource: "Original procedural model; no reference dimensions recovered" },
        subdetailIds: Object.entries(PARENT_DETAILS).filter(([,value]) => value.ownerId === id).map(([key]) => key),
    };
}

// Each corridor is art direction: [u1,v1,u2,v2,u3,v3,u4,v4,lanes,spacing].
// These paths intentionally have no source pin IDs, signal names, net IDs or current.
const GUIDE_CORRIDORS = [
    [.493,.45,.45,.43,.43,.37,.405,.365,6,.008],
    [.54,.416,.54,.385,.54,.375,.54,.365,6,.006],
    [.62,.416,.655,.36,.67,.29,.695,.12,6,.005],
    [.646,.455,.68,.455,.72,.44,.74,.42,6,.007],
    [.646,.525,.68,.53,.71,.56,.78,.56,6,.008],
    [.646,.585,.685,.6,.78,.64,.82,.69,5,.007],
    [.59,.634,.59,.66,.59,.68,.59,.67,6,.006],
    [.515,.634,.485,.675,.48,.71,.49,.725,5,.007],
    [.493,.565,.45,.585,.40,.59,.33,.62,6,.006],
    [.493,.515,.47,.495,.455,.505,.45,.525,6,.007],
    [.36,.515,.325,.49,.30,.465,.295,.465,5,.007],
    [.305,.335,.265,.32,.245,.315,.24,.315,5,.006],
    [.35,.375,.335,.395,.285,.42,.25,.44,5,.007],
    [.37,.755,.40,.765,.43,.765,.485,.73,5,.006],
    [.615,.735,.65,.72,.68,.715,.69,.715,5,.006],
    [.48,.915,.46,.89,.43,.885,.415,.88,4,.006],
    [.72,.82,.73,.855,.74,.875,.75,.89,6,.006],
];
function guideGeometry() {
    const paths = [];
    GUIDE_CORRIDORS.forEach((c, corridor) => {
        for (let lane = 0; lane < c[8]; lane += 1) {
            const offset = (lane - (c[8] - 1)/2) * c[9];
            paths.push({ id: `guide-${corridor + 1}-${lane + 1}`, width: .16,
                points: [[c[0],c[1]+offset],[c[2],c[3]+offset],[c[4],c[5]+offset],[c[6],c[7]+offset]].map(([u,v]) => world(u,v)),
                visualProvenance: "ILLUSTRATIVE_ONLY" });
        }
    });
    return { label: "Illustrative surface paths · no electrical connectivity", provenance: "ILLUSTRATIVE_ONLY", paths };
}

// Selected surface-detail positions are artistic choices beside visual corridors.
// They are not measured via coordinates and do not imply plated electrical holes.
const SURFACE_FEATURE_LAYOUT = [
    [.25,.26], [.285,.285], [.46,.48], [.35,.57], [.65,.34], [.69,.27],
    [.78,.18], [.865,.345], [.69,.55], [.70,.61], [.805,.705], [.87,.85],
    [.39,.74], [.425,.765], [.47,.80], [.565,.795], [.71,.875], [.225,.845],
    [.105,.81], [.06,.68], [.155,.55], [.285,.435], [.33,.62], [.55,.675],
];
function surfaceFeatures() {
    return { label: "Illustrative pad-like rings and openings · no assigned connectivity",
        provenance: "ILLUSTRATIVE_ONLY", inventoryId: "B04",
        items: SURFACE_FEATURE_LAYOUT.map(([u,v],index) => {
            const [x,y] = world(u,v);
            return { id: `illustrative-surface-${String(index+1).padStart(2,"0")}`,
                inventoryId: "B04", x,y, normalizedPosition: [u,v],
                radius: .12, annulus: .32, showOpening: true,
                visualProvenance: "ILLUSTRATIVE_ONLY", countAsComponent: false,
                dimensionalSource: "ARTISTIC_SAMPLE_DIMENSIONS",
                observation: "Small ring / pad / hole-like detail; electrical function and plating unknown" };
        }) };
}

export function createIllustrativeSceneManifest() {
    const instances = BODY_LAYOUT.map(buildInstance);
    return {
        schemaVersion: 1, namespace: REFERENCE_INVENTORY_METADATA.namespace,
        id: `ohmni:illustrative-reference:v1:${VISUAL_SOURCE_HASH}`, title: "Dense component explorer", label: REFERENCE_LABEL,
        modelSourceHash: VISUAL_SOURCE_HASH,
        provenance: "ILLUSTRATIVE_ONLY", visualProvenance: "ILLUSTRATIVE_ONLY",
        source: REFERENCE_INVENTORY_METADATA, width: 140, depth: 100, thickness: 1.6,
        dimensionalSource: "ARTISTIC_SAMPLE_DIMENSIONS", instances,
        inventory: VISUAL_INVENTORY,
        holes: HOLE_LAYOUT.map(([id,u,v]) => ({id, ...Object.fromEntries(["x","y"].map((key,index) => [key,world(u,v)[index]])),
            radius: 1.7, annulus: 3.2, normalizedPosition: [u,v], visualProvenance: "ILLUSTRATIVE_ONLY",
            observation: id === "M04" ? "Partly observed corner; full sample opening is an artistic choice" : "Gold-rimmed opening observed; sample size is artistic"})),
        illustrativeGuideGeometry: guideGeometry(),
        illustrativeSurfaceFeatures: surfaceFeatures(),
        microdetailPatches: PATCH_LAYOUT.map(([id,region,u,v,width,depth,nearbyIds]) => {
            const [x,y] = world(u,v);
            return { id, family: "unresolved_patch", region, x, y, rotation: 0,
                options: {width,depth,height:.18}, visualProvenance: "ILLUSTRATIVE_ONLY",
                countAsComponent: false, selectable: false, ownerId: null, nearbyIds,
                label: "Unresolved surface / attachment detail", knownSourceFacts: knownSourceFacts(inventoryById.get(id)) };
        }),
        parentSubdetails: Object.entries(PARENT_DETAILS).map(([id,detail]) => ({id,...detail,visualProvenance:"ILLUSTRATIVE_ONLY"})),
        sharedFeatures: VISUAL_INVENTORY.filter(item => item.id.startsWith("B")),
        viewportFeatures: [
            {id:"V01", disposition:"OPTIONAL_NATIVE_GRID", explanation:"Viewer guide, never board copper"},
            {id:"V02", disposition:"NATIVE_FRONT_BACK_CONTROLS", explanation:"Ohmni camera controls replace the source editor axis widget"},
            {id:"V03", disposition:"NATIVE_RESET_AND_VIEW_CONTROLS", explanation:"Ohmni controls replace the source editor view cube"},
        ],
    };
}

export function getVisualFamilyCatalog() {
    return Object.entries(FAMILY_LESSONS).map(([family,lesson]) => ({
        family, ...lesson, modelAssetId:`ohmni-procedural/${family}@reference-packages-v1`,
        visualProvenance:"ILLUSTRATIVE_ONLY", modelSource:REFERENCE_INVENTORY_METADATA.modelSource,
        license:REFERENCE_INVENTORY_METADATA.modelLicense,
        instanceIds: VISUAL_INVENTORY.filter(item => item.family === family && item.disposition === "ILLUSTRATIVE_BODY").map(item => item.id),
        specimenOptions: {...(BODY_LAYOUT.find(row => row[1] === family)?.slice(6,9).reduce((result,value,index) => ({...result,[["width","depth","height"][index]]:value}),{}) ?? {width:4,depth:2,height:.18})},
    }));
}
