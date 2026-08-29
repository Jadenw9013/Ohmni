"""CircuitIR referential integrity and content hashing."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from proofboard.domain import (
    CircuitComponent,
    CircuitIR,
    Net,
    NetKind,
    PinRef,
    Quantity,
)


def _ir(**overrides) -> CircuitIR:
    base = {
        "ir_id": "t",
        "name": "test",
        "components": [
            CircuitComponent(ref="R1", part_id="GENERIC_RESISTOR", value=Quantity.ohms(1000)),
            CircuitComponent(ref="R2", part_id="GENERIC_RESISTOR", value=Quantity.ohms(1000)),
        ],
        "nets": [
            Net(name="A", connections=[PinRef(component="R1", pin="1"), PinRef(component="R2", pin="1")]),
        ],
    }
    base.update(overrides)
    return CircuitIR(**base)


class TestReferentialIntegrity:
    def test_duplicate_component_refs_are_rejected(self):
        with pytest.raises(ValidationError, match="duplicate component references"):
            _ir(
                components=[
                    CircuitComponent(ref="R1", part_id="GENERIC_RESISTOR"),
                    CircuitComponent(ref="R1", part_id="GENERIC_RESISTOR"),
                ],
                nets=[],
            )

    def test_duplicate_net_names_are_rejected(self):
        with pytest.raises(ValidationError, match="duplicate net names"):
            _ir(nets=[Net(name="A"), Net(name="A")])

    def test_connection_to_an_unknown_component_is_rejected(self):
        with pytest.raises(ValidationError, match="unknown component"):
            _ir(nets=[Net(name="A", connections=[PinRef(component="U99", pin="1")])])

    def test_a_pin_cannot_be_on_two_nets(self):
        # Physically impossible, and it silently breaks every net-based rule.
        with pytest.raises(ValidationError, match="is on two nets"):
            _ir(
                nets=[
                    Net(name="A", connections=[PinRef(component="R1", pin="1")]),
                    Net(name="B", connections=[PinRef(component="R1", pin="1")]),
                ]
            )

    def test_a_net_cannot_list_the_same_pin_twice(self):
        with pytest.raises(ValidationError, match="same pin more than once"):
            Net(
                name="A",
                connections=[PinRef(component="R1", pin="1"), PinRef(component="R1", pin="1")],
            )

    def test_a_signal_net_cannot_carry_an_external_supply(self):
        with pytest.raises(ValidationError, match="marked as a signal net"):
            Net.model_validate(
                {
                    "name": "VBUS",
                    "kind": "signal",
                    "external_source": {
                        "kind": "usb_vbus",
                        "voltage": {"minimum": "4.75V", "maximum": "5.25V"},
                    },
                }
            )

    def test_pin_existence_is_not_checked_here(self):
        # Deliberate: that needs the catalog, and the domain layer must not
        # reach for infrastructure. PB-ID-002 owns it instead.
        ir = _ir(nets=[Net(name="A", connections=[PinRef(component="R1", pin="99")])])
        assert ir.net("A") is not None


class TestContentHash:
    def test_same_content_same_hash(self):
        assert _ir().content_hash == _ir().content_hash

    def test_hash_ignores_bookkeeping(self):
        # Revision, parent hash and free-text notes describe the history, not
        # the design. Two identical circuits must collide regardless.
        a = _ir()
        b = _ir(revision=7, parent_hash="deadbeef", notes="reworked")
        assert a.content_hash == b.content_hash

    def test_hash_ignores_ordering(self):
        a = _ir()
        b = _ir(
            components=list(reversed(_ir().components)),
            nets=[
                Net(
                    name="A",
                    connections=[
                        PinRef(component="R2", pin="1"),
                        PinRef(component="R1", pin="1"),
                    ],
                )
            ],
        )
        assert a.content_hash == b.content_hash

    def test_hash_changes_when_topology_changes(self):
        a = _ir()
        b = _ir(
            nets=[
                Net(
                    name="A",
                    connections=[
                        PinRef(component="R1", pin="1"),
                        PinRef(component="R2", pin="2"),
                    ],
                )
            ]
        )
        assert a.content_hash != b.content_hash

    def test_hash_changes_when_a_value_changes(self):
        a = _ir()
        b = _ir(
            components=[
                CircuitComponent(ref="R1", part_id="GENERIC_RESISTOR", value=Quantity.ohms(2200)),
                CircuitComponent(ref="R2", part_id="GENERIC_RESISTOR", value=Quantity.ohms(1000)),
            ]
        )
        assert a.content_hash != b.content_hash

    def test_hash_supports_oscillation_detection(self, golden):
        # The repair loop needs to notice when a patch lands on a state it has
        # already been in. That only works if a round trip collides.
        from proofboard.fixtures.esp32_env_logger import broken_missing_i2c_pullups

        seen = {golden.content_hash}
        broken = broken_missing_i2c_pullups()
        assert broken.content_hash not in seen
        seen.add(broken.content_hash)
        # "Repairing" back to the original returns to a state already seen.
        assert golden.content_hash in seen


class TestLookups:
    def test_net_of_finds_the_owning_net(self, golden):
        net = golden.net_of("U3", "8")
        assert net is not None
        assert net.name == "3V3"

    def test_ground_and_power_nets(self, golden):
        assert [n.name for n in golden.ground_nets] == ["GND"]
        assert sorted(n.name for n in golden.power_nets) == ["3V3", "VBUS"]

    def test_golden_declares_a_usb_source_with_tolerance(self, golden):
        vbus = golden.net("VBUS")
        assert vbus is not None
        assert vbus.external_source is not None
        assert vbus.external_source.voltage.minimum == Quantity.volts(4.75)
        assert vbus.external_source.voltage.maximum == Quantity.volts(5.25)
        assert vbus.kind is NetKind.POWER
