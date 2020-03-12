import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from os.path import isdir, exists
from pdfuinew import Ui_Form
from handles import PdfHandle, OcrHandle
from customwidgets import PreviewWidget
from supports import slot


class PdfWidget(Ui_Form, QWidget):

    engine_signal = pyqtSignal(str, bool)

    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account', None)
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.set_datas()
        self.init()
        self.account = account

    def _work_path(self):
        return self.lineEdit.text().strip('"').strip(' ')

    def set_datas(self):
        '''
        在QT5中，信号可以连接到一切可以调用的对象上，包括普通函数，成员函数，函数对象，lambda表达式；
        总的来说，信号与槽的连接有两种方式：1、直接连接 2、队列连接；默认的自动连接下，如果发射信号的线程
        （而不是发送者所在的线程）与接受者所驻足的线程相同，则是队列连接；
        如果发送信号的线程与接收者所驻足的不在一个线程，则是队列连接。直接连接下，
        槽函数在发送信号的线程中立即执行；队列连接情况下，槽函数在接收者所在的线程时间循环处理到时，才执行。
        '''
        self.pdf_handle = PdfHandle()
        self.pdf_thread = QThread()
        # self.pdf_handle.moveToThread(self.pdf_thread)
        self.pdf_thread.finished.connect(self.pdf_handle.deleteLater)
        self.pdf_handle.destroyed.connect(self.pdf_thread.deleteLater)

        self.ocr_handle = OcrHandle(self.pdf_handle)
        self.ocr_thread = QThread()
        self.ocr_handle.moveToThread(self.ocr_thread)
        self.ocr_thread.finished.connect(self.ocr_handle.deleteLater)
        self.ocr_handle.destroyed.connect(self.ocr_thread.deleteLater)
        self.ocr_handle.ocr_signal.connect(self.ocr_handle.ocr) #Qt.QueuedConnection
        self.ocr_thread.start()

        self.pdf_handle.open_signal.connect(self.render_pdf)
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
        self.listWidget.hide()
        self.pushButton_4.hide()
        self.frame_2.hide()
        self.spacelabel.setFixedWidth(self.pdf_handle.screenSize[0] / 12 + self.pushButton_4.width())
        self.spacelabel.hide()

    @PdfHandle.slot(signal='open_signal')
    def render_pdf(self):
        self.pdf_handle.open(self._work_path())
        self.pushButton_4.setChecked(True)
        self.pushButton_4.show()
        self.spacelabel.show()
        self.listWidget.show()
        self.frame_2.show()

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

    @slot(signal='points_signal', sender='displaylabel', desc='run in pdf_thread')
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
        self.displayLabel.metedata.update({'index': 0, 'points': []})
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

    @slot(signal='clicked',sender='preview_label', desc='run in pdf_thread')
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
        self.displayLabel.metedata.update({'index': row})
        self.displayLabel.update()

    def openSlot(self):
        pass

    def startSlot(self):  # checkfile
        file = self._work_path()
        if exists(file):
            if file[-3:].lower() in ['pdf', 'png', 'jpg', 'bmp', 'peg'] or isdir(file):
                self.pdf_thread.start()
                self.pdf_handle.open_signal.emit()
        else:
            QMessageBox.warning(self, '警告', '打开正确格式的文件')

    def analysisSlot(self):
        pass

    def leftAnSlot(self):
        if self.pushButton_4.isChecked():
            self.pushButton_4.setIcon(QIcon(":/image/img/indent-decrease.svg"))
            self.spacelabel.show()
            self.listWidget.show()
        else:
            self.pushButton_4.setIcon(QIcon(":/image/img/indent-increase.svg"))
            self.spacelabel.hide()
            self.listWidget.hide()

    def rightAnSlot(self):
        if self.pushButton_3.isChecked():
            self.pushButton_3.setIcon(QIcon(":/image/img/indent-decrease.svg"))
            self.textBrowser.hide()
        else:
            self.pushButton_3.setIcon(QIcon(":/image/img/indent-increase.svg"))
            self.textBrowser.show()

    def closeEvent(self, event):
        super().closeEvent(event)
        self.pdf_thread.quit()
        self.ocr_thread.quit()

    def anaTest(self):
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

OcrWidget = PdfWidget

        
def main():
    app = QApplication(sys.argv)
    win = PdfWidget()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()