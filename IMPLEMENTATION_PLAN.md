# PADE v1.0 Implementation Plan

## Project Structure
```
pade/
├── core/          # Cell, Terminal, Net, Parameter, Testbench
├── stdlib/        # VoltageSource, CurrentSource, Resistor, Capacitor
├── statement/     # Analysis, Options, Save, Include, IC
├── backends/
│   ├── base.py    # Abstract: NetlistWriter, Simulator, NetlistReader, LayoutWriter
│   ├── spectre/   # Spectre implementation
│   ├── ngspice/   # NGspice implementation
│   └── magic/     # Magic layout implementation (Phase 7)
├── utils/         # parallel, circuit utilities
└── logging.py     # Logging utilities

examples/
├── pdk/sky130/    # SKY130 device wrappers
├── testbenches/   # Example testbenches
└── *.ipynb        # Notebook examples
```

## Completed

### Phase 1: Core Classes ✓
- Terminal, Net, Parameter, Cell, Testbench

### Phase 2: Spectre Backend + Stdlib ✓
- `stdlib/sources.py`, `stdlib/passives.py`
- `backends/base.py` - NetlistWriter, Simulator
- `backends/spectre/netlist_writer.py`
- `backends/spectre/simulator.py`

### Phase 3: Statements + Simulation Flow ✓
- `statement/` - Statement, Analysis, Options, Save, Include, IC
- Simulation run flow with live output

### Phase 4: NGspice Backend ✓
- `backends/ngspice/netlist_writer.py` - SPICE netlist format
- `backends/ngspice/simulator.py` - Run ngspice, return path
- Public example: `examples/02_ngspice_rc.ipynb`

### Phase 5: Spectre Netlist Reading ✓
- `backends/base.py` - Abstract NetlistReader
- `backends/spectre/netlist_reader.py` - Parse .scs subcircuits
- `load_subckt()` function and `NetlistCell` class
- GF130 inverter example: `examples/03_inverter_gf130.ipynb`

### Phase 6: SKY130 PDK Integration ✓
1. SKY130 PDK setup and installation script (`scripts/install_sky130.sh`)
2. `backends/ngspice/netlist_reader.py` - Parse SPICE subcircuits
3. Device wrappers as SPICE files (`examples/pdk/sky130/*.spice`)
4. SKY130 inverter example: `examples/03_inverter_sky130.ipynb`
5. Documentation: `docs/INSTALL_SKY130.md`

---

## Current Focus: Layout with Magic

### Phase 7: Core Layout + DRC
1. `backends/base.py` - Abstract LayoutWriter class
2. `backends/magic/layout_writer.py` - Magic TCL script generation
3. Basic layout primitives (rectangles, labels, ports)
4. Cell hierarchy support
5. DRC check integration
6. SKY130 layout example

### Phase 8: LVS + PEX + Post-Layout Simulation
1. Layout-vs-Schematic (LVS) with netgen
2. Parasitic extraction (PEX) with Magic
3. Post-layout simulation flow
4. Back-annotated netlist handling

---

## Future Phases

### Phase 9: Factory + API
1. Backend factory function
   - `pade.get_simulator('ngspice', ...)` → NgspiceSimulator
   - Auto-detect available backends
2. Clean public API review
3. Configuration system
   - `pade.config.set_pdk('sky130')`
   - Environment variable support
4. Error handling

### Phase 10: Documentation & Polish
1. README.md - Quick start with SKY130
2. Installation guide (NGspice + SKY130 + Magic)
3. API documentation
4. Examples
   - Basic simulation (RC filter)
   - SKY130 inverter
   - Layout flow with Magic
5. Polish `__init__.py` exports for clean public API

---

## Future: Cadence/Spectre Flow

### Phase 11: Layout (Cadence/Virtuoso)
1. Skillbridge integration
2. Layout compilation flow

### Phase 12: Full Cadence Integration
1. Spectre advanced features
2. Corner/Monte Carlo simulations
3. Virtuoso schematic integration
