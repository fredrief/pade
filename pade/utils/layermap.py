"""Utilities for parsing PDK layer information."""

import xml.etree.ElementTree as ET
from pathlib import Path
import re

from pade.layout.shape import LayerMap


def parse_klayout_lyp(lyp_path: str | Path, purpose: str = 'drawing') -> dict:
    """
    Parse KLayout .lyp file to create LayerMap mapping dict.
    
    Args:
        lyp_path: Path to .lyp file
        purpose: Layer purpose to extract (default: 'drawing')
        
    Returns:
        Dict suitable for LayerMap: {NAME: {'magic': name, 'gds': (layer, datatype)}}
    """
    tree = ET.parse(lyp_path)
    root = tree.getroot()
    
    mapping = {}
    for props in root.findall('.//properties'):
        name_elem = props.find('name')
        if name_elem is None:
            continue
            
        name_text = name_elem.text or ''
        
        # Parse: "met1.drawing - 68/20"
        match = re.match(r'(\w+)\.(\w+)\s*-\s*(\d+)/(\d+)', name_text)
        if not match:
            continue
            
        layer_name = match.group(1)
        layer_purpose = match.group(2)
        gds_layer = int(match.group(3))
        gds_datatype = int(match.group(4))
        
        if layer_purpose != purpose:
            continue
        
        # Use uppercase as key, lowercase name works for Magic
        upper_name = layer_name.upper()
        mapping[upper_name] = {
            'magic': layer_name,
            'gds': (gds_layer, gds_datatype)
        }
    
    return mapping


def create_layermap_from_pdk(pdk_path: str | Path, pdk_name: str = 'sky130A') -> LayerMap:
    """
    Create LayerMap from PDK's KLayout .lyp file.
    
    Args:
        pdk_path: Path to PDK root (e.g., ~/.ciel/sky130A)
        pdk_name: PDK name (used for .lyp filename and LayerMap name)
        
    Returns:
        LayerMap with Magic and GDS layer mappings
    """
    pdk_path = Path(pdk_path)
    lyp_path = pdk_path / 'libs.tech/klayout/tech' / f'{pdk_name}.lyp'
    
    mapping = parse_klayout_lyp(lyp_path)
    return LayerMap(pdk_name, mapping)
