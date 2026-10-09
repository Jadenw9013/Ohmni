// Pure, read-only inventory for the frozen landing reference. No renderer or I/O.
// A candidate and a geometric observation do not establish library compatibility.
import { packageBinding } from './visual-board-scene.js';
import { VISUAL_SOURCE_HASH } from './visual-version.js';

export const LANDING_REFERENCE_FINGERPRINT = '8ec92f595a26b5769e16186e32231332955db4411247973489abe6c9c9def4f8';
const SHA256 = /^[a-f0-9]{64}$/;
const EPSILON_MM = 1e-9; // Arithmetic tolerance only, never a manufacturing tolerance.
const CANDIDATES = Object.freeze({
    GENERIC_RESISTOR: ['OHM-005', 'chip2t', 'R.0805I'],
    GENERIC_CAPACITOR: ['OHM-024', 'chip2t', 'C.0805I'],
    GENERIC_LED_GREEN: ['OHM-079', 'led-passive', 'OHM-079'],
    HEADER_1X6_254: ['OHM-150', 'completion-a', 'OHM-150'],
    'AP2112K-3.3TRG1': ['OHM-120', 'leaded', 'OHM-120'],
    USB_C_RECEPTACLE_16P: ['OHM-165', 'completion-c', 'OHM-165'],
});

function finite(value, label) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new RangeError(`${label} must be finite`);
    return value;
}
function positive(value, label) {
    if (finite(value, label) <= 0) throw new RangeError(`${label} must be positive`);
    return value;
}
function freeze(value) {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
}
function text(value, label) {
    if (typeof value !== 'string' || !value.length) throw new RangeError(`${label} is required`);
    return value;
}

/** Explicit mirror, then rotation, then translation. No implicit board-side mirror. */
export function transformLandingPoint(point, { translationMm = [0, 0, 0], rotationDeg = 0,
    mirrorX = false, mirrorZ = false } = {}) {
    if (!Array.isArray(point) || point.length !== 3 || !Array.isArray(translationMm)
        || translationMm.length !== 3 || typeof mirrorX !== 'boolean' || typeof mirrorZ !== 'boolean') {
        throw new RangeError('Three coordinates and explicit boolean mirrors are required');
    }
    [...point, ...translationMm, rotationDeg].forEach(value => finite(value, 'transform'));
    const angle = rotationDeg * Math.PI / 180, x = point[0] * (mirrorX ? -1 : 1), y = point[1];
    return [translationMm[0] + x * Math.cos(angle) - y * Math.sin(angle),
        translationMm[1] + x * Math.sin(angle) + y * Math.cos(angle),
        translationMm[2] + point[2] * (mirrorZ ? -1 : 1)];
}

/**
 * Conservative, independently calculable SMD overlap observation. A circle lies
 * wholly inside each supported land and rectangular contact. Their shared disk
 * gives a lower bound without guessing a roundrect corner radius. Seating is
 * checked separately. This is neither a complete fit check nor footprint identity.
 */
