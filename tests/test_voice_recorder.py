"""Recorder acceptance: actual electrical data, exact firmware, saved revisions and failure cases."""
import ctypes
import io
import json
import subprocess
import wave

import pytest

from ohmni.application.projects import prepare_project, project_options
from ohmni.application.recorder import FIRMWARE_ROOT, SCENARIOS, firmware_files, simulate_recorder
from ohmni.catalog import default_catalog
from ohmni.domain import CircuitIR
from ohmni.domain.recorder import RECORDER_PINS
from ohmni.physical.placement import generate_placement
from ohmni.synthesis import SynthesisBrief, synthesize
from ohmni.synthesis.a4 import recorder_brief
from ohmni.verifier import verify


@pytest.mark.parametrize('rate',[32000,48000])
@pytest.mark.parametrize('seconds',[1,300,3600])
def test_recording_configuration_is_wired_placeable_and_exported_exactly(rate,seconds):
    brief=recorder_brief(recorder_sample_rate_hz=rate,recorder_max_seconds=seconds)
    r=synthesize(brief); assert r.accepted
    v=verify(r.circuit,default_catalog(),r.requirements)
    assert v.coverage==1 and not v.export_blocked
    assert len(generate_placement(r.circuit,r.placement_request,default_catalog()).board.placements)==25
    assert r.circuit.net_of('SD1','1').name=='SD_3V3'
    assert r.circuit.net_of('MIC1','1').name=='3V3'
    files=firmware_files(brief,r.circuit.content_hash)
    config=files['firmware/main/recorder_config.h'].decode()
    assert f'OHMNI_SAMPLE_RATE {rate}' in config and f'OHMNI_MAX_SECONDS {seconds}' in config
    manifest=json.loads(files['firmware/manifest.json'])
    assert manifest['gpio']==RECORDER_PINS
    assert manifest['brief_fingerprint']==brief.fingerprint
    assert manifest['circuit_hash']==r.circuit.content_hash
    assert manifest['physical_testing']=='NOT_PERFORMED'
    assert files==firmware_files(brief,r.circuit.content_hash)


@pytest.mark.parametrize('signal',['I2S_BCLK','I2S_WS','I2S_DATA','SD_DETECT','BUTTON1','LED1_DRIVE'])
def test_disconnected_or_misassigned_recorder_signals_block_release(signal):
    r=synthesize(recorder_brief());raw=r.circuit.model_dump()
    for net in raw['nets']:
        if net['name']==signal:net['connections']=[p for p in net['connections'] if p['component']!='U1']
    circuit=CircuitIR.model_validate(raw)
    report=verify(circuit,default_catalog(),r.requirements)
    assert report.export_blocked
    assert next(x for x in report.results if x.rule_id=='PB-AUDIO-001').outcome.value=='fail'


def test_wrong_channel_and_voltage_are_rejected():
    r=synthesize(recorder_brief());raw=r.circuit.model_dump()
    for net in raw['nets']:
        net['connections']=[p for p in net['connections'] if (p['component'],p['pin']) not in {('MIC1','1'),('MIC1','6')}]
        if net['name']=='VBUS':net['connections'].append({'component':'MIC1','pin':'1'})
        if net['name']=='3V3':net['connections'].append({'component':'MIC1','pin':'6'})
    report=verify(CircuitIR.model_validate(raw),default_catalog(),r.requirements)
    assert report.export_blocked
    assert {'PB-AUDIO-001','PB-PWR-001'} <= {x.rule_id for x in report.results if x.outcome.value=='fail'}


@pytest.mark.parametrize('change',[{'include_programming_header':False},{'status_led_count':2},{'button_count':0},{'sensors':[{'part_id':'BME280'}]}])
def test_unsupported_recorder_combinations_are_not_silently_ignored(change):
    b=SynthesisBrief.model_validate({**recorder_brief().model_dump(mode="json"),**change})
    assert not synthesize(b).accepted


def test_legacy_fingerprints_and_new_firmware_choices():
    legacy=SynthesisBrief();raw=legacy.model_dump(mode='json')
    raw.pop('recorder_sample_rate_hz');raw.pop('recorder_max_seconds')
    assert SynthesisBrief.model_validate(raw).fingerprint==legacy.fingerprint
    assert recorder_brief().fingerprint!=recorder_brief(recorder_sample_rate_hz=48000).fingerprint
    assert len(project_options()['families'])==4
    _,requirements=prepare_project(recorder_brief())
    assert not any('Firmware is not included' in x for x in requirements.requirements.assumptions)


@pytest.mark.parametrize('scenario',SCENARIOS)
@pytest.mark.parametrize('rate',[32000,48000])
def test_simulation_wav_and_failure_outcomes(scenario,rate):
    result,data=simulate_recorder(recorder_brief(recorder_sample_rate_hz=rate),scenario)
    with wave.open(io.BytesIO(data),'rb') as wav:
        assert (wav.getframerate(),wav.getnchannels(),wav.getsampwidth())==(rate,1,2)
        assert wav.getnframes()==result['saved_samples']
    assert result['queue_peak_bytes']<=result['queue_capacity_bytes']
    assert result['i2s_bclk_hz'] in (2048000,3072000)
    if scenario=='normal':
        assert result['error'] is None and result['duration_seconds']==3
        assert result['saved_samples']==rate*3
    else:
        assert result['outcome']=='ERROR_HANDLED' and result['error']
    assert result['status']=='SIMULATED' and result['limitations']


