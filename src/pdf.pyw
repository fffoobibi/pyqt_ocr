from sys import argv, exit
from PIL import Image, ImageQt
from fitz import open as pdf_open
from fitz import Matrix
from functools import wraps
from os.path import isfile, exists, isdir, abspath, join
from os import listdir
from math import sqrt

from PyQt5.QtWidgets import (QApplication, QWidget, QListWidgetItem, QGraphicsOpacityEffect,
                             QScrollBar, QVBoxLayout, QMessageBox, QLabel,
                             QListView)
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QSize, Qt, QPropertyAnimation, QRect, QCoreApplication
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QFont, QIcon
from pdfui import Ui_Form

from customwidgets import PreviewWidget
from supports import *
from typing import List, NoReturn

# g_dpi = 0
# g_width = 0
# g_height = 0


# def dpi(w_r, h_r, w, h):
#     global g_dpi, g_width, g_height
#     if g_dpi == 0:
#         g_width = w
#         g_height = h
#         g_dpi = sqrt(w**2 + h**2) / sqrt((w_r / 10 * 0.394)**2 +
#                                          (h_r / 10 * 0.394)**2)
#     return g_dpi


# class InitDpi(QWidget):
#     def __init__(self, parent=None, app=None):
#         super().__init__(parent)
#         desktop = QApplication.desktop()
#         screen_rect = desktop.screenGeometry()
#         height = screen_rect.height()
#         width = screen_rect.width()
#         dpi(desktop.widthMM(), desktop.heightMM(), width, height)
#         font = QFont("宋体")
#         font.setPixelSize(
#             11 *
#             (g_dpi / 96))  # CurrentFontSize *（DevelopmentDPI / CurrentFontDPI）
#         app.setFont(font)
#         self.close()


class Engine(object):
    def __init__(self, path):
        if isfile(path) and (path[-3:].lower() == 'pdf'):
            self.render = pdf_open(path)
            self.isPdf = True
            self.isDir = False
            self.isFile = False

        elif exists(path) and isdir(path):
            self.render = path
            self.isPdf = False
            self.isDir = True
            self.isFile = False

        elif isfile(path) and (path[-4:].lower() in [
                '.png', '.bmp', '.jpg', 'jpeg'
        ]):
            print(111)
            self.isFile = True
            self.isPdf = False
            self.isDir = False
        self.__pagesView = None
        self.target = path

    def pagesView(self) -> list:
        if self.__pagesView is None:
            if self.isPdf:
                self.__pagesView = [
                    'Page_%s' % page
                    for page in range(1, self.render.pageCount + 1)
                ]
            elif self.isDir:
                self.__pagesView = [
                    abspath(join(self.target, file))
                    for file in listdir(self.target)
                ]
            else:
                self.__pagesView = [self.target]
        return self.__pagesView

    def pageCount(self):
        if self.isPdf:
            return self.render.pageCount
        return len(self.pagesView())

    def getPixmap(self, index, zoom=(1.0, 1.0)) -> QPixmap:
        if self.isPdf:
            x, y = zoom
            pdf_pixmap = self.render[index].getPixmap(Matrix(x, y))
            fmt = QImage.Format_RGBA8888 if pdf_pixmap.alpha else QImage.Format_RGB888
            pixmap = QPixmap.fromImage(
                QImage(pdf_pixmap.samples, pdf_pixmap.width, pdf_pixmap.height,
                       pdf_pixmap.stride, fmt))
            return pixmap
        else:
            return QPixmap(self.pagesView()[index])

    def __getitem__(self, index) -> QPixmap:
        return self.getPixmap(index)

    def __repr__(self):
        return f'Engine<{self.target}>'


