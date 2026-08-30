"""Project-local footprint geometry derived from pinned KiCad library sources.

Only pad geometry needed by the golden project is retained. Source hashes bind
each subset to the inspected upstream KiCad 10 footprint file; no runtime global
library lookup is performed.
"""

from .models import FootprintDefinition, FootprintPad, FootprintSource

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
    source=_src("Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", "5f2993c50dbd5024384bf6fa972fcd10d40d0837039e1e371b326a27d9f5b8b7"),
    pads=[FootprintPad(number=str(i), x_mm=0, y_mm=(i-1)*2.54, width_mm=1.7, height_mm=1.7, kind="thru_hole", shape="circle") for i in range(1,7)]))

_usb_xy={"A1":(-3.25,-4.045),"A4":(-2.45,-4.045),"A5":(-1.25,-4.045),"A6":(-.25,-4.045),"A7":(.25,-4.045),"A8":(1.25,-4.045),"A9":(2.45,-4.045),"A12":(3.25,-4.045),"B1":(3.25,-4.045),"B4":(2.45,-4.045),"B5":(1.75,-4.045),"B6":(.75,-4.045),"B7":(-.75,-4.045),"B8":(-1.75,-4.045),"B9":(-2.45,-4.045),"B12":(-3.25,-4.045)}
_register(FootprintDefinition(footprint_id="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", width_mm=10, height_mm=8,
    source=_src("Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "c562a7f9713a8b754c4d2305a2ea15453469a1c8c48a9b17973383e8993fc750"),
    pads=[FootprintPad(number=n,x_mm=x,y_mm=y,width_mm=.6 if n[1:] in {"1","4","9","12"} else .3,height_mm=1.45) for n,(x,y) in _usb_xy.items()] + [FootprintPad(number="SH",x_mm=x,y_mm=y,width_mm=1,height_mm=2,kind="thru_hole",shape="oval",mechanical=True) for x,y in [(-4.32,-3.13),(-4.32,1.05),(4.32,-3.13),(4.32,1.05)] ]))


def footprint(footprint_id: str) -> FootprintDefinition | None:
    return FOOTPRINTS.get(footprint_id)

