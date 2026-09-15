"""The shared project contract covers each implemented hardware family."""

import io
import json
import time
import zipfile
from urllib.request import Request

import pytest
from test_project_api import OPENER, _request, _server

from ohmni.application.demo import DemoPipeline, _evidence_rows
from ohmni.application.project_requirements import project_requirement_results
from ohmni.application.projects import prepare_project, preview_project, project_options
from ohmni.domain import CircuitIR
from ohmni.physical.placement import generate_placement
from ohmni.synthesis import I2cSensorSlot, SynthesisBrief, synthesize
from ohmni.verifier import verify


def _briefs():
    return [SynthesisBrief.model_validate(family["defaults"]) for family in project_options()["families"]]


def test_options_offer_complete_supported_defaults_and_auto_address_slots():
    options=project_options()
    assert options["schema_version"]==1 and len(options["families"])==3
    assert {sensor["part_id"]:sensor["addresses"] for sensor in options["sensors"]}=={
        "BME280":[0x76,0x77],"TMP102AIDRLR":[0x48,0x49]}
    for family in options["families"]:
        brief=SynthesisBrief.model_validate(family["defaults"])
        assert brief.archetype.value==family["id"] and synthesize(brief).accepted
        slots=tuple(I2cSensorSlot.model_validate(slot) for slot in family["sensor_slot_defaults"])
        largest=brief.model_copy(update={"sensors":slots,"status_led_count":family["status_led_count"]["max"],
                                       "button_count":family["button_count"]["max"],
                                       "spi_devices":brief.spi_devices*family["spi_count"]["max"]})
        assert len(slots)==family["sensor_count"]["max"] and synthesize(largest).accepted


@pytest.mark.parametrize("brief",_briefs(),ids=lambda brief:brief.archetype.value)
def test_every_confirmed_choice_is_preserved_and_outcomes_are_narrow(brief,catalog):
    brief=brief.model_copy(update={"description":"Invented free-text capability: fly to Mars", "budget_usd":None})
    circuit,requirements=prepare_project(brief)
    result=synthesize(brief)
    semantic=verify(circuit,catalog,requirements.requirements)
    board=generate_placement(circuit,result.placement_request,catalog).board
    rows=project_requirement_results(brief,requirements,circuit,semantic,board,catalog)
    by_field={row["field"]:row for row in rows}
    fields={"project_name","description","archetype","input_power","input_voltage_v","logic_voltage_v",
            "mcu_part_id","sensor_count","status_led_count","button_count","spi_count",
            "include_programming_header","max_board_layers","hand_solderable_preferred","budget_usd","safety_domains"}
    assert fields<=by_field.keys()
    assert all(row["status"] in {"MET","VIOLATED","UNKNOWN"} for row in rows)
    assert by_field["mcu_part_id"]["status"]=="MET"
    assert by_field["input_power"]["display_value"]=="USB-C power, 5 V"
    assert by_field["input_power"]["value"]=="usb_c_5v"
    assert by_field["include_programming_header"]["display_value"]=="Yes"
    assert by_field["logic_voltage_v"]["display_value"].endswith(" V")
    assert by_field["description"]["value"]==brief.description and by_field["description"]["status"]=="UNKNOWN"
    assert by_field["budget_usd"]["status"]=="UNKNOWN"
    assert by_field["status_led_count"]["status"]==by_field["button_count"]["status"]=="MET"
    assert by_field["hand_solderable_preferred"]["status"]==("VIOLATED" if brief.sensors else "MET")
    assert by_field["hand_solderable_preferred"]["rule_ids"]==["PB-ID-005"]
    preview=preview_project(brief)
    assert preview.request==brief.description
    if not brief.sensors:
        assert not any("BME280" in row.value for row in preview.assumed)
    assert {row["component"] for row in _evidence_rows(catalog,circuit)}=={part.part_id for part in circuit.components}
    semantic.results=[]
    unknown=project_requirement_results(brief,requirements,circuit,semantic,board,catalog)
    assert next(row for row in unknown if row["field"]=="hand_solderable_preferred")["status"]=="UNKNOWN"


def test_statuses_detect_actual_missing_part_and_reject_unrelated_verification(catalog):
    brief=_briefs()[1]
    circuit,requirements=prepare_project(brief)
    result=synthesize(brief);board=generate_placement(circuit,result.placement_request,catalog).board
    values=circuit.model_dump()
    values["components"]=[part for part in values["components"] if part["ref"]!="D1"]
    for net in values["nets"]:net["connections"]=[pin for pin in net["connections"] if pin["component"]!="D1"]
    changed=CircuitIR.model_validate(values)
    semantic=verify(changed,catalog,requirements.requirements)
    rows=project_requirement_results(brief,requirements,changed,semantic,board,catalog)
    assert next(row for row in rows if row["field"]=="status_led_count")["status"]=="VIOLATED"
    with pytest.raises(ValueError,match="same circuit"):
        project_requirement_results(brief,requirements,circuit,semantic,board,catalog)


