from gui.main_window_ui import PadeMainUI
from functools import partial

class PadeCtrl:
    """Pade Main View Controller."""
    def __init__(self, view: PadeMainUI):
        """Controller initializer."""
        self._view = view
        # Connect signals and slots
        # self._connectSignals()

    # def _connectSignals(self):
    #     """Connect signals and slots."""
    #     self._view.debug.stateChanged.connect(self.checked_debug)
    #     self._view.run_sim.clicked.connect(partial(self.run_sim, 'Run sim'))

    # # Other functions
    # def checked_debug(self, checked):
    #     self._view.setDisplayText('checked' + str(checked))

    # def run_sim(self, txt):
    #     checked = self._view.debug.isChecked()
    #     self._view.setDisplayText(str(checked))