export function checkLandingContactOverlap(contact, land, transform = {}) {
    if (!Array.isArray(contact?.centerMm) || contact.centerMm.length !== 3) throw new RangeError('Contact center required');
    const width = positive(contact.widthMm, 'contact width'), height = positive(contact.heightMm, 'contact height');
    const padWidth = positive(land.width_mm, 'land width'), padHeight = positive(land.height_mm, 'land height');
    const padX = finite(land.x_mm, 'land x'), padY = finite(land.y_mm, 'land y');
    if (land.kind !== 'smd' || !['rect', 'roundrect', 'circle', 'oval'].includes(land.shape)) {
        return { status: 'NOT_ESTABLISHED', reason: 'Only SMD contact surfaces are covered by this check.' };
    }
    if (land.shape === 'circle' && padWidth !== padHeight) throw new RangeError('Circular land has unequal diameters');
    const center = transformLandingPoint(contact.centerMm, transform);
    const distance = Math.hypot(center[0] - padX, center[1] - padY);
    const radius = Math.min(width / 2, height / 2, Math.min(padWidth, padHeight) / 2 - distance);
    const common = { scope: 'SMD_CONTACT_SURFACE_OVERLAP_LOWER_BOUND', contactCenterMm: center,
        landCenterMm: [padX, padY, 0], centerDistanceMm: distance,
        numericalToleranceMm: EPSILON_MM, mechanicalToleranceMm: null };
    if (Math.abs(center[2]) > EPSILON_MM) return { ...common, status: 'FAIL_SEATING_PLANE', overlapLowerBoundMm2: 0 };
    if (radius > EPSILON_MM) return { ...common, status: 'SUPPORTED_OVERLAP_LOWER_BOUND',
        overlapLowerBoundMm2: Math.PI * radius ** 2 };
    if (distance > Math.hypot(width, height) / 2 + Math.hypot(padWidth, padHeight) / 2 + EPSILON_MM) {
        return { ...common, status: 'FAIL_DISJOINT', overlapLowerBoundMm2: 0 };
    }
    return { ...common, status: 'NOT_ESTABLISHED', overlapLowerBoundMm2: null,
        reason: 'The conservative disks do not overlap; the complete contact/land shapes were not tested.' };
}

/** XY containment of a square tail in a circular hole; no board/tail depth claim. */
export function checkLandingThroughHoleFit(contact, land, transform = {}) {
    const width = positive(contact.squareTailWidthMm, 'square tail width');
    if (land.kind !== 'thru_hole' || land.drill?.shape !== 'circle'
        || land.drill.width_mm !== land.drill.height_mm) {
        return { status: 'NOT_ESTABLISHED', reason: 'This check only covers square tails and circular plated holes.' };
    }
    const diameter = positive(land.drill.width_mm, 'hole diameter');
    const center = transformLandingPoint(contact.centerMm, transform);
    const distance = Math.hypot(center[0] - finite(land.x_mm, 'hole x'), center[1] - finite(land.y_mm, 'hole y'));
    const radialClearance = diameter / 2 - distance - width / Math.sqrt(2);
    return { status: radialClearance >= -EPSILON_MM ? 'SUPPORTED_HOLE_XY_CONTAINMENT' : 'FAIL_HOLE_XY_CONTAINMENT',
        scope: 'SQUARE_TAIL_IN_CIRCULAR_HOLE_XY', contactCenterMm: center,
        holeCenterMm: [land.x_mm, land.y_mm, 0], centerDistanceMm: distance,
        radialClearanceMm: radialClearance, numericalToleranceMm: EPSILON_MM,
        mechanicalToleranceMm: null, tailDepthEstablished: false };
}

function sourceLand(component, pad, index, board) {
    for (const key of ['x_mm', 'y_mm']) finite(pad[key], `land ${key}`);
    for (const key of ['width_mm', 'height_mm']) positive(pad[key], `land ${key}`);
    if (pad.drill) {
        positive(pad.drill.width_mm, 'drill width'); positive(pad.drill.height_mm, 'drill height');
    }
    const number = pad.kind === 'np_thru_hole' && pad.number === '' ? '' : text(pad.number, 'pad number');
    return { id: [component.ref, index, number], sourceIndex: index, electricalPadNumber: number,
        sourceGeometry: structuredClone(pad), footprintLocalCenterMm: [pad.x_mm, pad.y_mm, 0],
        // Saved pad coordinates already describe the physical footprint, on either side.
        // Mirroring these again would change the source copper geometry.
        boardCenterMm: transformLandingPoint([pad.x_mm, pad.y_mm, 0], {
            translationMm: [component.x_mm - board.width_mm / 2, component.y_mm - board.height_mm / 2, 0],
            rotationDeg: component.rotation_deg }),
        candidateModelContact: null };
}

