import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { homeRoute, HOME_GUIDES, initializeHome } from '../home.js';

function harness(hash = '') {
    const nodes = new Map(), listeners = {};
    function node(selector) {
        if (!nodes.has(selector)) nodes.set(selector, { hidden:false, open:false, textContent:'', children:[], dataset:{}, handlers:{},
            setAttribute(k,v){this[k]=v;}, focus(){this.focused=true;},
            replaceChildren(){this.children=[];}, append(...children){this.children.push(...children);},
            showModal(){this.open=true;}, close(){this.open=false; this.handlers.close?.();},
            addEventListener(k,fn){this.handlers[k]=fn;} });
        return nodes.get(selector);
    }
    const groups = {'[data-home-start]':[node('start'),node('get-started')], '[data-home-demo]':[node('demo')],
        '[data-home-info]':Object.keys(HOME_GUIDES).map(kind=>{const n=node(kind); n.dataset.homeInfo=kind; return n;})};
    node('#home').querySelectorAll=selector=>groups[selector]??[];
    node('#home').querySelector=node;
    const originals=Object.fromEntries(['document','window','location','history'].map(k=>[k,globalThis[k]]));
    Object.assign(globalThis,{document:{querySelector:node,createElement:tag=>({tag,textContent:''}),title:''},
        window:{addEventListener:(k,fn)=>{listeners[k]=fn;},scrollTo(){}}, location:{hash},
        history:{pushState:(_,__,next)=>{location.hash=next;}}});
    return {node,groups,listeners,restore(){for(const[k,v]of Object.entries(originals)){if(v===undefined)delete globalThis[k];else globalThis[k]=v;}}};
}

test('home routes separate workspace and historical demo URLs without guessing a project',()=>{
    for(const hash of ['', '#home', '#unrecognized'])assert.equal(homeRoute(hash),'home');
    for(const hash of ['#workspace','#sample-board','#visual-proof'])assert.equal(homeRoute(hash),'workspace');
});

test('loading a landing or workspace URL never creates a project or starts a demo',()=>{
    for(const hash of ['', '#workspace']){
        const h=harness(hash);let starts=0,demos=0;
        try{initializeHome({onStart:()=>starts++,onDemo:()=>demos++});assert.equal(starts,0);assert.equal(demos,0);
            assert.equal(h.node('#home').hidden,hash==='#workspace');
        }finally{h.restore();}
    }
});

test('both build entries invoke the project flow while demo invokes only its own callback',()=>{
    const h=harness();let starts=0,demos=0;
    try{initializeHome({onStart:()=>starts++,onDemo:()=>demos++});
        for(const n of h.groups['[data-home-start]'])n.handlers.click({preventDefault(){}});
        assert.equal(starts,2);assert.equal(demos,0);assert.equal(location.hash,'#workspace');
        h.node('demo').handlers.click({preventDefault(){}});assert.equal(starts,2);assert.equal(demos,1);
    }finally{h.restore();}
});

test('guide opens with actual explanatory text and close restores its initiating control',()=>{
    const h=harness();
    try{initializeHome();h.node('checks').handlers.click();assert.equal(h.node('#home-info').open,true);
        const text=h.node('#home-info-content').children.map(n=>n.textContent).join(' ');
        assert.match(text,/Missing evidence never counts as a pass/);assert.match(text,/have not been bench-tested/);
        h.node('[data-home-info-close]').handlers.click();assert.equal(h.node('#home-info').open,false);assert.equal(h.node('checks').focused,true);
        h.node('limits').handlers.click();assert.match(h.node('#home-info-content').children.map(n=>n.textContent).join(' '),/generated concept illustration/);
    }finally{h.restore();}
});

test('history navigation closes guides, changes focus and leaves the mounted workbench alone',()=>{
    const h=harness();const retained=h.node('.app-layout');retained.draft='unsaved draft';
    try{initializeHome();h.node('docs').handlers.click();location.hash='#workspace';h.listeners.hashchange();
        assert.equal(h.node('#home-info').open,false);assert.equal(h.node('.app-layout'),retained);assert.equal(retained.draft,'unsaved draft');
        assert.equal(h.node('.stage:not([hidden]) h1').focused,true);location.hash='#home';h.listeners.hashchange();
        assert.equal(h.node('#home-title').focused,true);assert.equal(retained.draft,'unsaved draft');
    }finally{h.restore();}
});

test('reference artwork is local, explicitly illustrative, and every visible action has a handler',()=>{
    const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
    const home=html.slice(html.indexOf('<section id="home"'),html.indexOf('<div class="app-layout"'));
    assert.match(home,/src="\/landing-board.png"/);assert.match(home,/Concept illustration/);
    assert.equal((home.match(/data-home-start/g)||[]).length,2);
    assert.equal((home.match(/data-home-demo/g)||[]).length,2);
    for(const query of ['BME280','ESP32','USB_C'])assert.ok(home.includes(`data-component-query="${query}"`));
    const png=readFileSync(new URL('../landing-board.png',import.meta.url));assert.equal(png.subarray(1,4).toString(),'PNG');
    assert.ok(HOME_GUIDES.docs.sections.some(([,body])=>body.includes('Unsaved changes')));
});
