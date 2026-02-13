# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] — 2026-02-13

First public release.

### Added
- Hierarchical schematic model: `Cell`, `Terminal`, `Net`, `Parameter`, `Testbench`
- Layout engine: `LayoutCell`, `Shape`, `Layer`, `Ref`, `Pin`, `Transform`
- L-shaped and jogged metal router with net-aware connectivity
- Schematic–layout integration: `check_connectivity()`, `check_shorts()`
- GDS export/import via gdstk
- Magic `.mag` layout export
- NGspice simulation backend (netlist writer, simulator, results reader)
- Spectre simulation backend (netlist writer)
- Ideal component library (`stdlib`): `V`, `R`, `C`, `L`, `I`, `B`
- Statement classes: `Analysis`, `Save`, `Include`, `IC`, `Options`
- `_post_register()` hook in `Cell` and `LayoutCell` for deferred initialization
- SKY130 example project with PDK configuration, primitives, digital cells
- `pex_enabled` decorator for transparent PEX netlist switching
- Two tutorials: Core PADE, Sigma-Delta Modulator design flow
- DevContainer with all open-source EDA tools and SKY130 PDK
