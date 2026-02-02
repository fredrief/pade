# PADE v1.0 Implementation Plan

## Project Structure
```
pade/
├── core/          # Cell, Terminal, Net, Parameter, Testbench
├── stdlib/        # VoltageSource, CurrentSource, Resistor, Capacitor
├── statement/     # Analysis, Options, Save, Include, IC
├── backends/
│   ├── base.py    # Abstract: NetlistWriter, Simulator, NetlistReader
│   ├── spectre/   # Spectre implementation
│   └── ngspice/   # NGspice implementation
├── utils/         # parallel, circuit utilities
├── examples/      # Example testbenches
├── pdk/           # PDK support (SKY130)
└── legacy/        # Old code for reference
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

---

## Current Focus: Open Source Flow (SKY130 + NGspice + Magic)

### Phase 6: SKY130 PDK Integration
1. SKY130 PDK setup and installation docs
2. `backends/ngspice/netlist_reader.py` - Parse SPICE subcircuits
3. `pdk/sky130/` - Device wrappers (nfet, pfet, etc.)
4. SKY130 inverter example: `examples/04_inverter_sky130.ipynb`

### Phase 7: Layout with Magic
1. Magic integration for layout generation
2. Layout-vs-Schematic (LVS) flow
3. Parasitic extraction (PEX)
4. Post-layout simulation

### Phase 8: Factory + API
1. Backend factory function
   - `pade.get_simulator('ngspice', ...)` → NgspiceSimulator
   - Auto-detect available backends
2. Clean public API review
3. Configuration system
   - `pade.config.set_pdk('sky130')`
   - Environment variable support
4. Error handling

### Phase 9: Documentation
1. README.md - Quick start with SKY130
2. Installation guide (NGspice + SKY130 + Magic)
3. API documentation
4. Examples
   - Basic simulation (RC filter)
   - SKY130 inverter
   - Layout flow with Magic

---

## Future: Cadence/Spectre Flow

### Phase 10: Layout (Cadence/Virtuoso)
1. Skillbridge integration
2. Layout compilation flow

### Phase 11: Full Cadence Integration
1. Spectre advanced features
2. Corner/Monte Carlo simulations
3. Virtuoso schematic integration
