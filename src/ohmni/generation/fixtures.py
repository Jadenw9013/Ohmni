"""Deterministic scripted model responses for the milestone demo."""

from ..adapters.fakes import RecordingLlmProvider
from ..catalog import default_catalog
from ..fixtures.esp32_env_logger import broken_sensor_on_5v, requirements
from ..verifier import verify

GOLDEN_REQUEST = (
    "Build an ESP32 environmental logger using the BME280. Power it from USB-C, "
    "keep it around $20, use a 2-layer PCB, and prefer parts I can hand solder."
)


def flawed_logger_provider() -> RecordingLlmProvider:
    provider = RecordingLlmProvider()
    circuit = broken_sensor_on_5v()
    req = requirements()
    report = verify(circuit, default_catalog(), req)
    blocking_ids = [f.finding_id for f in report.findings if f.severity.value in {"critical", "error"}]
    provider.queue({
        "project_name": "ESP32 environmental logger", "description": GOLDEN_REQUEST,
        "max_input_voltage_v": 5.25, "target_logic_voltage_v": 3.3,
        "budget_usd": 20, "max_board_layers": 2, "hand_solderable": True,
        "interfaces": ["i2c", "uart", "usb_power_sink"],
        "required_part_ids": ["ESP32-WROOM-32E", "BME280"],
        "functional_requirements": ["Measure environmental conditions", "Provide a status LED"],
        "assumptions": ["USB-C is used as a 5 V sink without Power Delivery"],
    })
    provider.queue({
        "blocks": [
            {"block_id": "usb", "purpose": "5 V USB-C power", "selected_part_id": "USB_C_RECEPTACLE_16P"},
            {"block_id": "regulator", "purpose": "3.3 V regulation", "selected_part_id": "AP2112K-3.3TRG1"},
            {"block_id": "compute", "purpose": "logging compute", "selected_part_id": "ESP32-WROOM-32E", "required_interfaces": ["i2c"]},
            {"block_id": "sensor", "purpose": "environment sensing", "selected_part_id": "BME280", "required_interfaces": ["i2c"], "required_rails": ["VDD", "VDDIO"]},
        ],
        "relationships": [{"source_block": "compute", "target_block": "sensor", "interface": "i2c"}],
    })
    provider.queue({"circuit": circuit.model_dump(mode="json"), "architecture_block_ids": ["usb", "regulator", "compute", "sensor"], "rationale": ["Use known catalog parts only"]})
    provider.queue({
        "original_circuit_hash": circuit.content_hash,
        "triggering_finding_ids": blocking_ids,
        "operations": [
            {"operation": "move_pin", "component_ref": "U3", "pin": "6", "from_net": "VBUS", "to_net": "3V3"},
            {"operation": "move_pin", "component_ref": "U3", "pin": "8", "from_net": "VBUS", "to_net": "3V3"},
        ],
        "rationale": "Move both BME280 supply domains to the verified 3.3 V rail.",
    })
    return provider
