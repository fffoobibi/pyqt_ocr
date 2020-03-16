import sys
from PyQt5.QtWidgets import QWidget, QApplication, QListWidgetItem, QMessageBox, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QThread, QSize

from os.path import isdir, exists
from pdfuinew import Ui_Form
from handles import PdfHandle, OcrHandle
from customwidgets import PreviewWidget
from supports import *
from srcs import *


class PdfWidget(Ui_Form, QWidget):
    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account', None)
        super().__init__(*args, **kwargs)
        self.account = account or Account()
        self.setupUi(self)
        self.setHandles()
        self.init()

    def _work_path(self):
        return self.lineEdit.text().strip('"').strip(' ')

    def setHandles(self):
        self.pdf_handle = PdfHandle()
        self.pdf_thread = QThread()
        self.pdf_handle.moveToThread(self.pdf_thread)
        self.pdf_thread.finished.connect(self.pdf_handle.deleteLater)
        self.pdf_handle.destroyed.connect(self.pdf_thread.deleteLater)
        # self.pdf_thread.start()

        self.ocr_handle = OcrHandle(self.pdf_handle)  #self.pdf_handle
        self.ocr_thread = QThread()
        self.ocr_handle.moveToThread(self.ocr_thread)
        self.ocr_thread.finished.connect(self.ocr_handle.deleteLater)
        self.ocr_handle.destroyed.connect(self.ocr_thread.deleteLater)
        self.ocr_handle.ocr_signal.connect(self.ocr_handle.ocr) 
        self.ocr_handle.results_signal.connect(self.display)
        self.ocr_thread.start()

        self.pdf_handle.open_signal.connect(self.render_pdf)
        self.pdf_handle.display_signal.connect(self.updateListWidget)
        self.pdf_handle.reload_signal.connect(self.reload)
        self.pdf_handle.clear_signal.connect(self.clear_infos)

        self.textBrowser.copy_latest.connect(self.copy_latest)
        self.displayLabel.points.points_signal.connect(
            self.updateListWidgetItem)

        self.lineEdit_2.current_page.connect(self.jump)
        self.checkBox.stateChanged.connect(self.updateCheckstate)
        self.radioButton.toggled.connect(self.updateRadiostate)
        self.radioButton_2.toggled.connect(self.updateRadiostate)
        self.radioButton_3.toggled.connect(self.updateRadiostate)


    @slot(signal='toggled', sender='radioButtons')
    def updateRadiostate(self, state):
        user = self.account.active_user()
        if self.sender() == self.radioButton:
            if state:
                user.config.set('recognition', 'type', 0)
        elif self.sender() == self.radioButton_2:
            if state:
                user.config.set('recognition', 'type', 1)
        elif self.sender() == self.radioButton_3:
            if state:
                user.config.set('recognition', 'type', 2)
        user.sync(self.account)

    @slot(signal='stateChanged', sender='checkBox')
    def updateCheckstate(self, state: int):
        index = int(self.lineEdit_2.text()) - 1
        try:
            if state == 2:
                self.pdf_handle.select_state[index] = True
            elif state == 0:
                self.pdf_handle.select_state[index] = False
        except:
            ...

    def updatePageCheckState(self, index: int) -> NoReturn:
        if self.pdf_handle.select_state[index] == True:
            self.checkBox.setChecked(True)
        else:
            self.checkBox.setChecked(False)

    def updateRadioState(self) -> NoReturn:
        user = self.account.active_user()
        flag = user.config.get('recognition', 'type', int)
        if flag== 0:
            self.radioButton.setChecked(True)
        elif flag == 1:
            self.radioButton_2.setChecked(True)
        elif flag == 2:
            self.radioButton_3.setChecked(True)

    @slot(signal='returnPressed', sender='lineEdit_2')
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
        self.comboBox.setItemIcon(0, QIcon(':/image/img/file-pdf.svg'))
        self.comboBox.setItemIcon(1, QIcon(':/image/img/image.svg'))
        self.comboBox.setItemIcon(2, QIcon(':/image/img/folder.svg'))
        self.setWindowTitle('PDF')
        self.label_2.setText('of 0')
        self.lineEdit_2.setText('0')
        self.listWidget.hide()
        self.pushButton_4.hide()
        self.frame_2.hide()
        self.spacelabel.setFixedWidth(self.pdf_handle.screenSize[0] / 12 +
                                      self.pushButton_4.width())
        self.spacelabel.hide()

    @slot(signal='open_signal', sender='')
    def render_pdf(self):
        self.pdf_handle.setEngine(self._work_path())
        if self.pdf_handle.getEngine().isFile:
            self.pushButton_4.setChecked(False)
            self.pushButton_4.setIcon(QIcon(':/image/img/indent-decrease.svg'))
        else:
            self.pushButton_4.setChecked(True)
            self.pushButton_4.setIcon(QIcon(':/image/img/indent-decrease.svg'))
            self.listWidget.show()
        self.pushButton_4.show()
        self.spacelabel.show()
        self.frame_2.show()
        self.pdf_handle.open(self._work_path())
        
    @slot(signal='clear_signal', sender='')
    def clear_infos(self):
        self.listWidget.clear()
        self.displayLabel.points.clear()
        import gc; gc.collect()

    @slot(signal='reload_signal', sender='')
    def reload(self):
        msg = self.comboBox.currentText()
        replay = QMessageBox.question(self, msg, f'确认重新加载{msg}么?',
                                      QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
        self.pdf_handle.reload = replay

    def _disPointsToPrePoints(self, dis_index,
                              dis_points: RectCoords) -> RectCoords or [[]]:
        p_width, p_height = self.pdf_handle.displaySize(dis_index)
        width, height = self.pdf_handle.previewSize(dis_index)
        process = []
        for point in dis_points:
            tmp = []
            if point:
                x1, y1, x2, y2 = point
                x3 = x1 / p_width * width
                y3 = y1 / p_height * height
                x4 = x2 / p_width * width
                y4 = y2 / p_height * height
                tmp.extend([x3, y3, x4, y4])
                process.append(tmp)
        return process if process else [[]]

    @slot(signal='points_signal', sender='displaylabel')
    def updateListWidgetItem(self, points):
        self.pdf_handle.fake_pixmaps_indexes = self.listWidget.indexes # 重要
        self.displayLabel.points.clear()
        self.displayLabel.points.appends(points)
        index = int(self.lineEdit_2.text()) - 1
        process = self._disPointsToPrePoints(index, points)
        self.pdf_handle.pixmaps_points[index] = points
        item = self.listWidget.item(index)
        preview_label = self.listWidget.itemWidget(item).preview_label
        preview_label.points.clear()
        preview_label.points.appends(process)
        preview_label.update()

    def get_item_widget(self, pixmap, index):
        shadow_width = self.pdf_handle.screenSize[0] / 12 / 14
        widget = PreviewWidget(index, pixmap, shadow_width)
        widget.preview_label.clicked.connect(self.displayPdfPage)
        widget.preview_label.reset_signal.connect(self.resetListWidget)
        widget.preview_label.setFixedSize(*self.pdf_handle.previewSize(index))
        return widget

    @slot(signal='reset_signal', sender='preview_label')
    def resetListWidget(self):
        self.listWidget.indexes = self.pdf_handle.pixmaps_indexes.copy()
        self.pdf_handle.fake_pixmaps_indexes = self.listWidget.indexes # 重要
        self.pdf_handle.select_state = [True] * len(self.pdf_handle.pixmaps_indexes)

        self.updatePageCheckState(0)
        self.updateRadioState()
        render_type = self.pdf_handle.getEngine().render_type
        if render_type in ['pdf', 'file']:
            for index, label_points in enumerate(self.pdf_handle.pixmaps_points):
                item = self.listWidget.item(index)
                preview_label = self.listWidget.itemWidget(item).preview_label
                preview_label.index = index
                preview_label.setEditPixmap(
                    self.pdf_handle.renderPixmap(
                        index, pdf_prezoom=self.pdf_handle.previewZoom(index)))
                preview_label.points.clear()
                preview_label.points.appends(
                    self._disPointsToPrePoints(index, label_points))
                preview_label.update()
                QApplication.processEvents()

            self.listWidget.setCurrentRow(0)
            item = self.listWidget.item(index)
            preview_label = self.listWidget.itemWidget(item).preview_label
            preview_label.clicked.emit(0)
        else:
            self.listWidget.clear()
            self.pdf_handle.display_signal.emit(0, self.pdf_handle.pixmaps_indexes)
            for index, label_points in enumerate(self.pdf_handle.pixmaps_points):
                item = self.listWidget.item(index)
                preview_label = self.listWidget.itemWidget(item).preview_label
                preview_label.points.clear()
                preview_label.points.appends(
                    self._disPointsToPrePoints(index, label_points))
                preview_label.update()
                QApplication.processEvents()


    @slot(signal='display_signal', sender='pdf_handle')
    def updateListWidget(self, dis_index: int,
                         list_widget_indexes: list):  # 槽函数

        engine = self.pdf_handle.getEngine()

        shadow_width = self.pdf_handle.screenSize[dis_index] / 12 / 14
        preview_width, preview_height = self.pdf_handle.previewSize(dis_index)
        preview_zoom = self.pdf_handle.previewZoom(dis_index)
        display_zoom = self.pdf_handle.displayZoom(dis_index)
        display_pixmap = self.pdf_handle.renderPixmap(dis_index, display_zoom)

        # tets = self.pdf_handle.renderPixmap(0, pdf_prezoom=True)
        # tets.save('1.png')

        self.label_2.setText('of %s' % self.pdf_handle.pageCount())
        self.lineEdit_2.setText(str(dis_index + 1))

        self.listWidget.setFixedWidth(preview_width + shadow_width * 2 +
                                      10 * 2 + 20)
        self.displayLabel.setPixmap(display_pixmap)
        self.displayLabel.setEditPixmap(True)
        self.displayLabel.setEdit(True)
        self.displayLabel.show()
        self.filelabel.setText(engine.getName(dis_index))

        self.updatePageCheckState(dis_index)
        self.updateRadioState()

        # 生成预览图
        self.listWidget.indexes = self.pdf_handle.pixmaps_indexes.copy()
        self.pdf_handle.fake_pixmaps_indexes = self.listWidget.indexes # 重要

        for index in list_widget_indexes:
            if engine.isPdf:
                pix = self.pdf_handle.renderPixmap(index, preview_zoom)
                item = QListWidgetItem()
                widget = self.get_item_widget(pix, index)
                item.setSizeHint(
                    QSize(preview_width + shadow_width * 2,
                          preview_height + shadow_width * 2))
            else:
                pix = self.pdf_handle.renderPixmap(
                    index, self.pdf_handle.previewZoom(index))
                item = QListWidgetItem()
                widget = self.get_item_widget(pix, index)
                preview_width, preview_height = self.pdf_handle.previewSize(
                    index)
                item.setSizeHint(
                    QSize(preview_width + shadow_width * 2,
                          preview_height + shadow_width * 2))

            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, widget)
            QApplication.processEvents()
        self.listWidget.setCurrentRow(dis_index)
        

    @slot(signal='clicked', sender='preview_label', desc='run in pdf_thread')
    def displayPdfPage(self, index):
        item = self.listWidget.currentItem()
        row = self.listWidget.currentRow()
        page = self.pdf_handle.renderPixmap(
            index=index, zoom=self.pdf_handle.displayZoom(index))

        self.displayLabel.points.clear()
        self.lineEdit_2.setText(str(row + 1))
        self.displayLabel.setPixmap(page)
        self.displayLabel.setEditPixmap(page)
        self.displayLabel.points.appends(self.pdf_handle.pixmaps_points[index])
        self.displayLabel.update()
        self.filelabel.setText(self.pdf_handle.getEngine().getName(index))

        self.updatePageCheckState(index)
        self.updateRadioState()

    def openSlot(self):
        if self.comboBox.currentText() == '图片':
            pic_name, file_types = QFileDialog.getOpenFileName(
                self, '图片', home, '图片(*.png;*.jpg;*.jpeg;*.bmp)')
            if pic_name:
                self.lineEdit.setText(pic_name)
        elif self.comboBox.currentText() == '目录':
            dir_name = QFileDialog.getExistingDirectory(self, '文件夹', home)
            if dir_name:
                self.lineEdit.setText(dir_name)
        else:
            pdf_name, file_types = QFileDialog.getOpenFileName(
                self, 'pdf', home, 'PDF(*.pdf)')
            if pdf_name:
                self.lineEdit.setText(pdf_name)

    def startSlot(self):  # checkfile
        file = self._work_path()
        if exists(file):
            if file[-3:].lower() in ['pdf', 'png', 'jpg', 'bmp', 'peg'
                                     ] or isdir(file):
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
                QRect(0, rect.y(), rect.width(), rect.height()))
            self.textBrowser.show()
        self.anim.start()  # 启动动画

    @slot(signal='result_signal', sender='ocr_handle')
    def display(self, st):
        self.textBrowser.append(st)

    @slot(signal='copy_latest', sender='ctextbrowser')
    def copy_latest(self):
        if self.ocr_handle.latest_result:
            QApplication.clipboard().setText(self.ocr_handle.latest_result[-1])


OcrWidget = PdfWidget


def main():
    app = QApplication(sys.argv)
    win = PdfWidget()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
