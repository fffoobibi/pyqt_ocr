from sys import argv, exit
from math import sqrt
from re import findall, DOTALL
from sources import *

from os.path import expanduser, exists, join, abspath, basename, isdir, isfile, dirname
from os import popen
from PIL import ImageQt, Image
from copy import deepcopy
from configparser import ConfigParser
from datetime import datetime

from PyQt5.QtWidgets import (QWidget, QApplication, QMainWindow, QFileDialog,
                             QLabel, QHBoxLayout, QMenu, QMessageBox, QDialog,
                             QDesktopWidget, QAction, QPushButton)
from PyQt5.QtGui import QPixmap, QPen, QPainter, QCursor, QFont, QIcon
from PyQt5.QtCore import QThread, QObject, QRect, Qt, pyqtSignal, QTime
from ruia_ocr import BaiduOcrService, get_file_paths, BAIDU_ACCURATE_TYPE, BAIDU_GENERAL_TYPE, BAIDU_HANDWRITING_TYPE

from mainui import Ui_MainWindow
from advancedui import Ui_Dialog
from other import Other
from customwidgets import ImgLabel
from supports import Account, User, Config, DEFAULT_CONFIG
from handles import ResultsHandle, OcrHandle

g_dpi = 0
g_width = 0
g_height = 0

info_time = lambda: datetime.now().strftime('%H:%M:%S')
save_name = lambda: datetime.now().strftime('%Y%m%d_%H_%M_%S')

home = abspath(expanduser('~\\Desktop')) if exists(
    abspath(expanduser('~\\Desktop'))) else abspath(expanduser('~'))



def dpi(w_r, h_r, w, h):
    global g_dpi, g_width, g_height
    if g_dpi == 0:
        g_width = w
        g_height = h
        g_dpi = sqrt(w**2 + h**2) / sqrt((w_r / 10 * 0.394)**2 +
                                         (h_r / 10 * 0.394)**2)
    return g_dpi


class EditWidget(QWidget):
    def __init__(self, parent=None, pic: str = None, root=None):
        super().__init__(parent)
        self.initUI(pic)
        self.root = root
        self.setWindowFlags(Qt.WindowMinimizeButtonHint
                            | Qt.WindowCloseButtonHint)

    def initUI(self, pic):
        desktop = QApplication.desktop()
        pixmap = QPixmap(pic)
        p_width, p_height = pixmap.width(), pixmap.height()
        d_width, d_height = desktop.width(), desktop.height()
        if (p_width, p_height) > (d_width, d_height):
            scaled_x = max(p_width / d_width, p_height / d_height) + 0.35
            pixmap = pixmap.scaled(p_width / scaled_x, p_height / scaled_x)
        self.post_image = pixmap
        self.hbox = QHBoxLayout(self)
        self.lb = ImgLabel(self, draw_pixmap=pixmap)
        self.lb.setPixmap(pixmap)  # 在label上显示图片
        self.lb.setScaledContents(True)  # 让图片自适应label大小
        self.hbox.addWidget(self.lb)
        self.setLayout(self.hbox)
        self.setWindowTitle('编辑')
        self.lb.action2_signal.connect(lambda: self.close())

    def closeEvent(self, QCloseEvent):  ### 修改
        self.root.window_list.clear()
        self.root.pic_edited = True
        # self.root._post_image = ImageQt.fromqpixmap(self.post_image)
        QCloseEvent.accept()

    def showEvent(self, QShowEvent):
        region = self.root.run_info['advanced']['region']
        self.lb.points.clear()
        if region != 'none':
            for box in region.strip(';').split(';'):
                print(box)
                tmp = list(map(int, box.split(',')))
                self.lb.points.append(tmp)
            self.lb.x0, self.lb.y0, self.lb.x1, self.lb.y1 = self.lb.points[-1]
        QWidget.showEvent(self, QShowEvent)

    def displayCenter(self):
        self.setFixedSize(self.width(), self.height())
        cp = QDesktopWidget().availableGeometry().center()
        self.move(cp.x() - 1 / 2 * self.width(),
                  cp.y() - 1 / 2 * self.height())


