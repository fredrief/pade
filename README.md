# PADE — Programmatic Analog Design Environment

PADE is a Python framework for analog/mixed-signal IC design. It provides a
code-first environment for schematic capture, layout generation, simulation,
and verification.

## Features

- **Hierarchical schematic model** — cells, terminals, nets, parameters; compose circuits as Python classes
- **Layout engine** — rectangles, refs, pins, compass-based placement, transforms (move/rotate/mirror)
- **Router** — L-shaped and jogged metal routing with net-aware connectivity
- **Schematic–layout integration** — connectivity checker and short-circuit detection
- **Simulation backends** — NGspice (included in devcontainer), Spectre (bring your own license)
- **Layout I/O** — GDS export/import via gdstk, Magic `.mag` export

## Quick Start (VS Code + DevContainer)

This is the recommended setup. The DevContainer includes all open-source EDA tools
(ngspice, klayout, magic, netgen, yosys, iverilog) and the SKY130 PDK — zero manual
configuration.

**Prerequisites:** [VS Code](https://code.visualstudio.com/) with the
[Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
extension, and [Docker](https://www.docker.com/).

```bash
git clone https://github.com/fredrief/pade.git
cd pade
code .
```

When VS Code prompts **"Reopen in Container"**, click it. The first build takes a few
minutes (pulls the base image, installs dependencies). Subsequent opens are fast.

Once inside the container, open `examples/tutorials/01_core_pade.ipynb` and run it.

## Alternative: Docker Without VS Code

Build and run the container directly:

```bash
docker build -t pade -f .devcontainer/Dockerfile .
docker run -it --rm -v "$(pwd)":/workspaces/pade -w /workspaces/pade pade bash
pip install -e '.[dev]'
pip install jupyter
jupyter notebook --ip=0.0.0.0 --no-browser --allow-root
```

## Alternative: Native Install

For users who manage their own EDA tool installations.

```bash
pip install -e '.[dev]'
```

Core dependencies (`numpy`, `scipy`, `shapely`, `gdstk`) are installed automatically.
For simulation and verification you need the relevant tools on your `PATH`:

| Tool | Used for |
|------|----------|
| ngspice | SPICE simulation |
| klayout | GDS viewing |
| magic | DRC, extraction |
| netgen | LVS |

PDK setup (layer files, device models, design rules) is your responsibility in a
native install. The DevContainer handles all of this automatically for SKY130.

## Project Structure

```
pade/                       # Core package (pip-installable)
├── core/                   #   Cell, Testbench, Terminal, Net, Parameter
├── layout/                 #   LayoutCell, Shape, Layer, Ref, Pin, Route
├── backends/
│   ├── gds/                #   GDS reader/writer
│   ├── ngspice/            #   Netlist writer, simulator, results reader
│   ├── spectre/            #   Spectre backend
│   └── magic/              #   Magic layout writer
├── stdlib.py               #   Ideal components: V, R, C, L, I, B
└── statement.py            #   Analysis, Save, Include, IC, Options

examples/                   # Reference design project (SKY130)
├── pdk/sky130/             #   PDK layer maps, rules, vias, primitives
├── src/                    #   Circuits, testbenches, simulation runners
├── utils/                  #   EDA tool wrappers (DRC, LVS, PEX, synthesis)
└── tutorials/              #   Jupyter notebooks
```

## Tutorials

| # | Notebook | Covers |
|---|----------|--------|
| 1 | [Core PADE](examples/tutorials/01_core_pade.ipynb) | Schematic, simulation, layout, routing, GDS, connectivity — core API only |
| 2 | [Sigma-Delta Modulator (SKY130)](examples/tutorials/02_sigma_delta_sky130.ipynb) | Full design flow: PDK setup, transistor-level layout, DRC/LVS/PEX, digital integration |

## License

[MIT](LICENSE)
