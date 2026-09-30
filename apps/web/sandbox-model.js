// Disposable artistic composition. No evidence, nets, footprint, project or file IO.
export const SANDBOX_SIZE = Object.freeze({ width_nm: 80e6, depth_nm: 55e6 });
const GRIDS = [250000, 500000, 1000000];
const freeze = value => {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
};
export const emptySandbox = () => freeze({ items: [], past: [], future: [], sequence: 0 });
export function snapCoordinate(value, grid) {
    if (!Number.isFinite(value) || !GRIDS.includes(grid)) throw new RangeError('Invalid scene coordinate');
    return Math.round(value / grid) * grid;
}
function valid(item) {
    const keys = ['id','definition_id','x_nm','y_nm','width_nm','depth_nm','rotation_mdeg','side'];
    return item && Object.keys(item).length === keys.length && keys.every(key => Object.hasOwn(item,key))
        && typeof item.id === 'string' && item.id.length > 0 && item.id.length <= 100
        && typeof item.definition_id === 'string' && item.definition_id.length <= 300
        && [item.x_nm, item.y_nm].every(n => Number.isSafeInteger(n) && Math.abs(n) <= 500e6)
        && [item.width_nm, item.depth_nm].every(n => Number.isSafeInteger(n) && n > 0 && n <= 500e6)
        && [0,90000,180000,270000].includes(item.rotation_mdeg) && ['F.Cu','B.Cu'].includes(item.side);
}
export function sceneBounds(item) {
    if (!valid(item)) throw new RangeError('Invalid scene item');
    const quarter = item.rotation_mdeg % 180000 !== 0;
    const halfX = (quarter ? item.depth_nm : item.width_nm) / 2;
    const halfY = (quarter ? item.width_nm : item.depth_nm) / 2;
    return { left: item.x_nm-halfX, right: item.x_nm+halfX, top: item.y_nm-halfY, bottom: item.y_nm+halfY };
}
export function checkPlacement(items, candidate) {
    if (!valid(candidate)) return 'INVALID_INPUT';
    const a = sceneBounds(candidate);
    if (a.left < 0 || a.top < 0 || a.right > SANDBOX_SIZE.width_nm || a.bottom > SANDBOX_SIZE.depth_nm) return 'OUTSIDE';
    for (const item of items) {
        if (item.id === candidate.id || item.side !== candidate.side) continue;
        const b = sceneBounds(item);
        if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) return 'OVERLAP';
    }
    return 'ARTISTIC_FIT'; // Never DRC or electrical PASS.
}
export function sandboxCommand(state, command) {
    if (command.kind === 'discard') return emptySandbox();
    if (command.kind === 'undo') {
        if (!state.past.length) return state;
        return freeze({ items: state.past.at(-1), past: state.past.slice(0,-1),
            future: [state.items,...state.future], sequence: state.sequence+1 });
    }
    if (command.kind === 'redo') {
        if (!state.future.length) return state;
        return freeze({ items: state.future[0], past: [...state.past,state.items],
            future: state.future.slice(1), sequence: state.sequence+1 });
    }
    let items;
    if (command.kind === 'place') {
        const candidate = structuredClone(command.item);
        if (checkPlacement(state.items, candidate) !== 'ARTISTIC_FIT') throw new RangeError('Placement rejected');
        const existing = state.items.find(item => item.id === candidate.id);
        if (existing && (existing.definition_id !== candidate.definition_id || existing.width_nm !== candidate.width_nm
            || existing.depth_nm !== candidate.depth_nm)) throw new RangeError('Scene item identity changed');
        if (!existing && state.items.length >= 40) throw new RangeError('Scene limit reached');
        items = existing ? state.items.map(item => item.id === candidate.id ? candidate : item) : [...state.items,candidate];
    } else if (command.kind === 'reset') items = [];
    else if (command.kind === 'remove') {
        if (!state.items.some(item => item.id === command.id)) throw new RangeError('Unknown scene item');
        items = state.items.filter(item => item.id !== command.id);
    } else throw new RangeError('Unsupported sandbox command');
    return freeze({ items, past: [...state.past,state.items].slice(-100), future: [], sequence: state.sequence+1 });
}

export function sandboxManifest(state, definitions) {
    return { id: `sandbox:${state.sequence}`, provenance: 'ILLUSTRATIVE_ONLY', width: 80, depth: 55, thickness: 1.6,
        holes: [], pads: [], tracks: [], vias: [], silkscreen: [], instances: state.items.map(item => {
            const definition = definitions.find(d => d.id === item.definition_id);
            if (!definition) throw new RangeError('Unknown illustration');
            return { id: item.id, name: definition.name, family: definition.family,
                x: item.x_nm/1e6-40, y: 27.5-item.y_nm/1e6, rotation: -item.rotation_mdeg/1000,
                side: item.side, options: { ...definition.options } };
        }) };
}