class PdfHandle(QObject):

    open_signal = pyqtSignal()
    display_signal = pyqtSignal()
    reload_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    ocr_signal = pyqtSignal(list, list)

    @staticmethod
    def slot(signal: str = '', desc=''):
        def outer(func):
            @wraps(func)
            def inner(self, *args, **kwargs):
                res = func(self, *args, **kwargs)
                return res

            return inner

        return outer

    def __init__(self):
        super().__init__()
        self.__screenSize = None
        self.__engine = None

        self.reload = QMessageBox.No
        self.engined_counts = 0
        self.is_editing = False

        self.pixmaps = []
        self.pixmaps_points = []
        self.edited_pdfs = []

        self.__pdf_preview = None
        self.__pdf_previewZoom = None
        self.__pdf_displaySize = None
        self.__pdf_displayZoom = None

        self.__previewZooms: list = None
        self.__displayZooms: list = None
        self.__pageSizes: list = None

    def clear(self):
        # if self.reload == QMessageBox.Yes:

        self.__previewZooms: list = None
        self.__displayZooms: list = None
        self.__pageSizes: list = None

        self.__screenSize = None
        self.is_editing = False

        self.__pdf_previewSize = None
        self.__pdf_previewZoom = None
        self.__pdf_displaySize = None
        self.__pdf_displayZoom = None

        self.pixmaps.clear()
        self.pixmaps_points.clear()
        self.edited_pdfs.clear()
        self.clear_signal.emit()

    def setEngine(self, path):
        self.__engine = Engine(path)

    def getEngine(self) -> Engine:
        return self.__engine

    @property
    def screenSize(self) -> Size:
        if self.__screenSize is None:
            desktop = QApplication.desktop()
            self.__screenSize = desktop.width(), desktop.height()
        return self.__screenSize

    def pageSizes(self) -> List[Size]:
        if self.__pageSizes is None:
            if self.__engine.isPdf:
                pix = self.__engine.getPixmap(index=0, zoom=(1, 1))
                self.__pageSizes = [(pix.width(), pix.height()) for i in range(self.pageCount())]
            elif self.__engine.isFile:
                pix = self.__engine.getPixmap(index=0)
                self.__pageSizes = [(pix.width(), pix.height())]
            else:
                page_size = []
                for index in range(self.pageCount()):
                    pix = self.__engine.getPixmap(index=index)
                    page_size.append((pix.width(), pix.height()))
                self.__pageSizes = page_size
        return self.__pageSizes

    def previewSize(self, index) -> Size:
        if self.__engine.isPdf:
            if self.__pdf_previewSize is None:
                p_width, p_height = self.pageSizes()[0]
                d_width, d_height = self.screenSize
                zoom_width = d_width / 12
                zoom_height = p_height / p_width * zoom_width
                self.__pdf_previewSize = round(zoom_width, 0), round(zoom_height, 0)
            return self.__pdf_previewSize
        else:
            p_width, p_height = self.pageSizes()[index]
            d_width, d_height = self.screenSize
            zoom_width = d_width / 12
            zoom_height = p_height / p_width * zoom_width
            return round(zoom_width, 0), round(zoom_height, 0)


    def previewZoom(self, index) -> Zoom:
        if self.__engine.isPdf:
            if self.__pdf_previewZoom is None:
                p_width, p_height = self.pageSizes()[0]
                width, height = self.previewSize(0)
                self.__pdf_previewZoom = width / p_width, width / p_width
            return self.__pdf_previewZoom
        else:
            p_width, p_height = self.pageSizes()[0]
            width, height = self.previewSize(0)
            return width / p_width, width / p_width

    
    def displayZoom(self, index, file_auto=False, dir_auto=False) -> Zoom:
        def auto_scaled(target, scaled=True):
            p_width, p_height = target
            d_width, d_height = self.screenSize
            if (p_width, p_height) > (d_width, d_height):
                scaled_x = max(p_width / d_width, p_height / d_height) - 0.1
                displayZoom = scaled_x, scaled_x
                return displayZoom
            else:
                displayZoom = d_height * 0.8 / p_height, d_height * 0.8 / p_height
                if scaled:
                    return displayZoom
                return 1.0, 1.0
        if self.__displayZooms is None:
            if self.__engine.isPdf:
                if self.__pdf_displayZoom is None:
                    target = self.pageSizes()[index]
                    diszoom = auto_scaled(target)
                    self.__displayZooms = (diszoom for i in range(self.pageCount()))
                    self.__pdf_displayZoom = diszoom
                return self.__pdf_displayZoom
            elif self.__engine.isFile:
                target= self.pageSizes()[index]
                self.__displayZooms = [auto_scaled(target, False)]
            elif self.__engine.isDir:
                zooms = []
                for index in range(self.pageCount()):
                    pix = self.renderPixmap(index)
                    target = pix.width(), pix.height()
                    diszoom = auto_scaled(target, scaled=False)
                    zooms.append(diszoom)
                self.__displayZooms = zooms
        if self.__engine.isPdf:
            return self.__pdf_displayZoom
        return self.__displayZooms[index]


    def displaySize(self, index) -> Size:
        if self.__engine.isPdf:
            if self.__pdf_displaySize is None:
                p_width, p_height = self.pageSizes()[0]
                dis_zoom = self.displayZoom(0)
                width = round(p_width * dis_zoom[0], 0)
                height = round(p_height * dis_zoom[1], 0)
                self.__pdf_displaySize = width, height
            return self.__pdf_displaySize
        else:
            p_width, p_height = self.pageSizes()[index]
            dis_zoom = self.displayZoom(index)
            width, height = round(p_width * dis_zoom[0], 0), round(p_height * dis_zoom[1], 0)
            return width, height

    def pageCount(self) -> int:
        return self.__engine.pageCount()

    def renderPixmap(self, index, zoom=(1, 1)) -> QPixmap:
        pixmap = self.__engine.getPixmap(index, zoom)
        return pixmap

    def rendering(self) -> NoReturn:
        self.is_editing = True
        render_indexes = []
        for index in range(self.pageCount()):
            render_indexes.append(index)

        self.pixmaps = render_indexes
        self.pixmaps_points = [[[]] for points in range(len(self.pixmaps))]
        print('pixmaps', self.pixmaps)

    def open(self, path) -> NoReturn:
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
                self.reload_signal.emit()  # 阻塞
                if self.reload == QMessageBox.Yes:
                    self.clear()
                    self.setEngine(path)
                    self.rendering()
                    self.display_signal.emit()
                    self.reload = QMessageBox.No
                    print('redolad')
                elif self.reload == QMessageBox.No:
                    pass
            else:
                self.clear()
                self.setEngine(path)
                self.rendering()
                self.display_signal.emit()

    def init(self):
        pass


