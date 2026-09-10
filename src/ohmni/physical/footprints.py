"""Project-local footprint geometry derived from pinned KiCad library sources.

Only the pad geometry and placement envelopes needed by the catalog are retained. Source hashes bind
each subset to the inspected upstream KiCad 10 footprint file; no runtime global
library lookup is performed.
"""

import hashlib
import json
from collections.abc import Iterable

from .models import FootprintDefinition, FootprintDrill, FootprintPad, FootprintSource

LICENSE = "KiCad footprint libraries, CC-BY-SA-4.0 with KiCad library exception"


def _src(library_id: str, digest: str) -> FootprintSource:
    return FootprintSource(library_id=library_id, upstream_file_sha256=digest,
                           license=LICENSE, derivation="pad geometry subset derived from pinned upstream KiCad 10 footprint")


def _two(footprint_id, digest, pitch, width, height):
    return FootprintDefinition(footprint_id=footprint_id, width_mm=width, height_mm=height,
        source=_src(footprint_id, digest), pads=[
            FootprintPad(number="1", x_mm=-pitch/2, y_mm=0, width_mm=1.0, height_mm=1.4),
            FootprintPad(number="2", x_mm=pitch/2, y_mm=0, width_mm=1.0, height_mm=1.4),
        ])


FOOTPRINTS = {
    "Resistor_SMD:R_0805_2012Metric": _two("Resistor_SMD:R_0805_2012Metric", "f050b6a50cc7e6f86291fb7aa8f87b0d02255e21cfbddf291cdccc87e5889794", 1.825, 2.0, 1.5),
    "Capacitor_SMD:C_0805_2012Metric": _two("Capacitor_SMD:C_0805_2012Metric", "62775a51fe74ba7f1b572de327bdbd3fc92582721b2abcaa47787865590d89cb", 1.9, 2.0, 1.5),
    "LED_SMD:LED_0805_2012Metric": _two("LED_SMD:LED_0805_2012Metric", "8806125556e590701b13b47a1725dff28fc47fca41a7905c7d78c8312d08cbbd", 1.875, 2.0, 1.5),
}


def _register(definition):
    FOOTPRINTS[definition.footprint_id] = definition


_register(FootprintDefinition(footprint_id="Package_TO_SOT_SMD:SOT-23-5", width_mm=3.0, height_mm=3.2,
    source=_src("Package_TO_SOT_SMD:SOT-23-5", "455a3f7c3e5eb5b8847eaa5df23e18651e78ab9f75afd09a0883758a0d901761"),
    pads=[FootprintPad(number=str(i+1), x_mm=(-1.1375 if i<3 else 1.1375), y_mm=(-.95,0,.95,.95,-.95)[i], width_mm=1.325, height_mm=.6) for i in range(5)]))

_register(FootprintDefinition(footprint_id="Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering", width_mm=2.5, height_mm=2.5,
    source=_src("Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering", "14464b7a437e7efb0fa9947b89a7d3825242f3ed82d649fe2ca45fad5d3dda86"),
    pads=[FootprintPad(number=str(i+1), x_mm=x, y_mm=y, width_mm=.35, height_mm=.5, shape="rect") for i,(x,y) in enumerate([(-.975,-1.025),(-.325,-1.025),(.325,-1.025),(.975,-1.025),(.975,1.025),(.325,1.025),(-.325,1.025),(-.975,1.025)])]))

_esp_pads = []
for i in range(1, 15): _esp_pads.append(FootprintPad(number=str(i), x_mm=-8.75, y_mm=-8.25+(i-1)*1.27, width_mm=1.5, height_mm=.9, shape="rect"))
for i in range(15, 25): _esp_pads.append(FootprintPad(number=str(i), x_mm=-5.71+(i-15)*1.27, y_mm=9.51, width_mm=.9, height_mm=1.5, shape="rect"))
for i in range(25, 39): _esp_pads.append(FootprintPad(number=str(i), x_mm=8.75, y_mm=8.26-(i-25)*1.27, width_mm=1.5, height_mm=.9, shape="rect"))
_esp_pads.append(FootprintPad(number="39", x_mm=-.68, y_mm=-.91, width_mm=4.2, height_mm=4.2, shape="rect"))
_register(FootprintDefinition(footprint_id="RF_Module:ESP32-WROOM-32", width_mm=19.5, height_mm=20.5,
    source=_src("RF_Module:ESP32-WROOM-32", "af11e3ded30556624b02dbdb6b72e7ee6ec829fa0c549365b154eb273f7dbf7c"), pads=_esp_pads))

