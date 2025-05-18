from PyQt6 import QtWidgets
from ui.main_window import MainWindow

def main():
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
