import json
import threading
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore

OPENER=build_opener(ProxyHandler({}))


@pytest.fixture
def server(tmp_path):
    value=DemoHTTPServer(('127.0.0.1',0),DemoHandler,store=JobStore(tmp_path))
    thread=threading.Thread(target=value.serve_forever,daemon=True);thread.start()
    try:yield value,f'http://127.0.0.1:{value.server_port}'
    finally:value.shutdown();value.server_close();thread.join(timeout=2)


def request(base,path,payload=None):
    req=Request(base+path,data=json.dumps(payload).encode() if payload is not None else None,
                headers={'Content-Type':'application/json'})
    try:
        with OPENER.open(req,timeout=10) as response:return response.status,json.loads(response.read())
    except HTTPError as error:return error.code,json.loads(error.read())


def test_reference_api_preserves_identity_and_refuses_arbitrary_input(server):
    service,base=server;identity=service._identity()
    assert request(base,'/api/behavior/OHM-004/run',{})[0]==400
    assert request(base,'/api/behavior/OHM-004/run',dict(identity,netlist='.shell bad'))[0]==400
    assert request(base,'/api/behavior/OHM-004/run',dict(identity,ui_version='0'*64))[0]==409
    assert service.behavior_service is None
    assert request(base,'/api/projects')[1]['projects']==[]


def test_blocked_behavior_is_explicit_and_cannot_create_a_project(server):
    service,base=server;identity=service._identity()
    code,body=request(base,'/api/behavior/OHM-083')
    assert code==200 and body['component']['available'] is False
    assert body['component']['source_status']=='research_required'
    assert body['component']['blockers']
    code,body=request(base,'/api/behavior/OHM-083/run',identity)
    assert code==200 and body['result']['status']=='not_run'
    assert body['result']['rating_status']=='not_run'
    assert body['server_instance_id']==identity['server_instance_id']
    assert request(base,'/api/projects')[1]['projects']==[]


def test_backend_failures_do_not_expose_private_paths(server):
    service,base=server
    class Broken:
        def describe(self,_entry):raise RuntimeError('C:/private/source.txt token=secret')
    service.behavior_service=Broken()
    code,body=request(base,'/api/behavior/OHM-004')
    assert code==503 and body=={'error':'behavior_run_unavailable'}


def test_behavior_summary_matches_the_audited_coverage_rule(server):
    service,base=server
    code,body=request(base,'/api/behavior')
    assert code==200 and len(body['entries'])==180
    states=[value['state'] for value in body['entries'].values()]
    assert states.count('simulated')==42
    assert body['entries']['OHM-057']=={'state':'simulated','reason':None}
    assert body['entries']['OHM-103']['state']=='reference_only' and body['entries']['OHM-103']['reason']
    assert body['entries']['OHM-083']['state']=='documented'
    code,body=request(base,'/api/behavior/OHM-057')
    assert body['component']['behavior_state']=='simulated'
