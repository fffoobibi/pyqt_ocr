from sys import argv, exit
from PIL import Image, ImageQt
from fitz import open as pdf_open
from os.path import isfile, exists, isdir, abspath, join
from os import listdir
import fitz

from PyQt5.QtWidgets import (QApplication, QWidget, QListWidgetItem,
                             QScrollBar, QVBoxLayout, QMessageBox, QLabel,
                             QListView)
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QSize, Qt
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen
from pdfui import Ui_Form
from customwidgets import ImgLabel, Validpoints


class EngineError(Exception):
    ...


class Engine(object):
    def __init__(self, path):

        if isfile(path) and (path[-3:].lower() == 'pdf'):
            self.render = pdf_open(path)
            self.isPdf = True
            pdf_pixmap = self.render[0].getPixmap(fitz.Matrix(2, 2))
            self.fmt = QImage.Format_RGBA8888 if pdf_pixmap.alpha else QImage.Format_RGB888
            self.stride = pdf_pixmap.stride

        elif exists(path) and isdir(path):
            self.render = path
            self.isPdf = False
        else:
            raise EngineError('渲染异常')
        self.__pagesView = None
        self.target = path

    def pagesView(self) -> list:
        if self.__pagesView is None:
            if self.isPdf:
                self.__pagesView = [
                    'Page_%s' % page
                    for page in range(1, self.render.pageCount + 1)
                ]
            else:
                self.__pagesView = [
                    abspath(join(self.dir, file)) for file in listdir(self.dir)
                ]
        return self.__pagesView

    def getPixmap(self, index, zoom=(1, 1)) -> QPixmap:
        if self.isPdf:
            pdf_pixmap = self.render[index].getPixmap(fitz.Matrix(*zoom))
            pixmap = QPixmap.fromImage(
                QImage(pdf_pixmap.samples, pdf_pixmap.width, pdf_pixmap.height,
                       self.stride, self.fmt))
            return pixmap
        else:
            return QPixmap(self.pagesView()[index])

    def __getitem__(self, index) -> QPixmap:
        return self.getPixmap(index)

    def __repr__(self):
        return f'Engine<{self.target}>'


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
        self.__scaledSize = None
        self.__previewSize = None
        self.__pageSize = None
        self.__screenSize = None
        self.__engine = None
        self.zoom = (1, 1)
        self.engined_counts = 0
        self.pixmaps = []
        self.pixmaps_points = []
        self.preview_pixmaps_points = []
        self.edited_pdfs = []

    def clear(self):
        self.__scaledSize = None
        self.__pageSize = None
        self.__screenSize = None
        self.__previewSize = None
        # self.pixmaps.clear()
        # self.pixmaps_points.clear()
        # self.preview_pixmaps_points.clear()
        # self.edited_pdfs.clear()
        self.clear_signal.emit()

    def setEngine(self, path):
        self.__engine = Engine(path)

    @property
    def screenSize(self) -> tuple:
        if self.__screenSize is None:
            desktop = QApplication.desktop()
            self.__screenSize = desktop.width(), desktop.height()
        return self.__screenSize


    @property
    def pageSize(self) -> tuple:
        if self.__pageSize is None:
            pix = self.__engine.getPixmap(0, self.zoom)
            self.__pageSize = pix.width(), pix.height()
        return self.__pageSize

    @property
    def previewSize(self) -> tuple:
        if self.__previewSize is None:
            p_width, p_height = self.pageSize
            d_width, d_height = self.screenSize
            zoom_width = d_width / 10
            zoom_height = p_height / p_width * zoom_width
            self.__previewSize = zoom_width, zoom_height
        return self.__previewSize

    
    @property
    def autoScaledSize(self) -> tuple:
        if self.__scaledSize is None:
            p_width, p_height = self.pageSize
            d_width, d_height = self.screenSize
            if (p_width, p_height) > (d_width, d_height):
                scaled_x = max(p_width / d_width, p_height / d_height) 
                self.__scaledSize = (p_width / scaled_x, p_height / scaled_x)
            else:
                self.__scaledSize = (p_width / p_height * d_height * 0.75,
                                     d_height * 0.75)
        return self.__scaledSize

    @autoScaledSize.setter
    def autoScaledSize(self, qsize: tuple):
        self.__scaledSize = qsize

    def renderPixmap(self, index, zoom=(1, 1)) -> QPixmap:
        pixmap = self.__engine.getPixmap(index, zoom)
        return pixmap

    def renderScaledPixmap(self,
                           index,
                           scaledSize: tuple = None,
                           aspectRatioMode=Qt.IgnoreAspectRatio,
                           transformMode=Qt.FastTransformation) -> QPixmap:
        if scaledSize:
            return self.renderPixmap(index).scaled(
                *scaledSize,
                aspectRatioMode=aspectRatioMode,
                transformMode=transformMode)
        return self.renderPixmap(index).scaled(*self.autoScaledSize,
                                               aspectRatioMode=aspectRatioMode,
                                               transformMode=transformMode)

    def rendering(self):
        render_indexes = []
        for index in range(len(self.__engine.pagesView())):
            render_indexes.append(index)

        self.pixmaps = render_indexes
        self.pixmaps_points = [
            [[]] for points in range(len(self.pixmaps))
        ]

    def open(self, path, parent_widget):
        self.engined_counts += 1
        self.edited_pdfs.append(path)

        try:
            if self.engined_counts == 1:
                flag = False
            else:
                flag = self.__engine.target == self.edited_pdfs[-1]
        except IndexError:
            flag = False
        finally:
            if flag:
                self.reload_signal.emit()
                while True:
                    if parent_widget.reloaded == QMessageBox.Yes:
                        self.clear()
                        self.setEngine(path)
                        self.rendering()
                        self.display_signal.emit()
                        parent_widget.reloaded = -1
                        break
                    elif parent_widget.reloaded == QMessageBox.No:
                        parent_widget.reloaded = -1
                        break
            else:
                self.clear()
                self.setEngine(path)
                self.rendering()
                self.display_signal.emit()
            self.thread().quit()

    def init(self):
        pass


