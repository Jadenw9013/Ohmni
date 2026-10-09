// P1 keeps declared source-pad approximations until original footprint revision
// identities are available. A candidate library model is never an automatic fit.
import { createAsset } from './visual-assets.js';

export function createLandingModelResolver(inventory) {
    const entries = new Map(inventory.entries.map(entry => [entry.ref, entry]));
    return (instance, materials) => {
        const binding = entries.get(instance.id);
        if (!binding || binding.footprintId !== instance.sourceFootprintId)
            throw new Error(`Unaccounted landing model: ${instance.id}`);
        const group = createAsset(instance.family, instance.options, materials);
        group.userData.landingBinding = binding;
        group.userData.geometryClaim = 'Declared source-pad package approximation; no verified library fit';
        return group;
    };
}
