"""SKY130 design rules. All dimensions in nm."""

from pdk.rules import DesignRules

sky130_rules = DesignRules()

sky130_rules.tech_name = 'sky130A'
sky130_rules.port_size = 100

# Metal layers
sky130_rules.LI = DesignRules.from_dict({'MIN_W': 170, 'MIN_S': 170, 'MIN_AREA': 25600})
sky130_rules.M1 = DesignRules.from_dict({'MIN_W': 140, 'MIN_S': 140, 'MIN_AREA': 8400})
sky130_rules.M2 = DesignRules.from_dict({'MIN_W': 140, 'MIN_S': 140, 'MIN_AREA': 8400})
sky130_rules.M3 = DesignRules.from_dict({'MIN_W': 300, 'MIN_S': 300, 'MIN_AREA': 24000})
sky130_rules.M4 = DesignRules.from_dict({'MIN_W': 300, 'MIN_S': 300, 'MIN_AREA': 24000})
sky130_rules.M5 = DesignRules.from_dict({'MIN_W': 1600, 'MIN_S': 1600, 'MIN_AREA': 640000})

# Via/contact layers
sky130_rules.LICON = DesignRules.from_dict({'W': 170, 'S': 170, 'ENC_DIFF': 60, 'ENC_POLY': 80, 'ENC_LI': 80})
sky130_rules.MCON = DesignRules.from_dict({'W': 170, 'S': 190, 'ENC_BOT': 60, 'ENC_TOP': 60})
sky130_rules.VIA1 = DesignRules.from_dict({'W': 150, 'S': 170, 'ENC_BOT': 55, 'ENC_TOP': 55})
sky130_rules.VIA2 = DesignRules.from_dict({'W': 200, 'S': 200, 'ENC_BOT': 40, 'ENC_TOP': 65})
sky130_rules.VIA3 = DesignRules.from_dict({'W': 200, 'S': 200, 'ENC_BOT': 60, 'ENC_TOP': 60})
sky130_rules.VIA4 = DesignRules.from_dict({'W': 800, 'S': 800, 'ENC_BOT': 190, 'ENC_TOP': 310})

# MiM capacitor rules
sky130_rules.CAPM2 = DesignRules.from_dict({
    'MIN_W': 1000,
    'MIN_S': 840,
    'ENC_BY_M4': 140,
})

# MOSFET rules (from Magic sky130A.tcl ruleset, converted um -> nm)
sky130_rules.MOS = DesignRules.from_dict({
    # Contact/via sizes
    'CONTACT_SIZE': 170,
    'VIA_SIZE': 170,
    # Enclosures (layer surrounds contact)
    'POLY_ENC_CONT': 80,
    'DIFF_ENC_CONT': 60,
    'LI_ENC_CONT': 80,
    # Gate geometry
    'GATE_EXT': 130,           # Poly extension beyond gate (over diffusion)
    'DIFF_EXT': 290,           # Diffusion extension beyond gate
    'GATE_TO_DIFFCONT': 145,   # Gate edge to diffusion contact center
    'GATE_TO_POLYCONT': 275,   # Gate edge to poly contact center
    # Spacings
    'DIFF_SPACING': 280,
    'POLY_SPACING': 210,
    'DIFF_POLY_SPACE': 75,
    'DIFF_GATE_SPACE': 200,
    # Substrate/well
    'SUB_ENC_DIFF': 180,
    # Min dimensions
    'MIN_L': 150,
    'MIN_W': 420,
    # Short gate threshold (below this, poly contacts must alternate)
    'MIN_ALLC': 260,
    # Minimum effective finger length
    'MIN_EFFL': 185,
})

# NFET-specific (1.8V)
sky130_rules.NFET = DesignRules.from_dict({
    'MIN_L': 150,
    'MIN_W': 420,
})

# PFET-specific (1.8V)
sky130_rules.PFET = DesignRules.from_dict({
    'MIN_L': 150,
    'MIN_W': 420,
    'GATE_TO_POLYCONT': 320,  # PFET needs slightly more space
})
