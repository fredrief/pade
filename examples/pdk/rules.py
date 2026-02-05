"""DesignRules - Generic container for PDK design rules with attribute access."""


class DesignRules:
    """Stores design rules with attribute access. Raises AttributeError if undefined.
    
    Example:
        rules = DesignRules()
        rules.M1 = DesignRules.from_dict({'MIN_W': 140, 'MIN_S': 140})
        print(rules.M1.MIN_W)  # 140
    """
    
    def __init__(self):
        self._data: dict = {}
    
    def __getattr__(self, name: str):
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"DesignRules: '{name}' not defined")
    
    def __setattr__(self, name: str, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    def __contains__(self, name: str) -> bool:
        return name in self._data
    
    def __repr__(self):
        return f"DesignRules({list(self._data.keys())})"
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DesignRules':
        """Load from dict. Nested dicts become nested DesignRules."""
        rules = cls()
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(rules, key, cls.from_dict(value))
            else:
                setattr(rules, key, value)
        return rules
    
    @classmethod
    def from_json(cls, path) -> 'DesignRules':
        """Load from JSON file."""
        import json
        from pathlib import Path
        with open(Path(path)) as f:
            return cls.from_dict(json.load(f))