class AdvancedDialog(QDialog, Ui_Dialog):

    save_user = pyqtSignal(User)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.user = user

    def update_account(self, from_user:User):
        self.lineEdit.setText(from_user.alias)
        self.login_lineEdit_id.setText(from_user.id)
        self.login_lineEdit_key.setText(from_user.key)
        self.login_lineEdit_secret.setText(from_user.secret)

    def update_config(self, from_config: Config):
        if from_config.get('out', 'format') == 'txt':
            self.out_lineEdit_title.setEnabled(False)
            self.out_comboBox.setCurrentIndex(0)
        else:
            self.out_lineEdit_title.setEnabled(True)
            self.out_comboBox.setCurrentIndex(1)
        self.out_lineEdit_dir.setText(from_config.get('out', 'directory'))

        self.comboBox.setCurrentIndex(
            from_config.get('recognition', 'type', parse=int))

        self.reg_timeEdit.setTime(
            QTime(0, 0, from_config.get('recognition', 'delay', int)))

        self.reg_comboBox.setEditText(from_config.get('recognition', 'number'))
        self.adv_lineEdit.setText(from_config.get('advanced', 'region'))

    def set_resetSlot(self, value: int):
        self.update_config(DEFAULT_CONFIG)
        self.update()

    def set_applySlot(self):
        user = self.user
        config = self.user.config
        user.id = self.login_lineEdit_id.text(),
        user.key = self.login_lineEdit_key.text(),
        user.secret = self.login_lineEdit_secret.text()
        user.alias = self.lineEdit.text()
        config.update_from_dict({
            'recognition': {
                'delay': self.reg_timeEdit.text()[:-1],
                'number': int(self.reg_timeEdit.text()[:-1]), 
                'type': self.comboBox.currentIndex()
            },
            'out': {
                'format': 'txt' if self.out_comboBox.currentText().startswith('文本') else 'xlsx',
                'directory': self.out_lineEdit_dir.text(),
                'title': 'none'
            },
            'advanced': {
                'region': self.adv_lineEdit.text(),
                'text1': 'none',
                'clean': 'false'
            }})
        self.save_user.emit(user)
        self.close()

    def out_buttonSlot(self):
        pass

    def out_fmtSlot(self, index: int):
        if index == 0:
            if self.user.config.get('out', 'format') == 'txt':
                self.out_lineEdit_title.setEnabled(False)
        else:
            if self.user.config.get('out', 'format') == 'xlsx':
                self.out_lineEdit_title.setEnabled(True)

    def reg_buttonSlot(self):
        pass

    def adv_buttonAddSlot(self):
        pass

    def adv_buttonHelpSlot(self):
        pass


