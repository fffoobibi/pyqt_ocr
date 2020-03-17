import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
# help(QPainter.drawPixmap)

class Widget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(600, 600)
        self.pix = QPixmap(r'C:\githubs\ocr\111.png')
    
    def paintEvent(self, evnet):
        painter = QPainter()
        painter.begin(self)

        painter.save()
        painter.translate(300, 300)
        painter.rotate(45)
        painter.drawPixmap(-150, -150, 300, 300, self.pix)
        painter.restore()

        painter.drawPixmap(-150, -150, 300, 300, self.pix)

        painter.end()

def main():
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()