def test_firmware_portable_core_compiles_and_wav_decodes(tmp_path):
    library=tmp_path/'recorder.so'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-shared','-fPIC',str(FIRMWARE_ROOT/'main/recorder_core.c'),'-o',str(library)],check=True)
    core=ctypes.CDLL(str(library))
    core.ohmni_pcm16.argtypes=[ctypes.c_int32];core.ohmni_pcm16.restype=ctypes.c_int16
    assert [core.ohmni_pcm16(x) for x in (0,2147483647,-2147483648,65536,-65536)]==[0,32767,-32768,1,-1]
    h=(ctypes.c_uint8*44)();core.ohmni_wav_header(h,48000,96000)
    with wave.open(io.BytesIO(bytes(h)+bytes(96000)),'rb') as wav:
        assert wav.getnframes()==48000 and wav.getframerate()==48000
    class Button(ctypes.Structure):
        _fields_=[('raw',ctypes.c_bool),('stable',ctypes.c_bool),('changed_ms',ctypes.c_uint32)]
    core.ohmni_press.argtypes=[ctypes.POINTER(Button),ctypes.c_bool,ctypes.c_uint32]
    core.ohmni_press.restype=ctypes.c_bool
    b=Button()
    events=[(0,True),(5,False),(10,True),(20,False),(25,True),(54,True),(55,True),(100,True),(101,False),(131,False),(140,True),(170,True)]
    assert [t for t,value in events if core.ohmni_press(ctypes.byref(b),value,t)]==[55,170]
    b=Button(False,False,0)
    assert not core.ohmni_press(ctypes.byref(b),True,0xfffffff0)
    assert core.ohmni_press(ctypes.byref(b),True,20)


def test_firmware_storage_finalization_and_failures_use_real_file_io(tmp_path):
    import os
    library=tmp_path/'storage.so'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-shared','-fPIC',
        str(FIRMWARE_ROOT/'main/recorder_core.c'),str(FIRMWARE_ROOT/'main/recorder_storage.c'),'-o',str(library)],check=True)
    core=ctypes.CDLL(str(library))
    core.ohmni_new_file.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t];core.ohmni_new_file.restype=ctypes.c_int
    core.ohmni_write_all.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t];core.ohmni_write_all.restype=ctypes.c_bool
    core.ohmni_finish_file.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_bool];core.ohmni_finish_file.restype=ctypes.c_bool
    (tmp_path/'REC00001.wav').write_bytes(b'keep this existing recording')
    (tmp_path/'REC00002.tmp').write_bytes(b'keep this recovery file')
    path=ctypes.create_string_buffer(512)
    fd=core.ohmni_new_file(os.fsencode(tmp_path),path,512)
    assert fd>=0 and path.value.endswith(b'REC00003.tmp')
    data=bytes(44+64000)
    assert core.ohmni_write_all(fd,data,len(data))
    assert core.ohmni_finish_file(fd,path,32000,64000,True)
    with wave.open(str(tmp_path/'REC00003.wav'),'rb') as wav:
        assert wav.getnframes()==32000 and wav.getsampwidth()==2
    assert not (tmp_path/'REC00003.tmp').exists()
    assert (tmp_path/'REC00001.wav').read_bytes()==b'keep this existing recording'
    assert (tmp_path/'REC00002.tmp').read_bytes()==b'keep this recovery file'
    for capture_ok, close_early in [(False,False),(True,True)]:
        fd=core.ohmni_new_file(os.fsencode(tmp_path),path,512)
        assert fd>=0
        assert core.ohmni_write_all(fd,bytes(44),44)
        if close_early: os.close(fd)
        assert not core.ohmni_finish_file(fd,path,32000,0,capture_ok)
        from pathlib import Path
        assert Path(os.fsdecode(path.value)).exists()
        assert not Path(os.fsdecode(path.value)).with_suffix('.wav').exists()
    assert core.ohmni_new_file(os.fsencode(tmp_path/'missing'),path,512)==-1
    assert not core.ohmni_write_all(-1,b'x',1)


