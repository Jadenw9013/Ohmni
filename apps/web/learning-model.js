// Learning content is a projection of recorded systems, never an electrical model.
const digest = (value) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const requireValue = (condition) => { if (!condition) throw new Error("Invalid circuit learning source"); };
const unique = (values) => new Set(values).size === values.length;

export function validateLearningSource(value, { reference = false } = {}) {
    requireValue(value && typeof value === "object");
    const { board, components, systems } = value;
    requireValue(board && Array.isArray(board.components) && Array.isArray(board.net_names)
        && Array.isArray(board.tracks) && Array.isArray(components) && Array.isArray(systems));
    requireValue(digest(board.artifact_fingerprint) && digest(board.routing_plan_fingerprint));
    if (reference) {
        requireValue(value.schema_version === 1
            && value.source?.kind === "previously_generated_reference_preview"
            && value.source.artifact_fingerprint === board.artifact_fingerprint
            && value.source.routing_plan_fingerprint === board.routing_plan_fingerprint);
    }
    const boardRefs = board.components.map((part) => part?.ref);
    const cardRefs = components.map((part) => part?.ref);
    requireValue(boardRefs.every((ref) => typeof ref === "string" && ref.length > 0)
        && unique(boardRefs) && unique(cardRefs) && boardRefs.length === cardRefs.length
        && cardRefs.every((ref) => boardRefs.includes(ref)));
    requireValue(unique(systems.map((system) => system?.system)));
    const refs = new Set(boardRefs);
    const nets = new Set(board.net_names);
    const validRefs = (list) => Array.isArray(list) && unique(list) && list.every((ref) => refs.has(ref));
    const validNets = (list) => Array.isArray(list) && unique(list) && list.every((net) => nets.has(net));
    for (const part of board.components) requireValue(validNets(part.net_names));
    for (const track of board.tracks) requireValue(nets.has(track?.net_name));
    for (const system of systems) {
        requireValue(system && typeof system.system === "string" && system.system.length > 0
            && typeof system.label === "string" && typeof system.summary === "string"
            && validRefs(system.component_refs) && validRefs(system.anchor_refs)
            && system.anchor_refs.every((ref) => system.component_refs.includes(ref))
            && system.component_refs.every((ref) => components.find((part) => part.ref === ref)?.system === system.system));
    }
    for (const card of components) {
        requireValue(systems.some((system) => system.system === card.system && system.component_refs.includes(card.ref)));
    }
    if (value.flows !== undefined) {
        requireValue(Array.isArray(value.flows));
        for (const flow of value.flows) {
            requireValue(flow && validRefs(flow.component_refs) && validNets(flow.net_names) && Array.isArray(flow.stages));
            for (const stage of flow.stages) requireValue(stage && validRefs(stage.component_refs) && validNets(stage.net_names));
        }
    }
    return value;
}

export function createLessons(source) {
    validateLearningSource(source, { reference: Boolean(source?.source) });
    const cards = new Map(source.components.map((part) => [part.ref, part]));
    return source.systems.filter((system) => system.component_refs.length > 0).map((system) => ({
        id: system.system,
        title: system.label,
        description: system.summary,
        refs: [...system.component_refs],
        anchorRefs: [...system.anchor_refs],
        parts: system.component_refs.map((ref) => ({ ref, name: cards.get(ref)?.name?.human || ref })),
    }));
}

export function discoveryOutcome(lesson, ref) {
    return Array.isArray(lesson?.refs) && lesson.refs.includes(ref) ? "match" : "other";
}
