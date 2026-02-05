"""Unified runner for physical verification tools (DRC, LVS, PEX)."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from utils.drc import DRC, DRCResult
from utils.lvs import LVS, LVSResult
from utils.pex import PEX, PEXResult

if TYPE_CHECKING:
    from pade.layout.cell import LayoutCell
    from pade.core.cell import Cell


@dataclass
class DesignResult:
    """Combined result of DRC/LVS/PEX runs."""
    drc: Optional[DRCResult] = None
    lvs: Optional[LVSResult] = None
    pex: Optional[PEXResult] = None

    @property
    def passed(self) -> bool:
        """True if all executed checks passed."""
        checks = []
        if self.drc:
            checks.append(self.drc.passed)
        if self.lvs:
            checks.append(self.lvs.matched)
        if self.pex:
            checks.append(self.pex.success)
        return all(checks) if checks else False

    def __str__(self) -> str:
        parts = []
        if self.drc:
            parts.append(str(self.drc))
        if self.lvs:
            parts.append(str(self.lvs))
        if self.pex:
            parts.append(str(self.pex))
        return '\n'.join(parts)


class DesignRunner:
    """Unified runner for DRC, LVS, and PEX verification.
    
    Provides a single interface to run physical verification tools
    with configurable options.
    
    Example:
        runner = DesignRunner(layout, schematic)
        
        # Run individual tools
        drc_result = runner.drc()
        lvs_result = runner.lvs()
        pex_result = runner.pex(cthresh=0.1)
        
        # Or run all at once
        result = runner.run_all()
        print(result)
        
        # Selective run
        result = runner.run_all(drc=True, lvs=True, pex=False)
    """
    
    def __init__(self, layout: 'LayoutCell', schematic: 'Cell' = None, **kwargs):
        """Initialize runner with layout and optional schematic.
        
        Args:
            layout: LayoutCell for verification
            schematic: Schematic Cell for LVS (required for LVS)
            **kwargs: Default settings for tools
                - cthresh: PEX capacitance threshold (default: 0)
                - rthresh: PEX resistance threshold (default: 0)
        """
        self.layout = layout
        self.schematic = schematic
        self.settings = kwargs
        
        self._drc = DRC()
        self._lvs = LVS()
        self._pex = PEX()
    
    def drc(self) -> DRCResult:
        """Run DRC check."""
        return self._drc.run(self.layout)
    
    def lvs(self) -> LVSResult:
        """Run LVS comparison."""
        if self.schematic is None:
            raise ValueError("Schematic required for LVS")
        return self._lvs.run(self.layout, self.schematic)
    
    def pex(self, cthresh: float = None, rthresh: float = None) -> PEXResult:
        """Run parasitic extraction.
        
        Args:
            cthresh: Capacitance threshold in fF (overrides default)
            rthresh: Resistance threshold in ohms (overrides default)
        """
        cthresh = cthresh if cthresh is not None else self.settings.get('cthresh', 0)
        rthresh = rthresh if rthresh is not None else self.settings.get('rthresh', 0)
        return self._pex.run(self.layout, cthresh=cthresh, rthresh=rthresh)
    
    def run_all(self, drc: bool = True, lvs: bool = True, pex: bool = True,
                **kwargs) -> DesignResult:
        """Run selected verification tools.
        
        Args:
            drc: Run DRC check
            lvs: Run LVS comparison (requires schematic)
            pex: Run parasitic extraction
            **kwargs: Override settings for this run
        
        Returns:
            DesignResult with results from each tool
        """
        result = DesignResult()
        
        if drc:
            result.drc = self.drc()
        
        if lvs:
            if self.schematic is None:
                raise ValueError("Schematic required for LVS")
            result.lvs = self.lvs()
        
        if pex:
            merged = {**self.settings, **kwargs}
            result.pex = self.pex(
                cthresh=merged.get('cthresh'),
                rthresh=merged.get('rthresh')
            )
        
        return result
