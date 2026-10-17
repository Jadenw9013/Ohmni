import test from 'node:test';
import assert from 'node:assert/strict';
import {accessToken, validateBoard} from '../fetch-workspace.js';
test('workspace token comes from fragment or tab storage, never a query', () => {
    const token = 'a'.repeat(43), values = new Map();
    const storage = {getItem:k=>values.get(k), setItem:(k,v)=>values.set(k,v)};
    assert.equal(accessToken({hash:'#access='+token}, storage), token);
    assert.equal(accessToken({hash:''}, storage), token);
    assert.throws(()=>accessToken({hash:'#access=wrong'}, storage));
    assert.throws(()=>accessToken({hash:'',search:'?access='+token}, null));
});
test('board projection must own every selectable component', () => {
    const data = {job_id:'abcdef123456',experience:{board:{components:[{ref:'U1'}]},components:[{ref:'U1'}]}};
    assert.equal(validateBoard(data), data);
    assert.throws(()=>validateBoard({...data,experience:{...data.experience,components:[{ref:'OTHER'}]}}));
});
