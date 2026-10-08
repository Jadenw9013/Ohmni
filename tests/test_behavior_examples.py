from pathlib import Path

import pytest

from ohmni.behavior.examples import compile_reference, load_reference_circuits
from ohmni.behavior.loader import BehaviorRegistry, BehaviorRegistryError
from ohmni.behavior.netlist import load_recipes

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def references():
    registry=BehaviorRegistry(repo_root=ROOT);recipes=load_recipes(registry,ROOT)
    return registry,recipes,load_reference_circuits(registry,recipes,ROOT)


def test_all_reference_circuits_reproduce_authored_probes_and_measure_only_used_roles(references):
    registry,recipes,data=references
    assert len(data['examples'])==92
    for key,row in data['examples'].items():
        original,_=compile_reference(row,registry,recipes,measure_currents=False)
        measured,_=compile_reference(row,registry,recipes)
        assert original.runnable and measured.runnable,(key,measured.problems)
        assert original.netlist_sha256==row['original_netlist_sha256']
        assert measured.netlist_sha256!=original.netlist_sha256
        for component in measured.components:
            assert not set(component.role_current_probes)&{'NC','NC1','NC2'}
            assert set(component.role_current_probes)<=set(component.role_nodes)
            assert len(set(component.role_current_probes.values()))==len(component.role_current_probes)


@pytest.mark.parametrize('measure_currents',[False,True])
def test_reference_input_cannot_silently_change(references,measure_currents):
    registry,recipes,data=references
    row=dict(data['examples']['OHM-004'],original_netlist_sha256='0'*64)
    with pytest.raises(BehaviorRegistryError,match='authored probe'):
        compile_reference(row,registry,recipes,measure_currents=measure_currents)
