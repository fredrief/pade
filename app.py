import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from gui.main_win import Ui_MainWindow
from gui.main_window_ui import PadeMainUI
from gui.main_window_ctrl import PadeCtrl

if __name__ == '__main__':
    # Create an instance of QApplication
    app = QApplication(sys.argv)
    mainWin = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(mainWin)
    mainWin.show()
    sys.exit(app.exec_())
