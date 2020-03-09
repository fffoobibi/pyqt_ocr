import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class Widget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame = QFrame(self)
        self.radio = QRadioButton(self.frame)
        

def main():
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()