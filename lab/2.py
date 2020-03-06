import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from customwidgets import ImgLabel, PreviewLabel

# class PreviewLabel(QLabel):
    # def __init__(self, *args, **kwargs):
    #     pixmap = kwargs.pop('pix' , None)
    #     super().__init__(*args, **kwargs)
    #     self.__enter = False
    #     self.pix = pixmap
    #     if self.pix:
    #         self.setPixmap(self.pix)
    #         self.setScaledContents(True)

    # def paintEvent(self, event):
    #     painter = QPainter()
    #     painter.setRenderHint(QPainter.Antialiasing)
    #     painter.begin(self)
    #     self.drawPolicy(painter)
    #     painter.end()

    # def drawPolicy(self, painter):
    #     painter.drawPixmap(self.rect(), self.pix)
    #     if self.__enter:
    #         painter.fillRect(self.rect(), QColor(120, 120, 120, 30))

    # def enterEvent(self, event):
    #     super().enterEvent(event)
    #     self.__enter = True
    #     self.update()

    # def leaveEvent(self, event):
    #     super().leaveEvent(event)
    #     self.__enter = False
    #     self.update()
        

class PreviewWidget(QWidget):
    def __init__(self, index, pixmap):
        super().__init__()
        # self.setAttribute(Qt.WA_TranslucentBackground)
        self.__enter = False
        self.selected = False
        self.preview_label = PreviewLabel()
        self.preview_label.setScaledContents(True)
        self.preview_label.setPixmap(pixmap)
        self.preview_label.setEdited(False)
        self.preview_label.setEditPixmap(pixmap)
        # self.preview_label.setStyleSheet('border: 5px solid black')
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.preview_label)
        self.setLayout(self.layout)

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.drawPolicy(painter)
        painter.end()
    
    def drawPolicy(self, painter):
        if self.__enter or self.selected:
            painter.setPen(Qt.black)
            path1 = QPainterPath()
            path1.addRect(QRectF(self.rect()))
            path2 = QPainterPath()
            path2.addRect(QRectF(self.preview_label.geometry()))
            painter.fillPath(path1 - path2, QColor(120, 120, 120, 80))
            painter.drawPath(path2)
      
    def enterEvent(self, event):
        super().enterEvent(event)
        self.__enter = True
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.__enter = False
        self.update()
    

def main():
    app = QApplication(sys.argv)
    win = PreviewWidget(0, QPixmap(r'C:\githubs\ocr\lab\1.png'))
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()