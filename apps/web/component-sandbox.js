import { BoardView } from './board-view.js';
import { visualBoard } from './visual-explorer.js';
import { emptySandbox, sandboxCommand, sandboxManifest, checkPlacement, snapCoordinate } from './sandbox-model.js';

const node = (tag, text, parent) => { const n=document.createElement(tag); n.textContent=text; parent?.append(n); return n; };
const svgNode = (tag, attributes, parent) => {
    const n=document.createElementNS('http://www.w3.org/2000/svg',tag);
    Object.entries(attributes).forEach(([k,v])=>n.setAttribute(k,String(v))); parent?.append(n); return n;
};
const messages = { ARTISTIC_FIT:'Fits the artistic scene. Electrical checks are unavailable.',
    OUTSIDE:'Outside the scene boundary.', OVERLAP:'Illustrative bodies overlap on this side.', INVALID_INPUT:'Enter valid scene coordinates.' };

export function openComponentSandbox(definitions, opener) {
    const dialog=document.createElement('dialog'); dialog.className='component-sandbox';
    dialog.setAttribute('aria-labelledby','sandbox-title');
    dialog.innerHTML=`<header class="story-heading"><div><h2 id="sandbox-title">Try a layout.</h2><p>Disposable learning scene. Nothing here changes a saved PCB.</p></div><button data-close>Discard & close</button></header>
        <p class="sandbox-warning">Artistic sizes, no connections. Fit feedback checks these sample boxes only; it is not a clearance or electrical check.</p>
        <div class="sandbox-layout"><aside><h3>Pick a part</h3><p>Drag a part to the map, or pick it and tap a location.</p><div data-inventory class="sandbox-inventory"></div></aside>
        <section><h3>Placement map</h3><div data-map-host></div><p data-fit role="status" aria-live="polite">Pick an illustration to begin.</p>
        <div class="sandbox-controls"><label>Grid <select data-grid><option value="1000000">1 mm</option><option value="500000">0.5 mm</option><option value="250000">0.25 mm</option></select></label>
        <label>X (mm) <input data-x type="number" min="-500" max="500" step="0.25"></label><label>Y (mm) <input data-y type="number" min="-500" max="500" step="0.25"></label>
        <button data-rotate>Rotate 90°</button><button data-side>Flip side</button><button data-place disabled>Place illustration</button><button data-cancel disabled>Cancel pickup</button></div>
        <p>Arrow keys nudge; Shift moves ten steps. R rotates, F flips, Enter places, Escape cancels pickup.</p>
        <h3>In this scene</h3><div data-placed class="sandbox-placed"></div></section>
        <section class="sandbox-preview"><h3>3D preview</h3><div class="sandbox-canvas"><canvas tabindex="0" aria-label="Illustrative scene. Drag to orbit. This view does not edit the placement map."></canvas></div><p>Drag to orbit. Preview updates after placement.</p></section></div>
        <footer class="story-navigation"><div><button data-undo disabled>Undo</button><button data-redo disabled>Redo</button><button data-reset>Reset scene</button></div><button data-discard>Discard scene</button></footer>`;
    document.body.append(dialog); dialog.showModal();
    const $=s=>dialog.querySelector(s), listeners=[];
    const listen=(target,event,fn)=>{target.addEventListener(event,fn);listeners.push(()=>target.removeEventListener(event,fn));};
    const map=svgNode('svg',{viewBox:'0 0 80 55',preserveAspectRatio:'none',tabindex:0,
        role:'application','aria-label':'Placement map. Pick a part, use arrow keys to move, R to rotate, Enter to place.'},$('[data-map-host]'));
    const background=svgNode('rect',{x:0,y:0,width:80,height:55,fill:'#e6f0ed'},map);
    const gridLayer=svgNode('g',{'pointer-events':'none'},map), itemLayer=svgNode('g',{},map), ghostLayer=svgNode('g',{'pointer-events':'none'},map);
    let state=emptySandbox(), candidate=null, grid=1000000, serial=0, pointer=null, suppressClick=false, coordinateError=false;
    const view=new BoardView($('canvas')); view.options.showLabels=false; view.options.showSilk=false;
    const close=()=>{state=emptySandbox();candidate=null;view.dispose();listeners.forEach(fn=>fn());dialog.close();dialog.remove();opener?.focus();};
    function updateGhost() {
        coordinateError=false;
        ghostLayer.replaceChildren();
        const result=candidate?checkPlacement(state.items,candidate):null;
        $('[data-fit]').textContent=candidate?`${candidate.id}, ${candidate.side==='F.Cu'?'front':'back'}, ${candidate.rotation_mdeg/1000}°. ${messages[result]}`:'Pick an illustration to begin.';
        $('[data-place]').disabled=result!=='ARTISTIC_FIT'; $('[data-cancel]').disabled=!candidate;
        $('[data-x]').value=candidate?candidate.x_nm/1e6:''; $('[data-y]').value=candidate?candidate.y_nm/1e6:'';
        if(candidate) drawItem(ghostLayer,candidate,true,result!=='ARTISTIC_FIT');
    }
    function drawItem(layer,item,ghost=false,bad=false) {
        const group=svgNode('g',{transform:`translate(${item.x_nm/1e6} ${item.y_nm/1e6}) rotate(${item.rotation_mdeg/1000})`},layer);
        const shape=svgNode('rect',{x:-item.width_nm/2e6,y:-item.depth_nm/2e6,width:item.width_nm/1e6,height:item.depth_nm/1e6,
            fill:bad?'#f4b6b6':ghost?'#b5d1ff':item.side==='F.Cu'?'#408b72':'#6680ad',stroke:bad?'#ba3e43':'#2159e8',
            'stroke-width':.3,'fill-opacity':ghost ? 0.6 : 1,'stroke-dasharray':ghost?'1 .5':'none','data-sandbox-item':item.id},group);
        if(!ghost){const title=svgNode('title',{},shape);title.textContent=`${item.id}: ${item.side==='F.Cu'?'front':'back'} illustration`;}
        const label=svgNode('text',{x:0,y:0,'font-size':1.8,'text-anchor':'middle','pointer-events':'none',fill:'#142c3a'},group);label.textContent=item.id;
    }
    function render() {
        itemLayer.replaceChildren();state.items.forEach(item=>drawItem(itemLayer,item));
        $('[data-undo]').disabled=!state.past.length;$('[data-redo]').disabled=!state.future.length;
        const placed=$('[data-placed]');placed.replaceChildren();
        state.items.forEach(item=>{const row=node('div','',placed);const pick=node('button',`${item.id}: ${definitions.find(d=>d.id===item.definition_id).name}`,row);
            pick.onclick=()=>{candidate={...item};updateGhost();map.focus();};
            const remove=node('button',`Remove ${item.id}`,row);remove.onclick=()=>{state=sandboxCommand(state,{kind:'remove',id:item.id});candidate=null;render();};});
        const manifest=sandboxManifest(state,definitions), board=visualBoard(manifest);
        board.components.forEach((part,i)=>{part.side=manifest.instances[i].side;});
        view.setBoard(board);view.setCameraPreset(state.items.at(-1)?.side==='B.Cu'?'back':'iso');
        updateGhost();
    }
    function pickup(definition) {
        candidate={id:`P${++serial}`,definition_id:definition.id,width_nm:Math.round(definition.options.width*1e6),
            depth_nm:Math.round(definition.options.depth*1e6),x_nm:40e6,y_nm:27e6,rotation_mdeg:0,side:'F.Cu'};updateGhost();
    }
    function place() {
        if(!candidate||coordinateError)return;
        try{state=sandboxCommand(state,{kind:'place',item:candidate});candidate=null;render();}
        catch{$('[data-fit]').textContent='Placement rejected. Check overlap, bounds and the 40-illustration scene limit.';}
    }
    function moveTo(event) {
        if(!candidate)return;
        const rect=map.getBoundingClientRect();
        candidate={...candidate,x_nm:snapCoordinate((event.clientX-rect.left)/rect.width*80e6,grid),
            y_nm:snapCoordinate((event.clientY-rect.top)/rect.height*55e6,grid)};updateGhost();
    }
    function inside(event){const r=map.getBoundingClientRect();return event.clientX>=r.left&&event.clientX<=r.right&&event.clientY>=r.top&&event.clientY<=r.bottom;}
    function startPointer(event) {
        if(event.button!==0)return;
        pointer={id:event.pointerId,x:event.clientX,y:event.clientY,moved:false,fromInventory:event.currentTarget.tagName==='BUTTON'};event.currentTarget.setPointerCapture?.(event.pointerId);
    }
    definitions.forEach(def=>{const button=node('button',def.name,$('[data-inventory]'));button.type='button';
        listen(button,'pointerdown',event=>{if(event.button!==0)return;pickup(def);startPointer(event);});
        button.onclick=()=>{if(suppressClick){suppressClick=false;map.focus();return;}pickup(def);map.focus();};});
    listen(map,'pointerdown',event=>{
        if(event.button!==0)return;
        const id=event.target.closest?.('[data-sandbox-item]')?.getAttribute('data-sandbox-item');
        if(id)candidate={...state.items.find(item=>item.id===id)};
        if(candidate){startPointer(event);moveTo(event);}
    });
    listen(document,'pointermove',event=>{
        if(!candidate||pointer?.id!==event.pointerId)return;
        if(Math.hypot(event.clientX-pointer.x,event.clientY-pointer.y)>6)pointer.moved=true;
        if(pointer.moved)moveTo(event);
    });
    listen(document,'pointerup',event=>{
        if(pointer?.id!==event.pointerId)return;
        suppressClick=pointer.fromInventory;pointer=null;
        if(inside(event)){moveTo(event);place();}
    });
    listen(document,'pointercancel',()=>{pointer=null;candidate=null;updateGhost();});
    const cancel=()=>{pointer=null;candidate=null;updateGhost();};
    $('[data-place]').onclick=place;$('[data-cancel]').onclick=cancel;
    const rotate=()=>{if(candidate){candidate={...candidate,rotation_mdeg:(candidate.rotation_mdeg+90000)%360000};updateGhost();}};
    const flip=()=>{if(candidate){candidate={...candidate,side:candidate.side==='F.Cu'?'B.Cu':'F.Cu'};updateGhost();}};
    $('[data-rotate]').onclick=rotate;$('[data-side]').onclick=flip;
    for(const [key,axis] of [['x','x_nm'],['y','y_nm']])$(`[data-${key}]`).onchange=event=>{
        if(!candidate)return;const mm=Number(event.target.value);
        if(event.target.value===''||!Number.isFinite(mm)||Math.abs(mm)>500){coordinateError=true;$('[data-place]').disabled=true;$('[data-fit]').textContent='Enter a finite coordinate between -500 and 500 mm.';return;}
        candidate={...candidate,[axis]:snapCoordinate(mm*1e6,grid)};updateGhost();};
    $('[data-grid]').onchange=event=>{grid=Number(event.target.value);drawGrid();if(candidate){candidate={...candidate,x_nm:snapCoordinate(candidate.x_nm,grid),y_nm:snapCoordinate(candidate.y_nm,grid)};updateGhost();}};
    function drawGrid(){gridLayer.replaceChildren();const step=grid/1e6;for(let x=step;x<80;x+=step)svgNode('path',{d:`M${x} 0V55`,stroke:'#a7c1b7','stroke-width':.04},gridLayer);for(let y=step;y<55;y+=step)svgNode('path',{d:`M0 ${y}H80`,stroke:'#a7c1b7','stroke-width':.04},gridLayer);}
    listen(map,'keydown',event=>{
        if(!candidate)return;const step=grid*(event.shiftKey?10:1);
        const changes={ArrowLeft:['x_nm',-step],ArrowRight:['x_nm',step],ArrowUp:['y_nm',-step],ArrowDown:['y_nm',step]};
        if(changes[event.key]){event.preventDefault();const [key,delta]=changes[event.key];candidate={...candidate,[key]:candidate[key]+delta};updateGhost();}
        else if(event.key.toLowerCase()==='r'){event.preventDefault();rotate();}
        else if(event.key.toLowerCase()==='f'){event.preventDefault();flip();}
        else if(event.key==='Enter'){event.preventDefault();place();}
        else if(event.key==='Escape'){event.preventDefault();event.stopPropagation();cancel();}
    });
    for(const kind of ['undo','redo','reset','discard'])$(`[data-${kind}]`).onclick=()=>{state=sandboxCommand(state,{kind});candidate=null;render();};
    $('[data-close]').onclick=close;
    listen(dialog,'cancel',event=>{event.preventDefault();if(candidate)cancel();else close();});
    drawGrid();render();background.focus?.();
    if(!view.renderer)node('p','3D is unavailable. The placement map and all controls still work.',$('.sandbox-preview'));
}
