"""Controller authoring schematic with space for the real 100-pin symbol.

The generic compiler's 76.2 mm cells suit the small existing catalog. A 100-pin
symbol occupies 124.46 mm vertically, so sharing those cells would place pin
labels on a preceding symbol. Move whole instances and their pin bindings
together; net names, pin roles and connectivity remain unchanged.
"""

from ohmni.eda.kicad.compiler import KiCadSchematicCompiler


class ControllerSchematicCompiler(KiCadSchematicCompiler):
    def _instance(self, circuit, instance, spec, x, y, root_uuid, project, connected):
        if len(spec.pins) > 100:
            raise ValueError("Controller authoring layout supports at most 100 pins")
        return super()._instance(
            circuit, instance, spec, x, y * 3, root_uuid, project, connected,
        )
