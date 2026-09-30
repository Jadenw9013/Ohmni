import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { emptySandbox, sandboxCommand, checkPlacement, snapCoordinate, sandboxManifest } from '../sandbox-model.js';

const part = (patch = {}) => ({ id:'P1',definition_id:'capacitor/0805',x_nm:20e6,y_nm:20e6,
    width_nm:4e6,depth_nm:2e6,rotation_mdeg:0,side:'F.Cu',...patch });
const place = (state,item=part()) => sandboxCommand(state,{kind:'place',item});

test('all supported grids yield integer scene coordinates',()=>{
    assert.equal(snapCoordinate(1234567,250000),1250000);
    assert.equal(snapCoordinate(1234567,500000),1000000);
    assert.equal(snapCoordinate(1567890,1000000),2000000);
    for(const n of [NaN,Infinity,'12',null,true])assert.throws(()=>snapCoordinate(n,1000000));
    assert.throws(()=>snapCoordinate(10,123));
});

test('overlaps, out-of-bounds boxes, malformed and authority-bearing items are rejected',()=>{
    const s=place(emptySandbox());
    assert.equal(checkPlacement(s.items,part({id:'P2',x_nm:21e6})),'OVERLAP');
    assert.equal(checkPlacement([],part({x_nm:1e6})),'OUTSIDE');
    assert.equal(checkPlacement([],part({x_nm:81e6})),'OUTSIDE');
    assert.equal(checkPlacement([],part({y_nm:55e6})),'OUTSIDE');
    for(const patch of [{x_nm:NaN},{x_nm:1.2},{x_nm:true},{rotation_mdeg:45},{side:'unknown'},
        {width_nm:0},{verified:'PASS'},{evidence:{status:'PASS'}}]) {
        assert.equal(checkPlacement([],part(patch)),'INVALID_INPUT');
        assert.throws(()=>place(s,part(patch)));
    }
    assert.throws(()=>place(s,part({id:'P2',x_nm:21e6})));
    assert.equal(s.items.length,1);
});

test('quarter-turn bounds are checked and front/back feedback stays explicitly artistic',()=>{
    const long=part({width_nm:10e6,depth_nm:2e6,x_nm:2e6,rotation_mdeg:90000});
    assert.equal(checkPlacement([],long),'ARTISTIC_FIT');
    assert.equal(checkPlacement([],{...long,rotation_mdeg:0}),'OUTSIDE');
    const other=part({id:'P2',x_nm:20e6,y_nm:24e6});
    assert.equal(checkPlacement([other],part({width_nm:10e6,depth_nm:2e6})),'ARTISTIC_FIT');
    assert.equal(checkPlacement([other],part({width_nm:10e6,depth_nm:2e6,rotation_mdeg:90000})),'OVERLAP');
    assert.equal(checkPlacement([part()],part({id:'P2',side:'B.Cu'})),'ARTISTIC_FIT');
});

test('move, undo, redo, reset and discard preserve exact scene contents without mutating the base',()=>{
    const empty=emptySandbox(), first=place(empty), before=JSON.stringify(first);
    const moved=place(first,part({x_nm:30e6,rotation_mdeg:90000,side:'B.Cu'}));
    assert.equal(JSON.stringify(first),before);
    assert.deepEqual(sandboxCommand(moved,{kind:'undo'}).items,first.items);
    assert.deepEqual(sandboxCommand(sandboxCommand(moved,{kind:'undo'}),{kind:'redo'}).items,moved.items);
    const reset=sandboxCommand(moved,{kind:'reset'});
    assert.equal(reset.items.length,0);
    assert.deepEqual(sandboxCommand(reset,{kind:'undo'}).items,moved.items);
    assert.deepEqual(sandboxCommand(moved,{kind:'discard'}),emptySandbox());
    assert.deepEqual(empty.items,[]);
    assert.throws(()=>first.items.push(part({id:'P2'})));
});

test('branching clears redo and changing an existing illustration identity fails',()=>{
    const first=place(emptySandbox()), next=place(first,part({x_nm:30e6}));
    const undone=sandboxCommand(next,{kind:'undo'}), branch=place(undone,part({x_nm:40e6}));
    assert.equal(branch.future.length,0);
    assert.throws(()=>place(first,part({definition_id:'other'})));
    assert.throws(()=>place(first,part({width_nm:1e6})));
    assert.throws(()=>sandboxCommand(first,{kind:'commit_project'}));
    assert.deepEqual(sandboxCommand(first,{kind:'remove',id:'P1'}).items,[]);
});

test('history and number of placed illustrations are bounded',()=>{
    let state=emptySandbox();
    for(let i=0;i<40;i++) state=place(state,part({id:`P${i}`,x_nm:(i%10)*6e6+5e6,y_nm:Math.floor(i/10)*5e6+5e6}));
    assert.throws(()=>place(state,part({id:'P40',x_nm:70e6,y_nm:50e6})));
    state=emptySandbox();
    for(let i=0;i<110;i++)state=place(state,part({x_nm:(20+i%2)*1e6}));
    assert.equal(state.past.length,100);
});

test('3D projection keeps side and rotation without creating electrical geometry',()=>{
    const state=place(emptySandbox(),part({x_nm:10e6,y_nm:15e6,rotation_mdeg:90000,side:'B.Cu'}));
    const definitions=[{id:'capacitor/0805',name:'Capacitor',family:'ceramic_chip',options:{width:4,depth:2,height:1}}];
    const before=JSON.stringify(state), manifest=sandboxManifest(state,definitions);
    assert.equal(manifest.provenance,'ILLUSTRATIVE_ONLY');
    assert.deepEqual([manifest.instances[0].x,manifest.instances[0].y,manifest.instances[0].rotation,manifest.instances[0].side],[-30,12.5,-90,'B.Cu']);
    assert.deepEqual([manifest.pads,manifest.tracks,manifest.vias],[[],[],[]]);
    manifest.instances[0].options.width=99;
    assert.equal(definitions[0].options.width,4);
    assert.equal(JSON.stringify(state),before);
});

test('sandbox has no network or persistence path and pointer moves only update the ghost',()=>{
    for(const file of ['component-sandbox.js','sandbox-model.js']) {
        const source=readFileSync(new URL(`../${file}`,import.meta.url),'utf8');
        assert.doesNotMatch(source,/\bfetch\s*\(|localStorage|sessionStorage|indexedDB|\/api\/projects/);
    }
    const source=readFileSync(new URL('../component-sandbox.js',import.meta.url),'utf8');
    const move=source.split("listen(document,'pointermove'")[1].split("listen(document,'pointerup'")[0];
    assert.doesNotMatch(move,/setBoard|render\(/);
    assert.match(source,/pointercancel/);
    assert.match(source,/state=emptySandbox\(\);candidate=null;view.dispose\(\)/);
});
