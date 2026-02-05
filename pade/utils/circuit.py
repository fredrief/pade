"""
Circuit manipulation utilities.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pade.core.cell import Cell
    from pade.core.terminal import Terminal


def insert_between(cell: 'Cell',
                   term_a: 'Terminal',
                   term_b: 'Terminal',
                   cell_term_1: 'Terminal',
                   cell_term_2: 'Terminal') -> None:
    """
    Insert a cell between two terminals that are connected to the same net.
    
    Example:
        # Insert capacitor between two terminals
        insert_between(cap, amp.inp, bias.out, cap.terminals['p'], cap.terminals['n'])
    
    Args:
        cell: Cell to insert
        term_a: First terminal
        term_b: Second terminal  
        cell_term_1: Terminal of cell to connect to term_a's net
        cell_term_2: Terminal of cell to connect to term_b's net
    """
    from pade.core.net import Net
    
    # Verify that term_a and term_b are both connected to the same net
    if term_a.net is None or term_b.net is None:
        raise ValueError(
            f'Cannot insert between terminals {term_a} and {term_b} - '
            'one or both are not connected to a net'
        )
    
    if term_a.net is not term_b.net:
        raise ValueError(
            f'Cannot insert between terminals {term_a} and {term_b} - '
            'they are not connected to the same net'
        )
    
    net2 = term_b.net
    
    # Disconnect all terminals except term_b from net2
    pending_terminals = []
    for t in net2.connections[:]:  # Copy list to avoid modification during iteration
        if t is not term_b:
            pending_terminals.append(t)
    
    # Connect cell_term_2 to net2
    cell_term_2.connect(net2)
    
    # Create new net and connect cell_term_1 and all pending terminals
    net1 = Net(term_a.get_name_from_top().replace('.', '_'), cell.parent_cell)
    cell_term_1.connect(net1)
    
    for t in pending_terminals:
        t.disconnect()
        t.connect(net1)