function terminalMapping(component, lands) {
    const sourceElectricalGroups = Object.fromEntries([...new Set(lands.map(land => land.electricalPadNumber).filter(Boolean))]
        .map(number => [number, lands.filter(land => land.electricalPadNumber === number).map(land => land.id)]));
    if (component.part_id === 'GENERIC_LED_GREEN') {
        return { status: 'BLOCKED_SOURCE_DISCREPANCY', sourceElectricalGroups,
            approvedCatalogPinRoles: { '1': 'A', '2': 'K' }, approvedPackageTerminalRoles: { '1': 'K', '2': 'A' },
            approvedCatalogToPackageTerminal: { '1': '2', '2': '1' },
            approvedCatalogToCurrentFootprintPad: { '1': '2', '2': '1' },
            packageTerminalToSavedLand: null,
            basis: 'src/ohmni/behavior/data/bindings/GENERIC_LED_GREEN.json; .ai/approvals/COMPONENT-BEHAVIOR-STAGE1.yaml',
            reason: 'The frozen preview records LEDn_A on pad 1 and GND on pad 2, predating the approved catalog-to-footprint permutation. Preserve that source; do not relabel, rotate or certify it as the current binding.' };
    }
    return { status: 'SOURCE_LANDS_ONLY', sourceElectricalGroups, packageTerminalToSavedLand: null,
        basis: 'Saved reference physical-land ordering and electrical pad numbers.',
        reason: component.part_id === 'GENERIC_MOMENTARY_BUTTON'
            ? 'Four physical lands retain repeated electrical numbers 1,1,2,2; no unique terminal-to-pad claim is made.'
            : 'Recorded land identity does not prove the retained approximation has a matching physical contact.' };
}

function candidateFor(component, datasets) {
    const definition = CANDIDATES[component.part_id];
    if (!definition) return null;
    const [componentId, dataset, profileId] = definition, data = datasets[dataset];
    const record = data?.components?.find(record => record.id === componentId);
    const candidate = { componentId, dataset, profileId, eligible: false, status: 'CANDIDATE_ONLY',
        sourceSpecSha256: data?.source_spec_sha256 ?? null, modelSourceSha256: VISUAL_SOURCE_HASH,
        sourceRecordStatus: record?.status ?? null,
        reason: 'Original footprint-file revision identity and complete physical-fit checks are unavailable.',
        options: componentId === 'OHM-150' ? { N: 6 } : {},
        candidateToFootprint: null };
    if (data && (!SHA256.test(data.source_spec_sha256) || !record || record.profile_id !== profileId)) {
        throw new RangeError(`Candidate dataset does not contain the expected ${componentId} profile/revision`);
    }
    if (componentId === 'OHM-165') {
        candidate.status = 'REJECTED_VARIANT';
        candidate.reason = 'Library USB-C model is Amphenol 12401610E4, not the saved HRO TYPE-C-31-M-12 footprint.';
    } else if (componentId === 'OHM-079') {
        candidate.status = 'BLOCKED_SOURCE_DISCREPANCY';
        candidate.reason = 'Approved LED polarity roles and frozen pad/net assignment require explicit reconciliation; geometry alone cannot approve a binding.';
    }
    return candidate;
}

