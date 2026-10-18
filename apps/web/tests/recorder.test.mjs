import test from 'node:test';
import assert from 'node:assert/strict';
import {createAsset,createMaterials} from '../visual-assets.js';
import {packageBinding} from '../visual-board-scene.js';
import {recorderPanelHtml} from '../recorder-panel.js';
import {supportedBrief,sameBrief,briefChanges} from '../project-contract.js';

const brief={schema_version:1,project_name:'Recorder',description:'Mono WAV recording',archetype:'a4_usb_voice_recorder',input_power:'usb_c_5v',input_voltage_v:5,logic_voltage_v:3.3,mcu_part_id:'ESP32-WROOM-32E',sensors:[],spi_devices:[],status_led_count:1,button_count:1,include_programming_header:true,max_board_layers:2,hand_solderable_preferred:false,budget_usd:null,safety_domains:[],recorder_sample_rate_hz:32000,recorder_max_seconds:300};
test('recorder revision settings are retained and constrained',()=>{
    assert.ok(supportedBrief(brief));
    assert.ok(!supportedBrief({...brief,recorder_sample_rate_hz:16000}));
    assert.ok(!supportedBrief({...brief,recorder_max_seconds:0}));
    assert.ok(!sameBrief(brief,{...brief,recorder_sample_rate_hz:48000}));
    assert.ok(briefChanges(brief,{...brief,recorder_max_seconds:60}).length);
});
test('recorder components have distinct 3D models and exact source contacts',()=>{
    for(const [id,family,n] of [['ADAFRUIT_3421','i2s_microphone',6],['ADAFRUIT_4682_SDHC','microsd_module',9]]){
        assert.equal(packageBinding({part_id:id}),family);
        const pads=Array.from({length:n},(_,i)=>({number:String(i+1),x_mm:i*2.54,y_mm:3,width_mm:1.8,height_mm:1.8,kind:"thru_hole"}));
        const asset=createAsset(family,{pads},createMaterials());
        assert.equal(asset.userData.sourceContacts.length,n);
        assert.deepEqual(asset.userData.sourceContacts,pads.map(({number,x_mm,y_mm})=>({number,x_mm,y_mm})));
        let meshes=0;asset.traverse(o=>{if(o.isMesh){meshes++;assert.ok(o.geometry.attributes.position.count>0);}});
        assert.ok(meshes>=5);
        assert.equal(asset.getObjectByName("source-position gold recorder pins").count,n);
    }
});
test('simulation UI labels synthetic evidence and escapes external text',()=>{
    assert.equal(recorderPanelHtml(null),'');
    const html=recorderPanelHtml({simulations:[{scenario:'normal'},{scenario:'<script>'}]});
    assert.match(html,/synthetic sound/);assert.match(html,/physical audio and power testing are pending/);
    assert.ok(!html.includes('<script>'));assert.match(html,/microphone|Firmware/);
});
