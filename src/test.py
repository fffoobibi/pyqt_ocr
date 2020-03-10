import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from customwidgets import ImgLabel


class ScaledLabel(ImgLabel):
    pass
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.d_scaled = []
    #     self.d_w = self.width()
    #     self.d_h = self.height()

    # def paintEvent(self, QPaintEvent):
    #     super().paintEvent(QPaintEvent)
    #     points = []
    #     for xycoords in self.points.data:
    #         x1, y1, x2, y2 = xycoords
    #         w, h = abs(x2 - x1), abs(y2 - y1)
    #         if (x2 - x1) > 0 and (y2 - y1) > 0:
    #             points.append([x1, y1, x2, y2])  # 右下方滑动
    #         elif (x2 - x1) > 0 and (y2 - y1) < 0:
    #             points.append([x1, y1 - h, x2, y2 + h])  # 右上方滑动
    #         elif (x2 - x1) < 0 and (y2 - y1) > 0:
    #             points.append([x2, y2 - h, x1, y1 + h])  # 左下方滑动
    #         else:
    #             points.append([x2, y2, x1, y1])  # 左上方滑动
    #     w, h = self.width(), self.height()
    #     for xycoords in points:
    #         x1,y1,x2,y2 = xycoords
    #         self.d_scaled.append([(x1/w, y1/h),(x2/w, y2/h)])


class Widget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pixmap = QPixmap(r"C:\Users\fqk12\Desktop\111.png")
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.label = ScaledLabel(self)
        self.label.setScaledContents(True)
        self.label.setPixmap(pixmap)
        self.label.setEditPixmap(pixmap)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.default_w, self.default_h = pixmap.width(), pixmap.height()
        print('d', self.default_w)

    def wheelEvent(self, event):
        points = []
        for xycoords in self.label.points.data:
            x1, y1, x2, y2 = xycoords
            w, h = abs(x2 - x1), abs(y2 - y1)
            if (x2 - x1) > 0 and (y2 - y1) > 0:
                points.append([x1, y1, x2, y2])  # 右下方滑动
            elif (x2 - x1) > 0 and (y2 - y1) < 0:
                points.append([x1, y1 - h, x2, y2 + h])  # 右上方滑动
            elif (x2 - x1) < 0 and (y2 - y1) > 0:
                points.append([x2, y2 - h, x1, y1 + h])  # 左下方滑动
            else:
                points.append([x2, y2, x1, y1])  # 左上方滑动

        w, h = self.width(), self.height()
        self.label.points.clear()
        angle = event.angleDelta()
        if angle.y() > 0: # 放大
            process = []
            scaled_w = round(self.width() * 1.1, 0)
            scaled_h = round(self.height() * 1.1, 0)
            for xycoords in points:
                x1, y1, x2, y2 = xycoords
                x_1, y_1, x_2, y_2 = x1 / w * scaled_w, y1 / h * scaled_h, x2 / w * scaled_w, y2 / h * scaled_h
                self.label.points.append([x_1, y_1, x_2, y_2])
        else:
            scaled_w = round(self.width() * 0.9, 0)
            scaled_h = round(self.height() * 0.9, 0)
            if scaled_w <= self.default_w:
                self.label.points.appends(points)
            else:
                process = []
                for xycoords in points:
                    x1, y1, x2, y2 = xycoords
                    x_1, y_1, x_2, y_2 = x1 / w * scaled_w, y1 / h * scaled_h, x2 / w * scaled_w, y2 / h * scaled_h
                    self.label.points.append([x_1, y_1, x_2, y_2])

        if scaled_w <= self.default_w:
            self.resize(self.default_w, self.default_h)
        else:
            self.resize(scaled_w, scaled_h)


def main():
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())

from pdf import Engine
app = QApplication([])
eng = Engine(r"C:\Users\fqk12\Desktop\111.png")
print(eng.pageCount())
print(eng.pagesView()) 
print(eng.getPixmap(0).size())
app.exec_()