function geometricObservations(component, candidate, datasets, lands) {
    if (candidate?.componentId === 'OHM-150' && datasets['completion-a']) {
        const profile = datasets['completion-a'].profiles?.['OHM-150'];
        if (!profile || profile.kind !== 'header' || profile.rows !== 1 || profile.right_angle
            || !profile.source_parameters?.includes('N') || lands.length !== 6) throw new RangeError('Expected the supported single-row header profile');
        const pitch = positive(profile.pitch, 'header pitch'), pin = positive(profile.pin, 'header pin width');
        candidate.candidateToFootprint = { rotationDeg: 180, translationMm: [0, 5 * pitch / 2, 0],
            mirrorX: false, mirrorZ: false, status: 'CANDIDATE_XY_TRANSFORM_ONLY',
            basis: 'Library pin 1 is at positive Y from FCO; saved footprint pin 1 is its origin and grows along positive Y.' };
        return lands.map((land, index) => {
            if (land.electricalPadNumber !== String(index + 1)) throw new RangeError('Unexpected header physical-land order');
            const contact = { terminal: String(index + 1), centerMm: [0, (2.5 - index) * pitch, 0],
                squareTailWidthMm: pin, basis: 'component-library/data/completion-a.json:OHM-150, N=6' };
            land.candidateModelContact = structuredClone(contact);
            return { terminal: contact.terminal, landId: land.id, candidateContact: contact,
                ...checkLandingThroughHoleFit(contact, land.sourceGeometry, candidate.candidateToFootprint),
                limitation: 'Canonical square cross-section in source circular hole only; no plating tolerance, solder, body seating or actual board/tail depth verdict.' };
        });
    }
    if (!candidate || candidate.dataset !== 'chip2t' || !datasets.chip2t) return [];
    const profile = datasets.chip2t.family?.profiles?.[candidate.profileId], dimensions = profile?.dimensions_mm;
    if (!dimensions) throw new RangeError('Candidate chip profile dimensions required');
    const length = positive(dimensions.overall_length?.default, 'profile length');
    const width = positive(dimensions.overall_width?.default, 'profile width');
    const band = positive((dimensions.terminal_band_bottom ?? dimensions.terminal_band)?.default, 'profile contact band');
    if (2 * band >= length || lands.length !== 2) throw new RangeError('Unsupported two-terminal candidate geometry');
    candidate.candidateToFootprint = { rotationDeg: 0, translationMm: [0, 0, 0], mirrorX: false, mirrorZ: false,
        status: 'CANONICAL_SYMMETRIC_PROFILE_ONLY', basis: 'Non-polar chip profile local convention; not an exact package binding.' };
    return ['1', '2'].map((terminal, index) => {
        const land = lands.find(land => land.electricalPadNumber === terminal);
        if (!land) throw new RangeError('Missing named chip land');
        const contact = { terminal, centerMm: [(index ? 1 : -1) * (length - band) / 2, 0, 0],
            widthMm: band, heightMm: width, basis: `component-library/data/chip2t.json:${candidate.profileId}` };
        land.candidateModelContact = structuredClone(contact);
        return { terminal, landId: land.id, candidateContact: contact,
            ...checkLandingContactOverlap(contact, land.sourceGeometry),
            limitation: 'Conservative positive overlap at the canonical seating plane only; no solder, tolerance, full footprint, body collision or electrical compatibility verdict.' };
    });
}

