from PyQt5.QtWidgets import QCheckBox, QGridLayout, QLabel, QMainWindow
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout, QGraphicsLayout
from PyQt5.QtCore import Qt

class PadeMainUI(QMainWindow):
    """Main View (GUI)."""
    def __init__(self):
        """View initializer."""
        super().__init__()
        # Set some main window's properties
        self.setWindowTitle('PADE')
        self.setFixedSize(235, 235)
        # Set the central widget and the general layout
        self.generalLayout = QGridLayout()
        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.generalLayout)
        # Simulation options
        self._simulation_options()

    def _simulation_options(self):
        # Simulations options widget
        self.simOptLayout = QVBoxLayout()
        # Create the display widget
        self.simOptLabel = QLabel()
        self.simOptLabel.setText('Simulation Options')
        self.simOptLayout.addWidget(self.simOptLabel)
        # Add the display to the general layout
        self.generalLayout.addLayout(self.simOptLayout, 0,0)
