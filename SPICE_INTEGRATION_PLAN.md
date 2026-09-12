# SPICE Simulation Integration Plan

## Context
Ohmni currently performs deterministic "semantic" checks against datasheet text (e.g., verifying a pin receives 3.3V based on math). To make it a true enterprise sandbox, we need to validate the physical analog reality of the circuits using SPICE simulation.

The `SpiceTool` Protocol and `SimulationRun` models are already defined in `src/ohmni/adapters/__init__.py`. The `DesignOrchestrator` (in `src/ohmni/generation/orchestrator.py`) currently runs KiCad ERC but skips SPICE.

## Work Items

### 1. `src/ohmni/eda/simulation.py` — NEW
Create a new module to handle netlist export and simulation.

**A. KiCad Netlist Exporter:**
Create a function/class to export a SPICE netlist from the generated `.kicad_sch` file.
* Use `subprocess` to call: `kicad-cli sch export netlist --format spice --output <out.cir> <input.kicad_sch>`
* Return the text content of the generated `.cir` netlist file.

**B. NgspiceAdapter:**
Create a class implementing the `SpiceTool` Protocol that invokes the standalone `ngspice` CLI.
```python
class NgspiceAdapter:
    def __init__(self, executable_path: str = "ngspice"):
        self.executable = executable_path
        
    def availability(self) -> ToolAvailability:
        # Check if self.executable exists (e.g., shutil.which). 
        # Return OK if found, UNAVAILABLE otherwise.
        
    def operating_point(self, netlist: str, run_id: str) -> SimulationRun:
        # 1. Write netlist to a temp file.
        # 2. Append `.op` (operating point) and `.print op` commands to the netlist if missing.
        # 3. Run `ngspice -b <temp_file>` in a subprocess.
        # 4. Parse the stdout for voltage/current nodes.
        # 5. Return a SimulationRun containing the OperatingPoint.
```

### 2. `src/ohmni/generation/models.py` — MODIFY
Update `DesignReport` to include the simulation results.
* Add `simulation: SimulationRun | None = None` to the `DesignReport` model.

### 3. `src/ohmni/generation/orchestrator.py` — MODIFY
Integrate simulation into the design pipeline *after* schematic generation.
* In the `run_eda` block (around line 165), after `KiCadSchematicCompiler.compile(...)` succeeds:
  1. Instantiate the new KiCad netlist exporter and generate the SPICE netlist.
  2. Instantiate `NgspiceAdapter` (checking availability first).
  3. If `ngspice` is available, run `adapter.operating_point()`.
  4. Pass the resulting `SimulationRun` into the `DesignReport`.

### 4. `tests/test_simulation.py` — NEW
* Write unit tests for the SPICE output parser. Provide dummy `ngspice -b` stdout text (e.g., `V(net1) = 3.300000e+00`) and ensure it correctly maps to `OperatingPoint` voltages/currents.
* Write a test for `NgspiceAdapter.availability()` behavior when the CLI is missing.

## Invariants
* If `ngspice` is not installed on the system, the tool must gracefully return `ToolStatus.UNAVAILABLE` and the orchestrator must output the `DesignReport` with `simulation=None` (or a `SimulationRun` with `status=UNAVAILABLE`). It must not crash the generation pipeline.
* Subprocess calls must use list arguments, never `shell=True` strings (SECURITY.md).