_register(FootprintDefinition(footprint_id="Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", width_mm=2.54, height_mm=15.24,
    source=_src("Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", "e3c3501f520fc1fc39eeb5d72137e680e509c0df2348ca77fef1b9db6ab974f0"),
    pads=[FootprintPad(number=str(i), x_mm=0, y_mm=(i-1)*2.54, width_mm=1.7, height_mm=1.7,
                       kind="thru_hole", shape="rect" if i == 1 else "circle",
                       drill=FootprintDrill(shape="circle", width_mm=1, height_mm=1)) for i in range(1,7)]))

_usb_xy={"A1":(-3.25,-4.045),"A4":(-2.45,-4.045),"A5":(-1.25,-4.045),"A6":(-.25,-4.045),"A7":(.25,-4.045),"A8":(1.25,-4.045),"A9":(2.45,-4.045),"A12":(3.25,-4.045),"B1":(3.25,-4.045),"B4":(2.45,-4.045),"B5":(1.75,-4.045),"B6":(.75,-4.045),"B7":(-.75,-4.045),"B8":(-1.75,-4.045),"B9":(-2.45,-4.045),"B12":(-3.25,-4.045)}
_register(FootprintDefinition(footprint_id="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", width_mm=10, height_mm=8,
    source=_src("Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "8d292db4e16dbd391bfc6c79366047ce1799e687d970810736a41426e88619b3"),
    pads=[FootprintPad(number=n,x_mm=x,y_mm=y,width_mm=.6 if n[1:] in {"1","4","9","12"} else .3,height_mm=1.45) for n,(x,y) in _usb_xy.items()]
         + [FootprintPad(number="SH",x_mm=x,y_mm=y,width_mm=1,height_mm=height,
                         kind="thru_hole",shape="oval",mechanical=True,
                         drill=FootprintDrill(shape="oval",width_mm=.6,height_mm=drill_height))
            for x,y,height,drill_height in [(-4.32,-3.13,2.1,1.7),(-4.32,1.05,1.6,1.2),
                                           (4.32,-3.13,2.1,1.7),(4.32,1.05,1.6,1.2)]]
         + [FootprintPad(number="",x_mm=x,y_mm=-2.6,width_mm=.65,height_mm=.65,
                         kind="np_thru_hole",shape="circle",mechanical=True,
                         drill=FootprintDrill(shape="circle",width_mm=.65,height_mm=.65)) for x in (-2.89,2.89)]))


def _chip(footprint_id, digest, x, pad_width, pad_height, width, height):
    """Retain actual lands; use the upstream courtyard's bounding rectangle."""
    return FootprintDefinition(
        footprint_id=footprint_id, width_mm=width, height_mm=height,
        source=_src(footprint_id, digest), pads=[
            FootprintPad(number=str(i), x_mm=px, y_mm=0,
                         width_mm=pad_width, height_mm=pad_height)
            for i, px in ((1, -x), (2, x))
        ],
    )


# Existing 0805 definitions remain unchanged for accepted artifact compatibility.
# Additional packages use exact upstream lands and conservative courtyard bounds.
for _id, _hash, _x, _pw, _ph, _w, _h in (
    ("Resistor_SMD:R_0402_1005Metric", "6ed88b70926af431471c0ccaf6a55485f8cedab01cce4d1d4f3298a6cb6cef2c", .51, .54, .64, 1.86, .94),
    ("Resistor_SMD:R_0603_1608Metric", "03fc7902b2661df01b4d828fdb6eab9eddf974e7130ed2b98892607387a50c4b", .825, .8, .95, 2.96, 1.46),
    ("Resistor_SMD:R_1206_3216Metric", "f45a0f7c60b15463e1126a75a9ff484349ecd1861de62f1cbff41574e03b7643", 1.4625, 1.125, 1.75, 4.56, 2.26),
    ("Capacitor_SMD:C_0402_1005Metric", "3d8a1dc70b71dbc3a5786560f7f9d0cabe99f1182653b072cde5046e4e3f6fc4", .48, .56, .62, 1.82, .92),
    ("Capacitor_SMD:C_0603_1608Metric", "d45eebd5cb9faace255d4ec95a0f9484efde898359507b02e2ba9bbb3ef6d857", .775, .9, .95, 2.96, 1.46),
    ("Capacitor_SMD:C_1206_3216Metric", "420c3ac494743fbc47653b6e7d0107d51620e25c77eaf73f083e799807fd1381", 1.475, 1.15, 1.8, 4.6, 2.3),
    ("LED_SMD:LED_0603_1608Metric", "923edc26771553cc36919e187c64d599da73e11c1f4f3e52c80b86512036faff", .7875, .875, .95, 2.96, 1.46),
):
    _register(_chip(_id, _hash, _x, _pw, _ph, _w, _h))

_register(FootprintDefinition(
    footprint_id="Package_TO_SOT_SMD:SOT-23", width_mm=3.86, height_mm=3.4,
    source=_src("Package_TO_SOT_SMD:SOT-23", "7fb2859c6463f3a37966a1a20c31d8bfe7d4e8459d00bb165d5a7488270816c5"),
    pads=[FootprintPad(number=str(i), x_mm=x, y_mm=y, width_mm=1.475, height_mm=.6)
          for i, x, y in ((1, -.9375, -.95), (2, -.9375, .95), (3, .9375, 0))],
))

_register(FootprintDefinition(
    footprint_id="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", width_mm=7.4, height_mm=5.4,
    source=_src("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "3c9b63198dd4dbf5e6c28c84702c29fad46a35103b821a19306c4ac888ad8e76"),
    pads=[FootprintPad(number=str(i), x_mm=x, y_mm=y, width_mm=1.95, height_mm=.6)
          for i, x, y in ((1, -2.475, -1.905), (2, -2.475, -.635), (3, -2.475, .635),
                          (4, -2.475, 1.905), (5, 2.475, 1.905), (6, 2.475, .635),
                          (7, 2.475, -.635), (8, 2.475, -1.905))],
))

_register(FootprintDefinition(
    footprint_id="Package_TO_SOT_SMD:SOT-563", width_mm=2.4, height_mm=1.9,
    source=_src("Package_TO_SOT_SMD:SOT-563", "5db336475df2eb434a83572346092efba42569eff34d06282fa8f90bf3b786a4"),
    pads=[FootprintPad(number=str(i), x_mm=x, y_mm=y, width_mm=.675, height_mm=.35)
          for i, x, y in ((1, -.7125, -.5), (2, -.7125, 0), (3, -.7125, .5),
                          (4, .7125, .5), (5, .7125, 0), (6, .7125, -.5))],
))

_button_source = _src("Button_Switch_THT:SW_PUSH_6mm", "e284d5bbfb435ef0ad577512ffc7da06ea7cf5c87753287922d89e84c7f4a2a7")
_button_source.derivation += (
    "; all coordinates translated by (-3.25, -2.25) mm to center the courtyard; "
    "the four 2 mm circular lands retain duplicate terminal numbers and 1.1 mm drills"
)
_register(FootprintDefinition(
    footprint_id="Button_Switch_THT:SW_PUSH_6mm", width_mm=9.5, height_mm=7.5,
    source=_button_source,
    pads=[FootprintPad(number=n, x_mm=x, y_mm=y, width_mm=2, height_mm=2,
                       kind="thru_hole", shape="circle",
                       drill=FootprintDrill(shape="circle",width_mm=1.1,height_mm=1.1))
          for n, x, y in (("1", -3.25, -2.25), ("1", 3.25, -2.25),
                          ("2", -3.25, 2.25), ("2", 3.25, 2.25))],
))


def footprint(footprint_id: str) -> FootprintDefinition | None:
    return FOOTPRINTS.get(footprint_id)


def footprint_geometry_fingerprint(footprint_ids: Iterable[str] | None = None) -> str:
    """Bind a compiled set of footprints to its current complete local geometry."""
    identifiers = sorted(FOOTPRINTS if footprint_ids is None else set(footprint_ids))
    unknown = set(identifiers) - FOOTPRINTS.keys()
    if unknown:
        raise ValueError(f"unknown footprint geometry: {sorted(unknown)}")
    geometry = {identifier: FOOTPRINTS[identifier].content_hash for identifier in identifiers}
    return hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
