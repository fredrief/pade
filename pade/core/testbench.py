"""
Testbench - Top-level cell for simulation.
"""

from typing import Optional

from pade.core.cell import Cell


class Testbench(Cell):
    """
    Top-level cell designed for simulation.

    Testbench is just a Cell with:
    - instance_name == cell_name (marks it as top-level)
    - Ground net '0' added by default

    No special helper methods - users build testbenches like any other cell
    by instantiating sources, DUT, and loads as regular cells.
    """

    def __init__(self, name: Optional[str] = None, **kwargs) -> None:
        """
        Create a testbench.

        Args:
            name: Testbench name (defaults to class name)
            **kwargs: Config options passed to all subcells
        """
        name = name or type(self).__name__
        super().__init__(name, cell_name=name, **kwargs)
        self.add_net('0')  # Add ground net by convention
