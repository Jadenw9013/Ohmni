import {projectRequest} from './project-contract.js';
import {escapeHtml as e} from './view-model.js';

export function mountComponentTutor(root,{context,component,fetcher=globalThis.fetch}={}) {
    if(!root)return null;
    root.hidden=!globalThis.OHMNI_CONNECTED || !context || !component;
    if(root.hidden){root.innerHTML='';return null;}
    let disposed=false,busy=false,before=null,rows=[];
    const path=`/api/projects/${context.projectId}/revisions/${context.revisionId}`;
    root.innerHTML=`<section class="project-assistant"><h3>Ask about ${e(component)}</h3><p class="fineprint">Saved with this revision. Switch parts to continue their conversations.</p><div data-tutor-thread role="log" aria-label="Component conversation"></div><p data-tutor-error role="alert"></p><form data-tutor-form><label>Question about ${e(component)}<textarea data-tutor-question rows="3" maxlength="2000" required placeholder="How does this part work?"></textarea></label><button class="primary" data-tutor-send>Ask Ohmni</button></form><p class="fineprint">AI explanations use recorded design information. To edit the board, use Board chat or project settings.</p></section>`;
    const $=s=>root.querySelector(s);
    function render(){
        $('[data-tutor-thread]').innerHTML=(before?'<button type="button" class="ghost" data-tutor-older>Load earlier messages</button>':'')+rows.map(item=>`<div class="assistant-user-message"><span>You</span><p>${e(item.message)}</p></div><div class="assistant-reply"><span>Ohmni · ${e(component)}</span><p style="white-space:pre-wrap">${e(item.answer.explanation)}</p>${item.answer.unknowns?.length?`<p>Still unknown: ${e(item.answer.unknowns.join(' '))}</p>`:''}<details><summary>Records used</summary><ul>${(item.answer.sources||[]).map(source=>`<li>${e(source.label)}</li>`).join('')}</ul></details></div>`).join('');
        $('[data-tutor-older]')?.addEventListener('click',()=>void load(true));
    }
    async function load(older=false){
        try{const {payload}=await projectRequest(path+'/history?channel='+encodeURIComponent('component:'+component)+(older&&before?'&before='+before:''),{fetcher});
            if(disposed)return;rows=older?[...payload.messages,...rows]:payload.messages;before=payload.before;render();
        }catch(error){if(!disposed)$('[data-tutor-error]').textContent=error.message;}
    }
    async function ask(event){
        event.preventDefault();if(busy)return;
        const question=$('[data-tutor-question]').value.trim();if(!question)return;
        busy=true;$('[data-tutor-send]').disabled=true;$('[data-tutor-send]').textContent='Thinking…';$('[data-tutor-error]').textContent='';
        try{const {payload}=await projectRequest(path+'/teach',{fetcher,timeoutMs:90000,method:'POST',data:{component,question}});
            if(disposed)return;rows.push({message:question,answer:payload.answer});render();$('[data-tutor-question]').value='';
        }catch(error){if(!disposed)$('[data-tutor-error]').textContent=error.message;}
        finally{busy=false;if(!disposed){$('[data-tutor-send]').disabled=false;$('[data-tutor-send]').textContent='Ask Ohmni';}}
    }
    $('[data-tutor-form]').addEventListener('submit',ask);void load();
    return {dispose(){disposed=true;}};
}
