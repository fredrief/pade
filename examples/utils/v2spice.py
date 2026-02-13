"""Gate-level Verilog to SPICE netlist converter.

Converts a structural (post-synthesis) Verilog netlist into a SPICE
subcircuit that can be simulated in NGspice alongside analog blocks.

The gate-level Verilog contains only module ports, wire declarations,
cell instantiations with named port connections, and assign statements.
No behavioral constructs.

Usage::

    from utils.v2spice import GateLevelConverter

    conv = GateLevelConverter(spice_lib='/path/to/sky130_fd_sc_hd.spice')
    conv.convert(
        verilog_path='cic_filter_synth.v',
        output_path='cic_filter.spice',
        module_name='cic_filter',         # optional if file has one module
        power_nets={'VPWR': 'VPWR', 'VGND': 'VGND',
                    'VPB': 'VPWR', 'VNB': 'VGND'},
    )

The output file can then be loaded into a PADE testbench::

    from pade.backends.ngspice.netlist_reader import load_subckt
    CICFilter = load_subckt('cic_filter.spice', 'cic_filter')
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SpiceSubckt:
    """Parsed .subckt header from a SPICE library."""
    name: str
    pins: list[str]  # ordered pin list


@dataclass
class VerilogInstance:
    """A cell instantiation from structural Verilog."""
    cell_type: str
    inst_name: str
    connections: dict[str, str]  # port_name -> net_name


@dataclass
class VerilogModule:
    """Parsed structural Verilog module."""
    name: str
    ports: list[str]
    wires: set[str] = field(default_factory=set)
    instances: list[VerilogInstance] = field(default_factory=list)
    assigns: list[tuple[str, str]] = field(default_factory=list)  # (lhs, rhs)


# ---------------------------------------------------------------------------
# SPICE library parser (subcircuit headers only)
# ---------------------------------------------------------------------------

def parse_spice_lib(path: str | Path) -> dict[str, SpiceSubckt]:
    """Parse .subckt headers from a SPICE library file.

    Only reads the header lines — skips internal content for speed.
    Handles SPICE line continuations (``+``).

    Returns:
        Dict mapping subcircuit name to SpiceSubckt.
    """
    path = Path(path)
    text = path.read_text()
    # Join continuation lines
    text = re.sub(r'\n\+\s*', ' ', text)

    subckts: dict[str, SpiceSubckt] = {}
    for m in re.finditer(
        r'^\s*\.subckt\s+(\S+)\s+(.*)', text, re.IGNORECASE | re.MULTILINE
    ):
        name = m.group(1)
        tokens = m.group(2).split()
        # Tokens are pin names until we hit a param=value pair
        pins = [t for t in tokens if '=' not in t]
        subckts[name] = SpiceSubckt(name=name, pins=pins)
    return subckts


# ---------------------------------------------------------------------------
# Verilog parser (structural only)
# ---------------------------------------------------------------------------

_MODULE_RE = re.compile(r'module\s+(\w+)\s*\(([^)]*)\)\s*;')
_INST_RE = re.compile(
    r'(\w+)\s+(\S+)\s*\((.*?)\)\s*;', re.DOTALL
)
_PORT_RE = re.compile(r'\.(\w+)\s*\(([^)]*)\)')
_ASSIGN_RE = re.compile(r'assign\s+(\S+)\s*=\s*(\S+)\s*;')


def _sanitize_net(name: str) -> str:
    """Convert a Verilog net name to a SPICE-safe identifier.

    Removes backslash escapes, replaces brackets and spaces with
    underscores.
    """
    name = name.strip()
    if name.startswith('\\'):
        name = name[1:]
    name = name.replace('[', '_').replace(']', '').replace(' ', '')
    return name


def parse_verilog(path: str | Path, module_name: str | None = None) -> VerilogModule:
    """Parse a structural (gate-level) Verilog file.

    Args:
        path: Path to the Verilog file.
        module_name: Module to extract. If *None*, uses the first module.

    Returns:
        Parsed VerilogModule.
    """
    text = Path(path).read_text()

    # Find module
    modules = _MODULE_RE.findall(text)
    if not modules:
        raise ValueError(f'No module found in {path}')
    if module_name:
        match = [(n, p) for n, p in modules if n == module_name]
        if not match:
            raise ValueError(f"Module '{module_name}' not found. Available: {[m[0] for m in modules]}")
        mod_name, port_str = match[0]
    else:
        mod_name, port_str = modules[0]

    # Parse ports from module declaration
    ports = [_sanitize_net(p.strip()) for p in port_str.split(',') if p.strip()]

    # Extract the module body
    pattern = re.compile(
        rf'module\s+{re.escape(mod_name)}\s*\([^)]*\)\s*;(.*?)endmodule',
        re.DOTALL,
    )
    body_match = pattern.search(text)
    if not body_match:
        raise ValueError(f'Could not extract body of module {mod_name}')
    body = body_match.group(1)

    # Collect wires (including vectors)
    wires: set[str] = set()
    for m in re.finditer(r'(?:input|output|wire)\s+(?:\[[\d:]+\]\s*)?(\S.*?)\s*;', body):
        for name in m.group(1).split(','):
            wires.add(_sanitize_net(name.strip()))

    # Collect assigns
    assigns = [
        (_sanitize_net(m.group(1)), _sanitize_net(m.group(2)))
        for m in _ASSIGN_RE.finditer(body)
    ]

    # Collect cell instantiations
    # Remove wire/input/output/assign lines to avoid false matches
    inst_body = re.sub(r'^\s*(?:input|output|wire|assign)\b.*?;\s*$', '', body, flags=re.MULTILINE)
    instances = []
    for m in _INST_RE.finditer(inst_body):
        cell_type = m.group(1)
        inst_name = m.group(2)
        port_str_inner = m.group(3)
        connections = {}
        for pm in _PORT_RE.finditer(port_str_inner):
            port_name = pm.group(1)
            net_name = _sanitize_net(pm.group(2))
            connections[port_name] = net_name
        if connections:  # skip non-instantiation matches
            instances.append(VerilogInstance(cell_type, inst_name, connections))

    return VerilogModule(
        name=mod_name, ports=ports, wires=wires,
        instances=instances, assigns=assigns,
    )


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

class GateLevelConverter:
    """Convert gate-level Verilog to a SPICE subcircuit.

    Args:
        spice_lib: Path to the PDK standard cell SPICE library
            (e.g. ``sky130_fd_sc_hd.spice``).  Used to look up pin
            order for each cell type.
    """

    def __init__(self, spice_lib: str | Path):
        self.spice_lib = Path(spice_lib)
        self._lib: dict[str, SpiceSubckt] | None = None

    @property
    def lib(self) -> dict[str, SpiceSubckt]:
        if self._lib is None:
            self._lib = parse_spice_lib(self.spice_lib)
        return self._lib

    def convert(
        self,
        verilog_path: str | Path,
        output_path: str | Path,
        module_name: str | None = None,
        power_nets: dict[str, str] | None = None,
    ) -> Path:
        """Convert a gate-level Verilog module to a SPICE subcircuit.

        Args:
            verilog_path: Path to the synthesised Verilog file.
            output_path: Path for the output SPICE file.
            module_name: Verilog module name (default: first module).
            power_nets: Mapping from SPICE power pin name to the net
                name used in the subcircuit.  Defaults to
                ``{'VPWR': 'VPWR', 'VGND': 'VGND', 'VPB': 'VPWR',
                'VNB': 'VGND'}``.

        Returns:
            Path to the written SPICE file.
        """
        if power_nets is None:
            power_nets = {
                'VPWR': 'VPWR', 'VGND': 'VGND',
                'VPB': 'VPWR', 'VNB': 'VGND',
            }

        module = parse_verilog(verilog_path, module_name)
        lines = self._emit_spice(module, power_nets)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text('\n'.join(lines) + '\n')
        return output_path

    def _emit_spice(
        self,
        module: VerilogModule,
        power_nets: dict[str, str],
    ) -> list[str]:
        """Generate SPICE netlist lines."""
        # Subcircuit ports: module ports + unique power net names
        power_port_names = sorted(set(power_nets.values()))
        subckt_ports = module.ports + power_port_names

        lines = [
            f'* Gate-level SPICE netlist for {module.name}',
            f'* Converted from Verilog by v2spice',
            f'* Instances: {len(module.instances)}',
            f'*',
            f'.subckt {module.name} {" ".join(subckt_ports)}',
        ]

        # Emit assign statements as zero-ohm resistors
        for i, (lhs, rhs) in enumerate(module.assigns):
            lines.append(f'Rassign{i} {lhs} {rhs} 0')

        # Emit cell instances
        missing_cells: set[str] = set()
        for inst in module.instances:
            subckt = self.lib.get(inst.cell_type)
            if subckt is None:
                if inst.cell_type not in missing_cells:
                    missing_cells.add(inst.cell_type)
                    lines.append(f'* WARNING: cell {inst.cell_type} not found in SPICE library')
                continue

            # Build pin list in SPICE order
            spice_pins = []
            for pin_name in subckt.pins:
                if pin_name in power_nets:
                    spice_pins.append(power_nets[pin_name])
                elif pin_name in inst.connections:
                    spice_pins.append(inst.connections[pin_name])
                else:
                    # Unconnected — tie to a dummy net
                    dummy = f'_NC_{inst.inst_name}_{pin_name}'
                    spice_pins.append(dummy)
                    lines.append(f'* WARNING: unconnected pin {pin_name} on {inst.inst_name}')

            inst_line = f'X{inst.inst_name} {" ".join(spice_pins)} {inst.cell_type}'
            lines.append(inst_line)

        lines.append(f'.ends {module.name}')
        return lines