class Win(QMainWindow, Ui_MainWindow):

    window_list = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.customSetup()
        self.customSetupPageTwo()
        self.actionsSet()
        self.styleSet()

    def customSetupPageTwo(self):
        self.actionzhu = QAction('主界面', self)
        self.menu_2.addAction(self.actionzhu)
        self.other = Other()
        self.other.backsig.connect(
            lambda: self.stackedWidget.setCurrentIndex(0))
        self.stackedWidget.addWidget(self.other)

    def actionsSet(self):
        self.menu.setTitle('设置')
        self.actionfenxi.triggered.connect(self.anaSlot)
        self.actionzhu.triggered.connect(
            lambda: self.stackedWidget.setCurrentIndex(0))
        self.actionzhanghao.triggered.connect(self.menuSlot)
        self.actionshezhe.triggered.connect(self.dialogSlot)

        self.actionzhanghao.setText('配置')
        self.actionshezhe.setText('高级')

    def styleSet(self):
        def _(file):
            stylesheet = open(file).read()
            self.setStyleSheet(stylesheet)
            self.other.setStyleSheet(stylesheet)

        _('./sources/flatwhite.css')

    def anaSlot(self):
        self.stackedWidget.setCurrentIndex(1)

    def customSetup(self):
        def copy_latest():
            try:
                text = findall(r'.*?\>(.*)\</p\>', self.results[-1],
                               DOTALL)[-1]
                QApplication.clipboard().setText(text)
            except IndexError:
                ...

        self.setWindowIcon(QIcon(':/image/flatwhite/app.ico'))
        tmp_h = 600 / 768
        tmp_w = 800 / 1366
        self.resize(int(g_width * tmp_w), int(g_height * tmp_h))  # w, h
        font = QFont()
        font.setBold(True)
        self.lineEdit.setFont(font)
        self.textBrowser_2.append('<p style="color:black">日志记录</p>')
        self.setWindowTitle('Ocr')
        self.prefix = None
        self.pic_edited = False
        self.results = []
        self.imgs = []
        self.account = Account()
        self.user = self.account.active_user()
        self.desktop = QApplication.desktop()
        self.dialog = AdvancedDialog(self, user=self.account.active_user())
        self.ocr_thread = QThread()

        self.textBrowser_1.clear_signal.connect(
            lambda: self.results.clear())  #####
        self.textBrowser_1.latest_signal.connect(copy_latest)  #######

    def picSlot(self):
        if self.comboBox.currentText() == '图片':
            pic_name, file_types = QFileDialog.getOpenFileName(
                self, '图片', home, '图片(*.png;*.jpg;*.jpeg;*.bmp)')
            if pic_name:
                self.lineEdit.setText(pic_name)
        else:
            dir_name = QFileDialog.getExistingDirectory(self, '文件夹', home)
            if dir_name:
                self.lineEdit.setText(dir_name)

    def editSlot(self):
        if self.comboBox.currentIndex() == 0:
            if self.lineEdit.text().strip('"').strip(' ')[-3:].lower() not in [
                    'jpg', 'png', 'bmp', 'peg'
            ]:
                QMessageBox.warning(self, '警告', '请添加jpg, png, bmp, jpeg格式的图片')
            else:
                if len(self.window_list) == 0:
                    if self.lineEdit.text():
                        edit_widget = EditWidget(pic=self.lineEdit.text(),
                                                 root=self)
                        self.window_list.append(edit_widget)
                        edit_widget.lb.points.points_signal.connect(
                            self.updateRegion)
                        edit_widget.show()
                        edit_widget.displayCenter()
                    else:
                        QMessageBox.warning(self, '提示', '选择图片或文件夹')
                else:
                    self.window_list[0].raise_()
        else:
            QMessageBox.warning(self, '警告', '不支持目录下编辑图片')

    def ocrSlot(self):
        self.user.config.set('parseinfo', 'workpath', self.lineEdit.text().strip('"').strip(' '))
        work_path = self.user.config.get('parseinfo', 'workpath')
        if not self.pic_edited:
            try:
                im = Image.open(self.lineEdit.text().strip('"').strip(' '))
                p_width, p_height = im.width, im.height
                d_width, d_height = self.desktop.width(
                ), self.desktop.height()
                if (p_width, p_height) > (d_width, d_height):
                    scaled_x = max(p_width / d_width,
                                    p_height / d_height) + 0.35
                    im = im.resize(
                        (p_width / scaled_x, p_height / scaled_x),
                        Image.ANTIALIAS)
                self._post_image = im
            except:
                ...

        if work_path:
            if work_path[-3:].lower() not in ['jpg', 'png', 'bmp', 'peg']:
                QMessageBox.warning(self, '警告',
                                    '请添加jpg, png, bmp, jpeg格式的图片')
            else:
                self.ocr_thread.start()
        else:
            QMessageBox.warning(self, '提示', '选择图片')
            

    def outSlot(self):
        file_name, file_types = QFileDialog.getSaveFileName(
            self, '文件', home + f'\\{save_name()}.txt', '文件(*.txt;*.xlsx)')
        if file_name:
            if file_name.endswith('txt'):
                out = map(lambda e: e[3:-4],
                          filter(lambda e: e.startswith('<p>'), self.results))
                with open(file_name, 'w+') as file:
                    file.write('\n'.join(out))

    def updateRegion(self, res: list):
        st = ''
        if res:
            for box in res:
                tmp = map(str, box)
                st += ','.join(tmp) + ';'
            self.run_info['advanced']['region'] = st
        else:
            self.run_info['advanced']['region'] = 'none'
        self.cfg.save(self.run_info)

    def displayOcr(self, st):
        if self.prefix is None:
            prefix = self.lineEdit.text().strip('"').strip('\'')
            if isfile(prefix):
                self.prefix = dirname(prefix)
            elif isdir(prefix):
                self.prefix = prefix
        self.results.append(st)
        self.textBrowser_1.append(f'<pre style="font-family:宋体">{st}</pre>')
        if st.startswith('<p style="font-weight:bold'):
            self.imgs.append(st[52:-5])
        if st.startswith('<p>'):
            if self.run_info['recognition']['type'] == '0':
                flag = '精准模式'
            elif self.run_info['recognition']['type'] == '1':
                flag = '通用模式'
            else:
                flag = '手写模式'

            if self.run_info['advanced']['region'] == 'none':
                region = '全局识别'
            else:
                region = '局部识别'
            self.textBrowser_2.append(
                f'<pre style="font-family:宋体">{len(self.imgs)}. [{info_time()}]--{join(self.prefix, self.imgs[-1])} {flag} {region} 识别完成... </pre>'
            )

    def menuSlot(self):
        popen(f'Notepad {self.cfg.file_path}')

    def dialogSlot(self):
        user = self.account.active_user()
        config = user.config
        self.dialog.update_account(from_user=user)
        self.dialog.update_config(from_config=config)
        self.dialog.exec_()

    def closeEvent(self, QCloseEvent):
        if self.window_list:
            for win in self.window_list:
                win.close()
        QCloseEvent.accept()


class InitDpi(QWidget):
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        desktop = QApplication.desktop()
        screen_rect = desktop.screenGeometry()
        height = screen_rect.height()
        width = screen_rect.width()
        dpi(desktop.widthMM(), desktop.heightMM(), width, height)
        font = QFont("宋体")
        font.setPixelSize(
            11 *
            (g_dpi / 96))  # CurrentFontSize *（DevelopmentDPI / CurrentFontDPI）
        app.setFont(font)
        self.close()


def main():
    app = QApplication(argv)
    InitDpi(app=app)
    myWin = Win()
    myWin.show()
    exit(app.exec_())


if __name__ == '__main__':
    main()