def test_options_identity_and_all_family_revisions_survive_restart(tmp_path):
    saved=[]
    with _server(tmp_path) as (server,base):
        identity=server._identity()
        status,response=_request(base,"/api/project-options")
        assert status==200 and response["options"]==project_options()
        status,response=_request(base,"/api/project-options",headers={"X-Ohmni-Server-Instance":"stale"})
        # Header validation uses the same identity protocol as project reads.
        assert status==409 and response["error"]=="server_instance_mismatch"
        for brief in _briefs():
            status,response=_request(base,"/api/projects",{**identity,"brief":brief.model_dump(mode="json")})
            assert status==201
            saved.append(response["project"])
    with _server(tmp_path) as (_server_instance,base):
        for project in saved:
            status,response=_request(base,f"/api/projects/{project['project_id']}")
            assert status==200 and response["project"]==project


def test_invalid_family_combinations_are_refused_without_a_saved_revision(tmp_path):
    a1,a2,a3=_briefs()
    invalid=[a1.model_copy(update={"sensors":(I2cSensorSlot(part_id="BME280",address=0x76),)*2}),
             a2.model_copy(update={"sensors":a1.sensors*2}),
             a3.model_copy(update={"spi_devices":a3.spi_devices*3})]
    with _server(tmp_path) as (server,base):
        for brief in invalid:
            status,response=_request(base,"/api/projects",{**server._identity(),"brief":brief.model_dump(mode="json")})
            assert status==422 and response["error"]=="project_refused"
            assert response["refusal"]["field_paths"]
        assert _request(base,"/api/projects")[1]["projects"]==[]


@pytest.mark.slow_integration
@pytest.mark.kicad
@pytest.mark.parametrize("brief",_briefs(),ids=lambda brief:brief.archetype.value)
def test_every_family_creates_runs_reopens_and_exports_through_the_real_api(tmp_path,monkeypatch,brief):
    from ohmni.adapters.tools import find_kicad_cli
    if find_kicad_cli() is None:pytest.skip("KiCad unavailable")
    def scripted_path_forbidden(*_args,**_kwargs):
        raise AssertionError("personal projects must not call the scripted demo pipeline")
    monkeypatch.setattr(DemoPipeline,"run",scripted_path_forbidden)
    with _server(tmp_path) as (server,base):
        identity=server._identity()
        status,response=_request(base,"/api/projects",{**identity,"brief":brief.model_dump(mode="json")})
        assert status==201
        project=response["project"];revision=project["revisions"][0]
        run_path=f"/api/projects/{project['project_id']}/revisions/{revision['revision_id']}/run"
        status,response=_request(base,run_path,identity)
        assert status==202
        job_id=response["job_id"];deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            status,job=_request(base,f"/api/jobs/{job_id}")
            assert status==200
            if job["status"] in {"complete","failed"}:break
            time.sleep(.05)
        assert job["status"]=="complete",job
        report=job["report"]
        assert report["mode"]=="bounded_synthesis" and report["project"]["archetype"]==brief.archetype.value
        assert report["project"]["brief_fingerprint"]==brief.fingerprint
        assert report["release"]["current"] and report["pcb"]["violations"]==report["pcb"]["unrouted"]==0
        assert any(row["status"]=="UNKNOWN" and row["field"]=="budget_usd" for row in report["requirements"])
        with OPENER.open(Request(base+f"/api/artifacts/{job_id}/build-package.zip"),timeout=30) as response:
            archive=zipfile.ZipFile(io.BytesIO(response.read()))
        assert SynthesisBrief.model_validate(json.loads(archive.read("confirmed-brief.json"))).fingerprint==brief.fingerprint
        assert json.loads(archive.read("report.json"))["project"]["archetype"]==brief.archetype.value
        assert _request(base,run_path,identity)[1]["job_id"]==job_id
    with _server(tmp_path) as (_restarted,base):
        status,job=_request(base,f"/api/jobs/{job_id}")
        assert status==200 and job["status"]=="complete" and job["report"]["release"]["current"]
        with OPENER.open(Request(base+f"/api/artifacts/{job_id}/build-package.zip"),timeout=30) as response:
            assert response.status==200