class PdfWidget(Ui_Form, QWidget):

    engine_signal = pyqtSignal(str, bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.init()
        self.set_datas()
        print('init', QThread.currentThreadId())

    def _work_path(self):
        return self.lineEdit.text().strip('"').strip(' ')

    def set_datas(self):
        self.reloaded = -1
        self._flag = 0
        self.pdf_handle = PdfHandle()
        self.pdf_thread = QThread()
        self.pdf_handle.moveToThread(self.pdf_thread)
        self.radioButton.setText('22')
        self.radioButton.showMaximized()
        # self.radioButton.setChecked(True)
        self.radioButton.setFixedHeight(30)

        self.pdf_thread.finished.connect(self.pdf_handle.deleteLater)
        self.pdf_handle.destroyed.connect(self.pdf_thread.deleteLater)

        self.pdf_handle.open_signal.connect(
            lambda: self.pdf_handle.open(self._work_path()))

        self.pdf_handle.display_signal.connect(self.updateListWidget)
        self.pdf_handle.reload_signal.connect(self.reload)
        self.pdf_handle.clear_signal.connect(self.clear_infos)

        self.displayLabel.points.points_signal.connect(
            self.updateListWidgetItem)
        self.lineEdit_2.current_page.connect(self.jump)

    def jump(self, index):
        if self.pdf_handle.is_editing:
            if index > (self.pdf_handle.pageCount() - 1):
                index = self.pdf_handle.pageCount() - 1
                self.listWidget.setCurrentRow(index)
            else:
                self.listWidget.setCurrentRow(index)
            current = self.listWidget.currentItem()
            widget = self.listWidget.itemWidget(current)
            widget.preview_label.clicked.emit(index)

    def init(self):
        self.setStyleSheet(open('./sources/flatwhite.css').read())
        self.setWindowTitle('PDF')
        self.label_2.setText('of 0')
        self.lineEdit_2.setText('0')
        self.displayLabel.hide()

    @PdfHandle.slot(signal='clear_signal')
    def clear_infos(self):
        self.listWidget.clear()
        self.displayLabel.points.clear()

    @PdfHandle.slot(signal='reload_signal')
    def reload(self):
        replay = QMessageBox.question(self, 'PDF', '确认重新加载pdf么?',
                                      QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
        self.pdf_handle.reload = replay

    @PdfHandle.slot(desc='run in pdf_thread')
    def updateListWidgetItem(self, points):
        self.displayLabel.points.clear()
        self.displayLabel.points.appends(points)

        index = int(self.lineEdit_2.text()) - 1
        p_width, p_height = self.pdf_handle.displaySize(index)
        width, height = self.pdf_handle.previewSize(index)
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
        item = self.listWidget.item(index)
        preview_label = self.listWidget.itemWidget(item).preview_label
        preview_label.points.clear()
        preview_label.points.appends(process)
        preview_label.update()

    @PdfHandle.slot(desc='run in pdf_thread')
    def get_item_widget(self, pixmap, index):
        shadow_width = self.pdf_handle.screenSize[0] / 12 / 14
        widget = PreviewWidget(index, pixmap, shadow_width)
        widget.preview_label.clicked.connect(self.displayPdfPage)
        widget.preview_label.setFixedSize(*self.pdf_handle.previewSize(index))
        return widget

    @PdfHandle.slot(signal='display_signal')
    def updateListWidget(self):  # 槽函数
        shadow_width = self.pdf_handle.screenSize[0] / 12 / 14
        preview_width, preview_height = self.pdf_handle.previewSize(0)
        preview_zoom = self.pdf_handle.previewZoom(0)
        display_pixmap = self.pdf_handle.renderPixmap(
            0, self.pdf_handle.displayZoom(0))

        self.label_2.setText('of %s' % self.pdf_handle.pageCount())
        self.lineEdit_2.setText('1')

        self.listWidget.setFixedWidth(preview_width + shadow_width * 2 +
                                    10 * 2 + 20)
        self.displayLabel.setPixmap(display_pixmap)
        self.displayLabel.setEditPixmap(display_pixmap)
        self.displayLabel.setEdit(True)
        self.displayLabel.show()

        engine = self.pdf_handle.getEngine()

        # 生成预览图
        self.listWidget.indexes = self.pdf_handle.pixmaps
        for index in self.pdf_handle.pixmaps:
            if engine.isPdf:
                pix = self.pdf_handle.renderPixmap(index, preview_zoom)
                item = QListWidgetItem()
                widget = self.get_item_widget(pix, index)
                item.setSizeHint(
                    QSize(preview_width + shadow_width * 2,
                        preview_height + shadow_width * 2))
            else:
                pix = self.pdf_handle.renderPixmap(index, self.pdf_handle.previewZoom(index))
                item = QListWidgetItem()
                widget = self.get_item_widget(pix, index)
                preview_width, preview_height = self.pdf_handle.previewSize(index)
                item.setSizeHint(
                    QSize(preview_width + shadow_width * 2,
                        preview_height + shadow_width * 2))

            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, widget)
            QApplication.processEvents()
        self.listWidget.setCurrentRow(0)

    @PdfHandle.slot(desc='run in pdf_thread')
    def displayPdfPage(self, index):
        item = self.listWidget.currentItem()
        row = self.listWidget.currentRow()
        page = self.pdf_handle.renderPixmap(index=index,
                                            zoom=self.pdf_handle.displayZoom(0))
        self.displayLabel.points.clear()
        self.lineEdit_2.setText(str(row + 1))
        self.displayLabel.setPixmap(page)
        self.displayLabel.setEditPixmap(page)
        self.displayLabel.points.appends(self.pdf_handle.pixmaps_points[index])
        self.displayLabel.update()

    def openSlot(self):
        pass

    def confirmSlot(self):
        # pdf_file = self._work_path()
        # if exists(pdf_file):
        #     if pdf_file[-3:].lower() == 'pdf':
        #         self.pdf_thread.start()
        #         self.pdf_handle.open_signal.emit()
        # else:
        #     QMessageBox.warning(self, '警告', '打开正确的pdf文件')

        pdf_file = self._work_path()
        self.pdf_thread.start()
        self.pdf_handle.open_signal.emit()
       

        

    def leftAnSlot(self):
        rect = self.listWidget.geometry()
        self.animL = QPropertyAnimation(self.listWidget,
                                        b'geometry')  
        self.animL.setDuration(200) 
        if self.pushButton_4.isChecked():
            self.animL.setStartValue(rect)  
            self.animL.setEndValue(QRect(-rect.width(), rect.y(), rect.width(),
                                     rect.height()))  
        else:
            self.animL.setStartValue(rect)  
            self.animL.setEndValue(QRect(0, rect.y(), rect.width(),
                                     rect.height()))  
        self.animL.start()
        if self.pushButton_4.isChecked():
            self.pushButton_4.setIcon(QIcon(":/image/img/indent-increase.svg"))
        else:
            self.pushButton_4.setIcon(QIcon(":/image/img/indent-decrease.svg"))

    def rightAnSlot(self):
        rect = self.textBrowser.geometry()
        self.anim = QPropertyAnimation(self.textBrowser,
                                       b'geometry')  # 设置动画的对象及其属性
        self.anim.setDuration(300)  # 设置动画间隔时间
        if self.pushButton_3.isChecked():
            self.anim.setStartValue(rect)  # 设置动画对象的起始属性
            self.anim.setEndValue(
                QRect(self.width(), rect.y(), rect.width(),
                      rect.height()))  # 设置动画对象的结束属性
        else:
            self.anim.setStartValue(rect)
            self.anim.setEndValue(
                QRect(0, rect.y(), rect.width(),
                      rect.height()))
            self.textBrowser.show()
        self.anim.start()  # 启动动画
        if self.pushButton_3.isChecked():
            self.pushButton_3.setIcon(QIcon(":/image/img/indent-decrease.svg"))
        else:
            self.pushButton_3.setIcon(QIcon(":/image/img/indent-increase.svg"))


def main():
    # QCoreApplication.setAttribute(Qt.AA_DisableHighDpiScaling)
    app = QApplication(argv)
    # InitDpi(app=app)
    pdfwidget = PdfWidget()
    pdfwidget.show()
    exit(app.exec_())


if __name__ == "__main__":
    main()