def test_pre_recorder_saved_project_reopens_and_can_be_edited(tmp_path):
    from ohmni.application.conversation import BoardPlan
    from ohmni.application.iteration import ProjectAssistant
    from ohmni.application.project_store import ProjectStore
    from ohmni.application.projects import preview_project
    b=SynthesisBrief();raw=b.model_dump(mode="json")
    raw.pop("recorder_sample_rate_hz");raw.pop("recorder_max_seconds")
    store=ProjectStore(tmp_path)
    project=store.save_revision(raw,b.fingerprint,preview_project(b).model_dump(mode="json"))
    rev=project["revisions"][0]
    assert rev["brief_fingerprint"]==b.fingerprint
    assert rev["brief"]["recorder_sample_rate_hz"]==32000
    class Provider:
        def generate_structured(self,request,schema):
            changed=SynthesisBrief.model_validate({**request.data["context"]["brief"],"project_name":"Renamed legacy project"})
            return schema.model_validate({"kind":"change","proposal":BoardPlan(brief=changed).model_dump(mode="json")})
    assistant=ProjectAssistant(Provider(),store,None)
    turn=assistant.ask(project["project_id"],rev["revision_id"],"Rename this project")
    assert turn["ready"] and [c["field"] for c in turn["changes"]]==["project_name"]
    saved=assistant.apply(project["project_id"],rev["revision_id"],turn["turn_id"])
    assert len(saved["revisions"])==2 and saved["revisions"][-1]["brief"]["project_name"]=="Renamed legacy project"


def test_recorder_export_manifest_rejects_missing_changed_and_escaped_files(tmp_path):
    import hashlib
    import zipfile

    from test_project_api import _seed_package

    from ohmni.application.project_store import ProjectStore
    from ohmni.application.recorder import write_recorder_artifacts
    from scripts.demo_server import JobStore
    b=recorder_brief();store,job,directory=_seed_package(tmp_path,brief=b)
    durable=ProjectStore(tmp_path)
    project=durable.save_revision(b.model_dump(mode='json'),b.fingerprint,{})
    revision=project['revisions'][0]['revision_id']
    durable.claim_job(project['project_id'],revision,JobStore._queued_record(job))
    report=store.jobs[job]['report']
    recorder=write_recorder_artifacts(directory,b,report['project']['circuit_hash'])
    report['project']['recorder']=recorder
    durable.save_job(store.jobs[job]);store.project_store=durable
    status,data=store.read_build_package(job)
    assert status=='current'
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name,digest in recorder['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==digest
        assert 'main/main.c' not in archive.namelist()
        assert b'physical' in archive.read('firmware/README.md')
    target=directory/'firmware/main/main.c';original=target.read_bytes()
    target.write_bytes(original+b'\n// tampered')
    assert store.read_build_package(job)[1] is None
    target.write_bytes(original)
    recorder=store.jobs[job]['report']['project']['recorder']
    removed=recorder['files'].pop('firmware/main/main.c')
    durable.save_job(store.jobs[job])
    assert store.read_build_package(job)[1] is None
    store.jobs[job]['report']['project']['recorder']['files']['firmware/main/main.c']=removed
    durable.save_job(store.jobs[job])
    target.unlink();outside=tmp_path/'outside.c';outside.write_bytes(original);target.symlink_to(outside)
    assert store.read_build_package(job)[1] is None
    target.unlink();target.write_bytes(original)
    assert store.read_build_package(job)[0]=='current'


def test_module_assembly_is_for_oriented_headers_not_bare_chips():
    from ohmni.bom.service import classify_assembly, generate_bom
    catalog=default_catalog();circuit=synthesize(recorder_brief()).circuit
    report=classify_assembly(generate_bom(circuit,catalog),catalog)
    modules=[risk for risk in report.risks if {'MIC1','SD1'} & set(risk.references)]
    assert len(modules)==2
    assert all(risk.difficulty.value=='easy' and risk.orientation_sensitive for risk in modules)
    assert all('standoff' in risk.detail and 'Bare chips' in risk.detail for risk in modules)


@pytest.mark.parametrize('part_id,filename,header',[
    ('ADAFRUIT_3421','Adafruit I2S Mic SPK0415HM4H.brd','JP2'),
    ('ADAFRUIT_4682_SDHC','Adafruit SDIO microSD.brd','JP1')])
def test_module_carrier_contacts_match_manufacturer_cad_including_mirrored_header(part_id,filename,header):
    import xml.etree.ElementTree as ET
    from pathlib import Path

    from ohmni.physical.footprints import footprint
    source=Path(__file__).parents[1]/'src/ohmni/catalog/data/recorder'/filename
    root=ET.parse(source)
    element=root.find(f'.//elements/element[@name="{header}"]')
    package=root.find(f'.//library[@name="{element.get("library")}"]/packages/package[@name="{element.get("package")}"]')
    edges=root.findall('.//board/plain/wire[@layer="20"]')
    xs=[float(e.get(key)) for e in edges for key in ('x1','x2')]
    ys=[float(e.get(key)) for e in edges for key in ('y1','y2')]
    cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
    mirror=-1 if element.get('rot','R0')=='MR0' else 1
    expected={p.get('name'):(float(element.get('x'))+mirror*float(p.get('x'))-cx,
        cy-float(element.get('y'))-float(p.get('y'))) for p in package.findall('pad')}
    part=default_catalog().require(part_id)
    geometry=footprint(part.packages[0].kicad_footprint)
    assert len(geometry.pads)==len(expected)==len(part.pins)
    for pad in geometry.pads:assert (pad.x_mm,pad.y_mm)==pytest.approx(expected[pad.number])
    assert geometry.width_mm==pytest.approx(max(xs)-min(xs)+1)
    assert geometry.height_mm==pytest.approx(max(ys)-min(ys)+1)
