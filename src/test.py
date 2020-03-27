import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class Widget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        p1 = QPoint(10, 10)
        p2 = QPoint(20, 20)
        print(p2 - p1)
        print(p2 + p1)
        self.rec = QRect(10, 10, 200, 200)
        self.resize(500, 500)

    def paintEvent(self, event):
        painter= QPainter()
        painter.begin(self)
        painter.drawRect(self.rec)
        painter.end()


def main():
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    # main()

    r = QRect(10, 10, 500, 500)
    r.moveTopLeft(QPoint(200, 200))
    print(r)
    print(r.topLeft())
