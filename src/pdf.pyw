from sys import argv, exit
from PIL import Image, ImageQt
from fitz import open as pdf_open
from os.path import isfile, exists

from PyQt5.QtWidgets import (QApplication, QWidget, QListWidgetItem, QScrollBar,
                             QVBoxLayout, QMessageBox, QLabel, QListView)
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QSize, Qt
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen
from pdfui import Ui_Form
from customwidgets import ImgLabel, Validpoints


class PreviewLabel(ImgLabel):

    clicked = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        index = kwargs.pop('index', 0)
        super().__init__(*args, **kwargs)
        self.index = index
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        super().mouseReleaseEvent(event)

    def paintEvent(self, QPaintEvent):
        self.setCursor(Qt.PointingHandCursor)
        painter = QPainter()
        painter.begin(self)
        self.drawPolicy(painter)
        painter.end()


class PdfHandle(QObject):

    display_signal = pyqtSignal()
    reload_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    ocr_signal = pyqtSignal(list, list)

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.scaledSize = None
        self.pixmaps = []
        self.pixmaps_points = []
        self.preview_pixmaps_points = []
        self.edited_pdfs = []

    def clear(self):
        self.scaledSize = None
        self.pixmaps.clear()
        self.pixmaps_points.clear()
        self.preview_pixmaps_points.clear()
        self.edited_pdfs.clear()
        self.clear_signal.emit()

    def renderPixmap(self, index):
        pass

    def rendering(self):
        desktop = QApplication.desktop()
        self.pdf = pdf_open(self.root.lineEdit.text().strip('"').strip(' '))
        pix = self.pdf[0].getPixmap()
        fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
        pixmap = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)

        p_width, p_height = pixmap.width(), pixmap.height()
        d_width, d_height = desktop.width(), desktop.height()
        if (p_width, p_height) > (d_width, d_height):
            scaled_x = max(p_width / d_width, p_height / d_height) + 0.35
            self.scaledSize = (p_width / scaled_x, p_height / scaled_x)
        else:
            self.scaledSize = (p_width, p_height)
        for page in self.pdf:
            pdf_pixmap = page.getPixmap()
            temp_pixmap = QPixmap.fromImage(
                QImage(pdf_pixmap.samples, pdf_pixmap.width, pdf_pixmap.height,
                       pdf_pixmap.stride, fmt))
            pixmap = temp_pixmap.scaled(*self.scaledSize)

            self.pixmaps.append(pixmap)

        self.pixmaps_points = [[] for points in range(len(self.pixmaps))]
        self.preview_pixmaps_points = [
            0 for points in range(len(self.pixmaps))
        ]

        self.display_signal.emit()

    def open(self):
        pdf_file = self.root.lineEdit.text().strip('"').strip(' ')
        self.root._flag += 1
        self.edited_pdfs.append(pdf_file)

        try:
            if self.root._flag == 1:
                flag = False
            else:
                flag = pdf_file == self.edited_pdfs[-1]
        except IndexError:
            flag = False
        finally:
            if flag:
                self.reload_signal.emit()
                while True:
                    if self.root.reloaded == QMessageBox.Yes:
                        self.clear()
                        self.rendering()
                        self.thread().quit()
                        self.root.reloaded = -1
                        break
                    elif self.root.reloaded == QMessageBox.No:
                        self.thread().quit()
                        self.root.reloaded = -1
                        break
            else:
                self.clear()
                self.rendering()
                self.thread().quit()

    def init(self):
        pass


