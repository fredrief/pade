"""
Parameter - Named parameter with value and optional unit.
"""

from typing import Any, Optional


class Parameter:
    """
    A parameter represents a named value with optional unit and default.
    
    Attributes:
        name: Parameter name (e.g., 'w', 'l', 'temp')
        value: Parameter value
        default: Default value (used in subcircuit definitions)
        unit: Optional unit string
    """
    
    def __init__(self, 
                 name: str, 
                 value: Any, 
                 default: Any = None,
                 unit: Optional[str] = None) -> None:
        """
        Create a parameter.
        
        Args:
            name: Parameter name
            value: Parameter value
            default: Default value for subcircuit parameters
            unit: Optional unit (e.g., 'm', 'F', 'Hz')
        """
        self.name = name
        self.value = value
        self.default = default
        self.unit = unit
    
    def __str__(self) -> str:
        return f"Parameter({self.name}={self.value})"
    
    def __repr__(self) -> str:
        return self.__str__()
