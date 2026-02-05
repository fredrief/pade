# PADE Agent Onboarding

Instructions and context for AI agents working on this project.

## Project Overview

**PADE** (Python Analog Design Environment) is a Python framework for analog/mixed-signal IC design. It provides a unified interface for schematic capture, layout, simulation, and physical verification (DRC/LVS/PEX).

### Core Principles

1. **Tool and PDK independence**: The core `pade/` library must remain completely independent of any specific simulator or PDK. All tool-specific and PDK-specific code lives in `examples/` or user projects.

2. **Backend architecture**: Different tools (NGspice, Spectre, Magic, etc.) are supported through backend modules. Adding a new simulator or layout tool should only require implementing a new backend, not modifying core code.

3. **Simplicity over features**: Keep the API minimal and intuitive. Prefer fewer, well-designed abstractions over comprehensive coverage.

4. **Self-contained examples**: The `examples/` directory serves as both documentation and testing. Tutorials should demonstrate complete workflows that users can follow.

### Directory Structure

```
pade/                    # Core library (tool/PDK independent)
├── core/                # Cell, Terminal, Net, Parameter, Testbench
├── backends/            # Simulator and tool backends
│   ├── ngspice/         # NGspice netlist writer, reader, simulator
│   ├── spectre/         # Cadence Spectre support
│   ├── gds/             # GDSII layout writer
│   └── magic/           # Magic layout writer
├── layout/              # Layout primitives (LayoutCell, Shape, Port)
├── statement.py         # Simulation statements (Analysis, Save, etc.)
├── stdlib.py            # Standard library (V, I sources)
└── utils/               # Utilities

examples/                # PDK-specific code and tutorials
├── pdk/sky130/          # SKY130 PDK implementation
│   ├── config.py        # PDK paths and configuration
│   ├── primitives/      # Transistors, capacitors, etc.
│   └── pex.py           # PEX decorator
├── src/                 # User designs
│   ├── testbenches/     # Testbench definitions
│   └── runners/         # Simulation runners
├── utils/               # Verification tools (DRC, LVS, PEX)
└── tutorials/           # Jupyter notebooks
```

### Key Abstractions

- **Cell**: Schematic component with terminals, nets, parameters, and subcells
- **LayoutCell**: Layout component with shapes, ports, and subcells
- **Backend writers**: Convert Cell/LayoutCell to tool-specific formats
- **Statement**: Simulation control (analyses, saves, options)
- **Runner**: Orchestrates simulation setup, execution, and post-processing

## Development Philosophy

### No Backwards Compatibility

This is a new project under active development. There are no users to break. Always choose the best implementation, even if it requires major rewrites. We will not be in a stable state for a long time.

### Minimal Overhead

- Tutorials serve as tests
- Comments only when necessary for understanding
- No verbose docstrings
- No formal testing framework (yet)
- Move fast, iterate quickly

### Architecture First

When adding features:
1. Consider how it fits the overall architecture
2. Ensure tool/PDK independence is maintained
3. Prefer patterns that scale to other tools/PDKs

## Code Style

### Conciseness

- Prefer short, clear code over verbose explanations
- Delete dead code immediately
- Remove unused imports, parameters, comments
- If you discover cleanup opportunities, do them (don't ask)

### Comments

- Minimal comments - code should be self-explanatory
- No section dividers (`# ========`)
- No "for backwards compatibility" patterns
- No placeholder comments like "can be extended later"

### Module Organization

- Keep `__init__.py` files minimal (docstring only, no exports)
- Users import directly: `from pade.core.cell import Cell`
- Consolidate small related modules into single files when sensible

### Patterns

**Decorators for optional functionality:**
```python
CapMimM4 = pex_enabled(load_subckt('cap_mim_m4.spice'))
```

**Runners for complex flows:**
```python
runner = CapRunner(w=10, l=10)
result = runner.run_and_evaluate('postlayout', pex={'C1': 'rc'})
```

**kwargs propagation for configuration:**
```python
# Settings flow through hierarchy
tb = MyTestbench(pex={'C1': 'rc'}, ...)
```

## Collaboration Style

### Discuss Before Implementing

For non-trivial changes, discuss the approach first. Present options with pros/cons. Wait for agreement before writing code.

### Be Direct

- Skip polite filler
- State facts and technical assessments directly
- Disagree when you see a better approach
- Ask clarifying questions when requirements are ambiguous

### Cleanup Always

When you notice:
- Unused imports or parameters
- Dead code
- Verbose comments
- Inconsistent patterns

Just fix them. Mention in your summary. Don't ask permission.

### Minimal Examples

When demonstrating code or creating examples, keep them minimal. Show only what's necessary to illustrate the point.

## Current State

### Working

- Schematic capture with Cell hierarchy
- NGspice and Spectre simulation
- Layout with GDS export
- DRC/LVS/PEX flow with Magic/Netgen
- SKY130 MiM capacitor complete flow (tutorial 04)

### Placeholder/TODO

- Transistor layout (raises NotImplementedError)
- More SKY130 primitives
- Cadence layout flow

### Future Plans

- Commercial PDK support (keep core independent!)
- More complete Cadence/Spectre flow
- Additional open-source PDKs

## Quick Reference

### Running Tutorials

```bash
cd examples/tutorials
jupyter notebook
```

Tutorials require SKY130 PDK installed (see `docs/INSTALL_SKY130.md`).

### Key Files to Understand

1. `pade/core/cell.py` - Core Cell abstraction
2. `pade/backends/ngspice/netlist_writer.py` - How netlists are generated
3. `examples/pdk/sky130/pex.py` - PEX decorator pattern
4. `examples/tutorials/04_mim_capacitor_sky130.ipynb` - Complete flow example

### Common Patterns

**Creating a testbench:**
```python
class MyTB(Testbench):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.V1 = V('V1', self, dc=1.8)
        self.V1.connect(['p', 'n'], ['vdd', '0'])
```

**Running simulation:**
```python
sim = NgspiceSimulator(output_dir=config.sim_data_dir)
raw = sim.simulate(tb, statements, 'run_name')
```

**Physical verification:**
```python
design = DesignRunner(layout, schematic)
result = design.run_all()  # DRC + LVS + PEX
```
