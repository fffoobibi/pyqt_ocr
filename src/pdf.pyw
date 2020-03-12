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