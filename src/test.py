
import sys
import io
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PIL import Image, ImageQt
path = r"C:\Users\fqk12\Desktop\test.jpg"

im = Image.open(path)
sm = im.resize((600, 600), Image.ANTIALIAS)
stream = io.BytesIO()
sm.save(stream, format='PNG')

newim = Image.open(stream)
qimage = ImageQt.ImageQt(newim)
print(qimage.size())
print(type(qimage))


class Widget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = QLabel(self)
        pix = QPixmap.fromImage(qimage)
        self.label.setPixmap(pix)
        self.resize(700, 700)

def main():
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
