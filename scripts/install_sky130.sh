#!/bin/bash
# Install SKY130 PDK and open source EDA tools for PADE
#
# Usage: ./scripts/install_sky130.sh
#
# This script installs:
# - ngspice (SPICE simulator)
# - magic (layout editor, DRC, LVS)
# - xschem (schematic editor)
# - ciel (PDK package manager)
# - SKY130 PDK

set -e

echo "=========================================="
echo "PADE SKY130 Installation Script"
echo "=========================================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v apt &> /dev/null; then
        PKG_MANAGER="apt"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
    else
        echo "Error: Unsupported Linux distribution"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PKG_MANAGER="brew"
else
    echo "Error: Unsupported OS: $OSTYPE"
    exit 1
fi

echo "Detected package manager: $PKG_MANAGER"

# Install system packages
echo ""
echo "Step 1: Installing system packages..."
echo "--------------------------------------"

if [[ "$PKG_MANAGER" == "apt" ]]; then
    sudo apt update
    sudo apt install -y ngspice magic xschem python3-pip
elif [[ "$PKG_MANAGER" == "dnf" ]] || [[ "$PKG_MANAGER" == "yum" ]]; then
    sudo $PKG_MANAGER install -y ngspice magic xschem python3-pip
elif [[ "$PKG_MANAGER" == "brew" ]]; then
    brew install ngspice
    # magic and xschem need to be built from source on Mac or use cask
    echo "Note: On macOS, magic and xschem may need manual installation"
    echo "See: http://opencircuitdesign.com/magic/"
    echo "See: https://xschem.sourceforge.io/stefan/index.html"
fi

# Verify installations
echo ""
echo "Verifying tool installations..."
command -v ngspice &> /dev/null && echo "  ✓ ngspice installed" || echo "  ✗ ngspice NOT found"
command -v magic &> /dev/null && echo "  ✓ magic installed" || echo "  ✗ magic NOT found"
command -v xschem &> /dev/null && echo "  ✓ xschem installed" || echo "  ✗ xschem NOT found"

# Install ciel (PDK package manager)
echo ""
echo "Step 2: Installing ciel (PDK manager)..."
echo "-----------------------------------------"
pip install --user ciel

# Add ~/.local/bin to PATH if not already
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    export PATH="$HOME/.local/bin:$PATH"
    echo "Added ~/.local/bin to PATH"
fi

# Verify ciel
command -v ciel &> /dev/null && echo "  ✓ ciel installed" || {
    echo "  ✗ ciel NOT found in PATH"
    echo "  Try: export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
}

# Install SKY130 PDK
echo ""
echo "Step 3: Installing SKY130 PDK..."
echo "---------------------------------"
echo "This may take several minutes (downloading ~500MB)..."

# Get latest SKY130 version
LATEST=$(ciel ls-remote --pdk-family=sky130 | head -1)
echo "Installing SKY130 version: $LATEST"

ciel enable --pdk-family=sky130 "$LATEST"

# Set up environment variables
echo ""
echo "Step 4: Setting up environment..."
echo "----------------------------------"

PDK_ROOT="$HOME/.ciel"

# Check if already in bashrc
if ! grep -q "PDK_ROOT" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# SKY130 PDK environment (added by PADE install script)" >> ~/.bashrc
    echo "export PDK_ROOT=\"$PDK_ROOT\"" >> ~/.bashrc
    echo "export PDK=sky130A" >> ~/.bashrc
    echo "Added PDK_ROOT and PDK to ~/.bashrc"
else
    echo "PDK_ROOT already configured in ~/.bashrc"
fi

export PDK_ROOT="$PDK_ROOT"
export PDK=sky130A

# Verify PDK installation
echo ""
echo "Step 5: Verifying installation..."
echo "----------------------------------"

if [[ -d "$PDK_ROOT/sky130A" ]]; then
    echo "  ✓ SKY130A PDK installed at $PDK_ROOT/sky130A"
else
    echo "  ✗ SKY130A PDK NOT found"
    exit 1
fi

# Check for model files
if [[ -f "$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice" ]]; then
    echo "  ✓ NGspice models found"
else
    echo "  ✗ NGspice models NOT found"
fi

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "To use the PDK, either:"
echo "  1. Open a new terminal, or"
echo "  2. Run: source ~/.bashrc"
echo ""
echo "Environment variables set:"
echo "  PDK_ROOT=$PDK_ROOT"
echo "  PDK=sky130A"
echo ""
echo "Test with:"
echo "  ngspice --version"
echo "  magic --version"
echo "  echo \$PDK_ROOT"