class PdfWidget(Ui_Form, QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.init()
        self.set_datas()

    def set_datas(self):
        self.reloaded = -1
        self._flag = 0
        self.pdf_handle = PdfHandle(self)
        self.pdf_thread = QThread()
        self.pdf_handle.moveToThread(self.pdf_thread)
        self.pdf_thread.started.connect(self.pdf_handle.open)
        self.pdf_handle.display_signal.connect(self.updateListWidget)
        self.pdf_handle.reload_signal.connect(self.reload)
        self.pdf_handle.clear_signal.connect(lambda: self.listWidget.clear())

    def init(self):
        self.listWidget.itemClicked.connect(self.test)
        self.label_2.points.points_signal.connect(self.updateListWidgetItem)
        self.setStyleSheet(open('./sources/flatwhite.css').read())
        self.setWindowTitle('PDF')


    def reload(self):
        replay = QMessageBox.question(self, 'PDF', '确认重新加载pdf么?',
                                      QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
        self.reloaded = replay

    def test(self, item):
        # help(self.listWidget.itemWidget)
        # help(self.listWidget.currentItem)

        # help(self.listWidget.setCurrentIndex)
        # help(self.listWidget.setCurrentItem)
        # help(self.listWidget.setCurrentRow)

        # help(self.listWidget.currentRow)
        # help(self.listWidget.currentIndex)
        # print(self.listWidget.currentIndex)
        # print(self.listWidget.item(1))
        pass

    def updateListWidgetItem(self, points):
        self.label_2.points.clear()
        self.label_2.points.appends(points)

        index = int(self.label_3.text()) - 1
        pix = self.pdf_handle.pixmaps[index]
        p_width, p_height = pix.width(), pix.height()
        width, height = pix.width() / 3, pix.height() / 3

        process = []
        for point in points:
            tmp = []
            x1, y1, x2, y2 = point
            x3 = x1 / p_width * width
            y3 = y1 / p_height * height
            x4 = x2 / p_width * width
            y4 = y2 / p_height * height
            tmp.extend([x3, y3, x4, y4])
            process.append(tmp)

        # label.setEditPixmap(pix)
        # label.points.appends(process)
        # item = self.listWidget.item(index)
        # self.listWidget.setItemWidget(item, widget)

        self.pdf_handle.pixmaps_points[index] = points
        self.pdf_handle.preview_pixmaps_points[index] = process

        item = self.listWidget.item(index)
        preview_label = self.listWidget.itemWidget(item).preview_label
        preview_label.points.clear()
        preview_label.points.appends(process)
        preview_label.update()

    def get_item_widget(self, pixmap, index):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        widget = QWidget()
        preview_label = PreviewLabel(index=index)
        preview_label.setEdited(False)
        widget.preview_label = preview_label
        width, height = pixmap.width() / 3, pixmap.height() / 3
        pix = pixmap.scaled(width, height)
        preview_label.setPixmap(pix)
        preview_label.setEditPixmap(pix)
        layout.addWidget(preview_label)
        indexlabel = QLabel(str(index + 1))
        indexlabel.setAlignment(Qt.AlignCenter)

        preview_label.clicked.connect(self.display)
        layout.addWidget(indexlabel)
        widget.setLayout(layout)
        return widget, preview_label, width, height

    def updateListWidget(self):
        self.listWidget.setFixedWidth(self.pdf_handle.pixmaps[0].width() / 3 +
                                      20)

        self.label_3.setText('1')
        self.label_2.setPixmap(self.pdf_handle.pixmaps[0])
        self.label_2.draw_pixmap = self.pdf_handle.pixmaps[0]
        self.label_2.setEdited(True)

        for index, pixmap in enumerate(self.pdf_handle.pixmaps):
            item = QListWidgetItem()
            widget, _, w, h = self.get_item_widget(pixmap, index)
            item.setSizeHint(QSize(w, h))
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, widget)
        print('count:', self.listWidget.count())

    def display(self, index):
        item = self.listWidget.currentItem()
        widget = self.listWidget.itemWidget(item)
        print('preview:', widget.preview_label.draw_pixmap.size())
        print('label:', self.pdf_handle.pixmaps[index].size())

        self.label_2.points.clear()
        self.label_3.setText(str(index + 1))
        self.label_2.setPixmap(self.pdf_handle.pixmaps[index])
        self.label_2.setEditPixmap(self.pdf_handle.pixmaps[index])
        # self.label_2.draw_pixmap = self.pdf_handle.pixmaps[index]
        self.label_2.points.appends(self.pdf_handle.pixmaps_points[index])
        self.label_2.metedata = {'index': index}
        self.label_2.update()

    def openSlot(self):
        pass

    def confirmSlot(self):
        pdf_file = self.lineEdit.text().strip('"').strip(' ')
        if exists(pdf_file):
            if pdf_file[-3:].lower() == 'pdf':
                self.pdf_thread.start()
        else:
            QMessageBox.warning(self, '警告', '打开正确的pdf文件')


def main():
    app = QApplication(argv)
    pdfwidget = PdfWidget()
    pdfwidget.show()
    exit(app.exec_())


if __name__ == "__main__":
    main()
