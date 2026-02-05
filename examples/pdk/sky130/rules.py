"""SKY130 design rules. All dimensions in nm."""

from pdk.rules import DesignRules

# =============================================================================
# Design Rules
# =============================================================================

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

# Via layers
sky130_rules.MCON = DesignRules.from_dict({'W': 170, 'S': 190, 'ENC_BOT': 60, 'ENC_TOP': 60})
sky130_rules.VIA1 = DesignRules.from_dict({'W': 150, 'S': 170, 'ENC_BOT': 55, 'ENC_TOP': 55})
sky130_rules.VIA2 = DesignRules.from_dict({'W': 200, 'S': 200, 'ENC_BOT': 40, 'ENC_TOP': 65})
sky130_rules.VIA3 = DesignRules.from_dict({'W': 200, 'S': 200, 'ENC_BOT': 60, 'ENC_TOP': 60})
sky130_rules.VIA4 = DesignRules.from_dict({'W': 800, 'S': 800, 'ENC_BOT': 190, 'ENC_TOP': 310})

# MiM capacitor rules
sky130_rules.CAPM2 = DesignRules.from_dict({
    'MIN_W': 1000,      # cap2m.1: min width
    'MIN_S': 840,       # cap2m.2a: min spacing
    'ENC_BY_M4': 140,   # cap2m.3: M4 must surround CAPM2
})

# Transistor rules
sky130_rules.NFET = DesignRules.from_dict({
    'MIN_L': 150, 'MIN_W': 420, 'POLY_EXT': 130, 'POLY_S': 210, 'CT_TO_GATE': 55
})
sky130_rules.PFET = DesignRules.from_dict({
    'MIN_L': 150, 'MIN_W': 420, 'POLY_EXT': 130, 'POLY_S': 210, 'CT_TO_GATE': 55
})