/** Source metadata is optional because the board subobject does not contain it. */
export function buildLandingBindings(board, sourceMetadata = {}, libraryDatasets = {}) {
    if (!board || board.artifact_fingerprint !== LANDING_REFERENCE_FINGERPRINT
        || board.kind === 'illustrative_sample' || board.visual_manifest) throw new RangeError('Frozen landing reference required');
    positive(board.width_mm, 'board width'); positive(board.height_mm, 'board height');
    if (!Array.isArray(board.components) || board.components.length !== 29) throw new RangeError('Expected all 29 saved references');
    if (sourceMetadata.artifact_fingerprint && sourceMetadata.artifact_fingerprint !== board.artifact_fingerprint) {
        throw new RangeError('Source metadata and board identity disagree');
    }
    const registryFingerprint = sourceMetadata.footprint_geometry_fingerprint ?? null;
    if (registryFingerprint !== null && !SHA256.test(registryFingerprint)) throw new RangeError('Invalid footprint registry identity');
    const source = { artifactFingerprint: board.artifact_fingerprint,
        footprintGeometryFingerprint: registryFingerprint, footprintGeometryScope: sourceMetadata.footprint_geometry_scope ?? null,
        sourceFootprintFileSha256: null, capturedOn: sourceMetadata.captured_on ?? null,
        provenance: 'SAVED_REFERENCE_PROJECTION', visualSourceHash: VISUAL_SOURCE_HASH,
        note: 'Identity is copied from the saved input, not independently reverified by this inventory.' };
    const seen = new Set();
    const entries = board.components.map(component => {
        const ref = text(component.ref, 'reference');
        if (seen.has(ref)) throw new RangeError(`Duplicate reference ${ref}`);
        seen.add(ref); text(component.part_id, 'part identity'); text(component.footprint_id, 'footprint identity');
        for (const key of ['x_mm', 'y_mm', 'rotation_deg']) finite(component[key], key);
        if (!['F.Cu', 'B.Cu'].includes(component.side) || !Array.isArray(component.pads) || !component.pads.length) {
            throw new RangeError('Explicit source side and physical lands required');
        }
        const family = packageBinding(component);
        if (family === 'missing_model') throw new RangeError(`Unmapped reference ${ref}`);
        const physicalLands = component.pads.map((pad, index) => sourceLand(component, pad, index, board));
        const candidate = candidateFor(component, libraryDatasets);
        const observations = geometricObservations(component, candidate, libraryDatasets, physicalLands);
        return { ref, partId: component.part_id, footprintId: component.footprint_id, sourceIdentity: { ...source },
            approximation: { assetId: `ohmni-procedural/${family}@reference-packages-v1`, family,
                status: 'PACKAGE_APPROXIMATION', sourceRevision: VISUAL_SOURCE_HASH,
                contactBasis: 'SOURCE_PAD_DERIVED_VISUALS', physicalFitEstablished: false },
            libraryCandidate: candidate,
            placement: { xMm: component.x_mm, yMm: component.y_mm, rotationDeg: component.rotation_deg,
                side: component.side, frame: 'OHMNI_Y_UP', sourcePadMirror: false,
                displayThicknessMm: board.display_thickness_mm, thicknessIsDisplayOnly: board.thickness_is_display_only === true },
            physicalLands, terminalMapping: terminalMapping(component, physicalLands),
            // The authoring report computes SHA-256 from this projection; it is not
            // the unavailable original footprint-file SHA and is never used as one.
            physicalLandProjection: { kind: 'DERIVED_SAVED_LAND_PROJECTION', sha256: null,
                canonicalJson: JSON.stringify({ footprintId: component.footprint_id, frame: 'OHMNI_Y_UP',
                    lands: physicalLands.map(land => ({ id: land.id, geometry: land.sourceGeometry })) }) },
            fit: { status: 'NOT_ESTABLISHED', observations,
                limitations: ['Original footprint-file revision SHA is absent.',
                    'Retained approximation mesh contact surfaces and seating/tails have not been independently checked.',
                    'Positive local overlap observations do not prove complete package fit, electrical behavior or manufacturability.'] },
            uncertainty: ['Component bodies, materials and display stack-up remain illustrative.',
                ...(registryFingerprint ? [] : ['Footprint registry identity was not supplied with the board subobject.']),
                ...(component.part_id === 'GENERIC_LED_GREEN' ? ['Saved LED pad/net assignment predates the approved polarity binding.'] : []),
                ...(candidate ? [candidate.reason] : ['No specific compatible library candidate is established.'])] };
    });
    return freeze({ schemaVersion: 1, source, entries,
        summary: { references: entries.length, physicalLands: entries.reduce((sum, entry) => sum + entry.physicalLands.length, 0),
            eligibleLibraryBindings: 0, establishedPhysicalFits: 0,
            positiveScopedOverlapObservations: entries.flatMap(entry => entry.fit.observations)
                .filter(observation => observation.status === 'SUPPORTED_OVERLAP_LOWER_BOUND').length,
            supportedHoleXyObservations: entries.flatMap(entry => entry.fit.observations)
                .filter(observation => observation.status === 'SUPPORTED_HOLE_XY_CONTAINMENT').length,
            sourceDiscrepancies: entries.filter(entry => entry.terminalMapping.status === 'BLOCKED_SOURCE_DISCREPANCY').length } });
}
