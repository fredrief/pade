"""
Analysis statement.
"""

from typing import Optional

from pade.statement.base import Statement


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