class PdfWidget(Ui_Form, QWidget):

    engine_signal = pyqtSignal(str, bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.init()
        self.set_datas()

    def _file(self):
        return self.lineEdit.text().strip('"').strip(' ')

    def set_datas(self):
        self.reloaded = -1
        self._flag = 0
        self.pdf_handle = PdfHandle(self)
        self.pdf_thread = QThread()
        self.pdf_handle.moveToThread(self.pdf_thread)
        self.pdf_thread.started.connect(
            lambda: self.pdf_handle.open(self._file(), self))
        self.pdf_handle.display_signal.connect(self.updateListWidget)
        self.pdf_handle.reload_signal.connect(self.reload)
        self.pdf_handle.clear_signal.connect(lambda: self.listWidget.clear())
        self.label_2.points.points_signal.connect(self.updateListWidgetItem)

    def init(self):
        self.listWidget.itemClicked.connect(self.test)
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
        # pix = self.pdf_handle.pixmaps[index]
        # p_width, p_height = pix.width(), pix.height()
        p_width, p_height = self.pdf_handle.autoScaledSize
        width, height = self.pdf_handle.previewSize
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

        self.pdf_handle.pixmaps_points[index] = points
        # self.pdf_handle.preview_pixmaps_points[index] = process

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

        preview_label.setPixmap(pixmap)
        preview_label.setEditPixmap(pixmap)
        layout.addWidget(preview_label)
        indexlabel = QLabel(str(index + 1))
        indexlabel.setAlignment(Qt.AlignCenter)

        preview_label.clicked.connect(self.displayPdfPage)
        layout.addWidget(indexlabel)
        widget.setLayout(layout)
        return widget

    def updateListWidget(self):
        preview_size = self.pdf_handle.previewSize
        self.listWidget.setFixedWidth(preview_size[0] + 20)
        display_pixmap = self.pdf_handle.renderScaledPixmap(
            index=0, transformMode=Qt.SmoothTransformation)
        self.label_3.setText('1')
        self.label_2.setPixmap(display_pixmap)
        self.label_2.setEditPixmap(display_pixmap)
        self.label_2.setEdited(True)

        # 生成预览图
        for index in self.pdf_handle.pixmaps:
            pix = self.pdf_handle.renderScaledPixmap(
                index,
                scaledSize=preview_size
                # transformMode=Qt.SmoothTransformation)
            item = QListWidgetItem()
            widget = self.get_item_widget(pix, index)
            item.setSizeHint(QSize(*preview_size))
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, widget)
            QApplication.processEvents()

    def displayPdfPage(self, index):
        item = self.listWidget.currentItem()
        widget = self.listWidget.itemWidget(item)
        print('preview_label', widget.preview_label.size(), self.pdf_handle.previewSize)
        
        page = self.pdf_handle.renderScaledPixmap(
            index=index, transformMode=Qt.SmoothTransformation)
        self.label_2.points.clear()
        self.label_3.setText(str(index + 1))
        self.label_2.setPixmap(page)
        self.label_2.setEditPixmap(page)
        self.label_2.points.appends(self.pdf_handle.pixmaps_points[index])
        self.label_2.metedata = {'index': index}
        self.label_2.update()

    def openSlot(self):
        pass

    def confirmSlot(self):
        pdf_file = self.lineEdit.text().strip('"').strip(' ')
        if exists(pdf_file):
            if pdf_file[-3:].lower() == 'pdf':
                # self.engine_signal.emit(pdf_file, True)
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
