import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class Rounded(object):

    def setRounded(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        bit = QBitmap(self.size())
        bit.fill()
        painter = QPainter()
        painter.begin(bit)
        painter.setRenderHint(QPainter.Antialiasing, 0)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.black)
        painter.drawRoundedRect(bit.rect(), 10, 10)
        painter.end()
        self.setMask(bit)

class Widget(QWidget, Rounded):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(500, 500)
        self.setRounded()        
   

def main():
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()