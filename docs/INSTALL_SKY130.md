# SKY130 PDK Installation Guide

This guide covers installing the SKY130 open-source PDK and associated tools for use with PADE.

## Quick Install (Linux)

```bash
cd pade/
./scripts/install_sky130.sh
source ~/.bashrc
```

## Manual Installation

### 1. Install EDA Tools

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ngspice magic xschem python3-pip
```

#### Fedora/RHEL
```bash
sudo dnf install ngspice magic xschem python3-pip
```

#### macOS
```bash
brew install ngspice
# magic and xschem require manual build - see links below
```

### 2. Install ciel (PDK Package Manager)

```bash
pip install --user ciel
```

Ensure `~/.local/bin` is in your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 3. Install SKY130 PDK

List available versions:
```bash
ciel ls-remote --pdk-family=sky130
```

Install latest:
```bash
ciel enable --pdk-family=sky130 $(ciel ls-remote --pdk-family=sky130 | head -1)
```

### 4. Set Environment Variables

Add to `~/.bashrc` (or `~/.zshrc`):
```bash
export PDK_ROOT="$HOME/.ciel"
export PDK=sky130A
```

Then reload:
```bash
source ~/.bashrc
```

## Verify Installation

```bash
# Check tools
ngspice --version
magic --version
xschem --version

# Check PDK
ls $PDK_ROOT/sky130A/
ls $PDK_ROOT/sky130A/libs.tech/ngspice/
```

You should see:
- `sky130.lib.spice` - Main model library
- Device model files for nfet, pfet, resistors, capacitors

## Directory Structure

After installation:
```
~/.ciel/
└── sky130A/
    ├── libs.ref/          # IP libraries (standard cells, etc.)
    └── libs.tech/         # Tool-specific files
        ├── ngspice/       # SPICE models
        ├── magic/         # Magic tech files
        └── xschem/        # Xschem symbols
```

## Using with PADE

```python
from pade.examples.pdk.sky130 import nfet_01v8, pfet_01v8

# Create inverter
mn = nfet_01v8('MN', parent=tb, w='1u', l='150n')
mp = pfet_01v8('MP', parent=tb, w='2u', l='150n')
```

## Troubleshooting

### ciel not found
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### PDK_ROOT not set
```bash
export PDK_ROOT="$HOME/.ciel"
```

### Models not found by ngspice
Ensure the include path in your netlist points to:
```
$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice
```

## Resources

- [SKY130 PDK Documentation](https://skywater-pdk.readthedocs.io/)
- [open_pdks GitHub](https://github.com/RTimothyEdwards/open_pdks)
- [Magic VLSI](http://opencircuitdesign.com/magic/)
- [Xschem](https://xschem.sourceforge.io/stefan/index.html)
- [NGspice](https://ngspice.sourceforge.io/)
