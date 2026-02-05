"""Netlist statements - backend-agnostic simulation control."""

from typing import Optional


class Statement:
    """
    Base class for netlist statements.

    Can be used directly for raw text, or inherited for structured statements.

    Examples:
        Statement('// custom comment')
        Statement('simulator lang=spectre')
    """

    def __init__(self, raw: Optional[str] = None):
        self.raw = raw

    def __repr__(self) -> str:
        if self.raw:
            return f"Statement({self.raw!r})"
        return f"{self.__class__.__name__}()"


class Analysis(Statement):
    """
    Analysis statement (ac, dc, tran, noise, stb, pss, etc.)

    Args:
        analysis_type: Type of analysis ('ac', 'dc', 'tran', etc.)
        name: Instance name (defaults to analysis_type)
        **params: Analysis parameters

    Examples:
        Analysis('ac', start=1, stop=10e9, dec=10)
        Analysis('tran', 'mytran', stop=1e-6)
        Analysis('dc')
        Analysis('noise', start=1, stop=10e9, oprobe='Vout')
    """

    def __init__(self, analysis_type: str, name: Optional[str] = None, **params):
        super().__init__()
        self.analysis_type = analysis_type
        self.name = name if name is not None else analysis_type
        self.params = params

    def __repr__(self) -> str:
        params_str = ', '.join(f'{k}={v!r}' for k, v in self.params.items())
        if params_str:
            return f"Analysis({self.analysis_type!r}, {self.name!r}, {params_str})"
        return f"Analysis({self.analysis_type!r}, {self.name!r})"


class Options(Statement):
    """
    Simulator options statement.

    Args:
        name: Instance name (defaults to 'opts')
        **params: Option parameters

    Examples:
        Options(reltol=1e-6, vabstol=1e-9)
        Options('myopts', temp=27)
    """

    def __init__(self, name: str = 'opts', **params):
        super().__init__()
        self.name = name
        self.params = params

    def __repr__(self) -> str:
        params_str = ', '.join(f'{k}={v!r}' for k, v in self.params.items())
        return f"Options({self.name!r}, {params_str})"


class Save(Statement):
    """
    Output selection statement.

    Args:
        signals: List of signals to save
        **settings: Additional save settings

    Examples:
        Save(['out', 'vdd', 'I0:drain'])
        Save(['out'], nestlvl=2)
    """

    def __init__(self, signals: Optional[list[str]] = None, **settings):
        super().__init__()
        self.signals = signals or []
        self.settings = settings

    def __repr__(self) -> str:
        return f"Save({self.signals!r})"


class Include(Statement):
    """
    Include file statement (for model files, corners, etc.)

    Args:
        path: Path to file to include
        selector: Optional selector string appended after the path


    Examples:
        Include('/path/to/models.scs')
        Include('/path/to/models.scs', selector='section=tt')
    """

    def __init__(self, path: str, selector: Optional[str] = None):
        super().__init__()
        self.path = path
        self.selector = selector

    def __repr__(self) -> str:
        if self.selector:
            return f"Include({self.path!r}, selector={self.selector!r})"
        return f"Include({self.path!r})"


class IC(Statement):
    """
    Initial conditions statement.

    Args:
        **conditions: Node=value pairs

    Examples:
        IC(out=0, vdd=1.8)
        IC(**{'net1': 0.5, 'net2': 1.0})
    """

    def __init__(self, **conditions):
        super().__init__()
        self.conditions = conditions

    def __repr__(self) -> str:
        cond_str = ', '.join(f'{k}={v!r}' for k, v in self.conditions.items())
        return f"IC({cond_str})"
