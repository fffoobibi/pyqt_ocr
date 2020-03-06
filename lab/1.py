from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from widget import Ui_Form
import sys

class Widget(QWidget, Ui_Form):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.label.setPixmap(QPixmap(r'C:\githubs\ocr\lab\1.png'))
        self.label.setScaledContents(True)
        print(self.label.pixmap())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.begin(self)
        self.draw(painter)
        painter.end()

    def draw(self, paint):
        print(self.rect())
        test= QColor(120, 120, 120, 100)
        red = QColor(255,0,0,0)
        t2 = QColor(55,55,55,255)
        paint.fillRect(self.rect(), test)

app = QApplication([])
win = Widget()
win.show()
app.exec_()