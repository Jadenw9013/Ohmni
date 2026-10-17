import test from 'node:test';
import assert from 'node:assert/strict';
import {connectWorkspace} from '../connected-session.js';

test('claim is removed from URL before network and exchanged for a cookie session',async()=>{
    const order=[];
    const location={hash:'#connect='+'a'.repeat(43),pathname:'/',search:''};
    const history={replaceState(_a,_b,url){order.push('strip');assert.equal(url,'/#workspace');location.hash='#workspace';}};
    let attempt=0;
    const fetcher=async(url,options)=>{
        assert.equal(url,'/connected/session');assert.equal(options.credentials,'same-origin');
        assert.equal(options.headers['X-Ohmni-Client'],'main-ui');
        assert.equal(JSON.parse(options.body).claim,'a'.repeat(43));
        assert.equal(order[0],'strip');
        if(!attempt++)throw new Error('network');
        return {ok:true,json:async()=>({connected:true,project_id:'1'.repeat(16)})};
    };
    await assert.rejects(connectWorkspace({fetcher,location,history}),/network/);
    await connectWorkspace({fetcher,location,history});
    assert.equal(globalThis.OHMNI_API_BASE,'/connected');
    assert.equal(globalThis.OHMNI_OPEN_PROJECT,'1'.repeat(16));
});
