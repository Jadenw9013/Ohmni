import {connectWorkspace} from './connected-session.js';
// Local standalone servers retain their established demo workflow.
let remembered = false;
try { remembered = localStorage.getItem('ohmni-connected') === 'true'; } catch {}
const hosted = !['localhost','127.0.0.1',''].includes(location.hostname) || globalThis.OHMNI_CONNECTED_LOCAL || location.hash.startsWith('#connect=') || remembered;
let toolsReady=false;
async function boot() {
    try {
        if (hosted) {
            await connectWorkspace();
            document.querySelector('#workspace-storage').textContent='Private';
            const note=document.querySelector('.starter-footnote');
            if(note)note.textContent='Projects and chats are saved online. This browser remembers your private workspace. Save edits before reloading.';
        }
        // Start optional telemetry after removing connection credentials, but
        // before the renderer's module graph competes for loading time.
        const {startTelemetry} = await import('./telemetry.js');
        void startTelemetry();
        const app = await import('./app.js');
        if (globalThis.OHMNI_OPEN_PROJECT) {
            window.dispatchEvent(new HashChangeEvent('hashchange'));
            await app.openConnectedProject(globalThis.OHMNI_OPEN_PROJECT);
        }
        if (toolsReady) return;
        toolsReady=true;
        const {initializeComponentStories} = await import('./component-stories.js');
        initializeComponentStories();
        const {initializeVisualExplorer} = await import('./visual-explorer.js');
        initializeVisualExplorer();
    } catch (error) {
        const panel = document.createElement('section');
        panel.setAttribute('role','alert');
        panel.style.cssText='position:fixed;inset:20% 10%;z-index:9999;background:#132027;color:#eef7f4;padding:2rem;border:1px solid #8edbc3;border-radius:1rem';
        const title = document.createElement('h1'); title.textContent='Reconnect your Ohmni workspace';
        const copy = document.createElement('p'); copy.textContent=error.message;
        const retry=document.createElement('button');retry.textContent='Retry connection';retry.onclick=()=>{panel.remove();void boot();};
        panel.append(title,copy,retry);document.body.append(panel);
    }
}
window.addEventListener('hashchange',()=>{if(location.hash.startsWith('#connect='))void boot();});
export const ready = boot();
