// Link credentials exist only in the incoming fragment. The server exchanges
// them for an HttpOnly cookie; project/chat records remain on the server.
let pendingClaim = null;
export async function connectWorkspace({fetcher=globalThis.fetch, location=globalThis.location, history=globalThis.history}={}) {
    const fragment = new URLSearchParams(location.hash.slice(1));
    const claim = fragment.get('connect') || pendingClaim;
    pendingClaim = claim;
    if (claim) history.replaceState(null, '', location.pathname + location.search + '#workspace');
    const response = await fetcher('/connected/session', {method:'POST', credentials:'same-origin', cache:'no-store',
        headers:{'Content-Type':'application/json','X-Ohmni-Client':'main-ui'}, body:JSON.stringify(claim ? {claim} : {})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.refusal?.message || 'Your workspace could not be connected. Retry or send OPEN in Fetch for a new link.');
    pendingClaim = null;
    globalThis.OHMNI_API_BASE = '/connected';
    globalThis.OHMNI_CONNECTED = true;
    try { globalThis.localStorage?.setItem('ohmni-connected','true'); } catch {}
    // A project ID is a navigation hint, never an access credential.
    const requested = data.project_id || fragment.get('project');
    if (requested && /^[0-9a-f]{16}$/.test(requested)) {
        globalThis.OHMNI_OPEN_PROJECT = requested;
        history.replaceState(null,'',location.pathname + location.search + '#workspace');
    }
    return data;
}
