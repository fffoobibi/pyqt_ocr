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

g_dpi = 0
g_width = 0
g_height = 0

info_time = lambda: datetime.now().strftime('%H:%M:%S')
save_name = lambda: datetime.now().strftime('%Y%m%d_%H_%M_%S')

home = abspath(expanduser('~\\Desktop')) if exists(
    abspath(expanduser('~\\Desktop'))) else abspath(expanduser('~'))

DEFAULT_SETTINGS = {
    'accounts': {
        'id': 'xxx',
        'key': 'xxx',
        'secret': 'xxx'
    },
    'recognition': {
        'delay': '2',
        'number': 'all',
        'type': '0'
    },
    'out': {
        'format': 'txt',
        'directory': home,
        'title': 'none'
    },
    'advanced': {
        'region': 'none',
        'text1': 'none',
        'clean': 'false'
    }
}


def dpi(w_r, h_r, w, h):
    global g_dpi, g_width, g_height
    if g_dpi == 0:
        g_width = w
        g_height = h
        g_dpi = sqrt(w**2 + h**2) / sqrt((w_r / 10 * 0.394)**2 +
                                         (h_r / 10 * 0.394)**2)
    return g_dpi


class Validpoints(QObject):
    points_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.__data = []

    @classmethod
    def fromList(points):
        point = Validpoints()
        point.appends(points)
        return point

    @property
    def data(self) -> list:
        res = []
        for v in self.__data:
            if v[:2] != v[2:]:
                res.append(v)
        return res

    def append(self, v: '[x0,y0,x1,y1]') -> bool:
        if v[:2] != v[2:]:
            self.__data.append(v)
            return True
        return False

    def appends(self, points:'List[List[int, int, int, int]]'):
        for point in points:
            self.append(point)

    def clear(self):
        self.__data.clear()

    def __iter__(self):
        for v in self.data:
            yield v

    def __getitem__(self, item):
        return self.__data[item]


class ImgLabel(QLabel):
    action1_signal = pyqtSignal(dict)
    action2_signal = pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        draw_pixmap = kwargs.pop('draw_pixmap', None)
        super().__init__(*args, **kwargs)
        self.__flag = None
        self.edited = True
        self.draw_pixmap = draw_pixmap
        self.points = Validpoints()
        self.metedata = {}
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

    def setEditPixmap(self, pixmap):
        self.draw_pixmap = pixmap
    
    def setEdited(self, flag):
        self.edited = flag

    def contextMenu(self, pos):
        menu = QMenu(self)
        a1 = menu.addAction('清除')
        a2 = menu.addAction('确认')
        action = menu.exec_(QCursor.pos())
        if action == a1:
            self.points.clear()
            self.action1_signal.emit(self.metedata)
            self.points.points_signal.emit([])
            self.update()
        elif action == a2:
            points = []
            for v in self.points.data:
                x1, y1, x2, y2 = v
                w, h = abs(x2 - x1), abs(y2 - y1)
                if (x2 - x1) > 0 and (y2 - y1) > 0:
                    points.append([x1, y1, x2, y2])  # 右下方滑动
                elif (x2 - x1) > 0 and (y2 - y1) < 0:
                    points.append([x1, y1 - h, x2, y2 + h])  # 右上方滑动
                elif (x2 - x1) < 0 and (y2 - y1) > 0:
                    points.append([x2, y2 - h, x1, y1 + h])  # 左下方滑动
                else:
                    points.append([x2, y2, x1, y1])  # 左上方滑动

            self.points.clear()
            self.points.appends(points)

            self.action2_signal.emit(self.metedata)
            self.points.points_signal.emit(points)

    def mousePressEvent(self, QMouseEvent):
        if self.draw_pixmap and self.edited:
            if QMouseEvent.button() == Qt.LeftButton:
                self.__flag = True
                self.points.append([QMouseEvent.x(), QMouseEvent.y(), 0, 0])
        else:
            super().mousePressEvent(QMouseEvent)

    def mouseReleaseEvent(self, QMouseEvent):
        if self.draw_pixmap and self.edited:
            if QMouseEvent.button() == Qt.LeftButton:
                self.__flag = False
        else:
            super().mouseReleaseEvent(QMouseEvent)

    def mouseMoveEvent(self, QMouseEvent):
        if self.draw_pixmap and self.edited:
            if self.__flag:
                self.points[-1][-2:] = [QMouseEvent.x(), QMouseEvent.y()]
                self.update()
        else:
            super().mouseMoveEvent(QMouseEvent)

    def paintEvent(self, QPaintEvent):
        if self.draw_pixmap and self.edited:
            self.setCursor(Qt.CrossCursor)
            painter = QPainter()
            painter.begin(self)
            self.drawPolicy(painter)
            painter.end()
        else:
            self.setCursor(Qt.ArrowCursor)
            super().paintEvent(QPaintEvent)

    def drawPolicy(self, painter):
        painter.drawPixmap(self.rect(), self.draw_pixmap)
        if self.points.data:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            for point in self.points:
                x1, y1, x2, y2 = point
                w, h = abs(x2 - x1), abs(y2 - y1)
                if (x2 - x1) > 0 and (y2 - y1) > 0:
                    painter.drawRect(x1, y1, w, h)  # 右下方滑动
                elif (x2 - x1) > 0 and (y2 - y1) < 0:
                    painter.drawRect(x1, y1 - h, w, h)  # 右上方滑动
                elif (x2 - x1) < 0 and (y2 - y1) > 0:
                    painter.drawRect(x1 - w, y1, w, h)  # 左下方滑动
                else:
                    painter.drawRect(x2, y1 - h, w, h)  # 左上方滑动


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
        self.root._post_image = ImageQt.fromqpixmap(self.post_image)
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.root = self.parent()

    def update_settings(self, import_default=False):
        if import_default:
            default_settings = deepcopy(DEFAULT_SETTINGS)
            default_settings.pop('accounts')
            self.run_info = default_settings
        else:
            self.run_info = deepcopy(self.root.run_info)

        if not import_default:
            self.login_lineEdit_id.setText(self.run_info['accounts']['id'])
            self.login_lineEdit_key.setText(self.run_info['accounts']['key'])
            self.login_lineEdit_secret.setText(
                self.run_info['accounts']['secret'])

        self.out_lineEdit_dir.setText(self.run_info['out']['directory'])
        if self.run_info['out']['format'] == 'txt':
            self.out_lineEdit_title.setEnabled(False)
            self.out_comboBox.setCurrentIndex(0)
        else:
            self.out_lineEdit_title.setEnabled(True)
            self.out_comboBox.setCurrentIndex(1)

        self.comboBox.setCurrentIndex(int(
            self.run_info['recognition']['type']))
        self.reg_timeEdit.setTime(
            QTime(0, 0, int(self.run_info['recognition']['delay'])))
        self.reg_comboBox.setEditText(
            '所有' if self.run_info['recognition']['number'] ==
            'all' else self.run_info['recognition']['number'])

        self.adv_lineEdit.setText(self.run_info['advanced']['region'])

    def set_resetSlot(self, value: int):
        self.update_settings(import_default=True)
        self.update()

    def set_applySlot(self):
        self.run_info.update({
            'accounts': {
                'id': self.login_lineEdit_id.text(),
                'key': self.login_lineEdit_key.text(),
                'secret': self.login_lineEdit_secret.text()
            },
            'recognition': {
                'delay':
                self.reg_timeEdit.text()[:-1],
                'number':
                'all' if self.reg_comboBox.currentText() == '所有' else
                self.reg_comboBox.currentText(),
                'type':
                str(self.comboBox.currentIndex())
            },
            'out': {
                'format':
                'txt' if self.out_comboBox.currentText().startswith('文本') else
                'xlsx',
                'directory':
                self.out_lineEdit_dir.text(),
                'title':
                'none'
            },
            'advanced': {
                'region': self.adv_lineEdit.text(),
                'text1': 'none',
                'clean': 'false'
            }
        })
        self.root.run_info.update(self.run_info)
        self.root.cfg.save(self.root.run_info)
        self.close()

    def out_buttonSlot(self):
        pass

    def out_fmtSlot(self, index: int):
        if index == 0:
            self.run_info['out']['format'] = 'txt'
            self.out_lineEdit_title.setEnabled(False)
        else:
            self.run_info['out']['format'] = 'xlsx'
            self.out_lineEdit_title.setEnabled(True)

    def reg_buttonSlot(self):
        pass

    def adv_buttonAddSlot(self):
        pass

    def adv_buttonHelpSlot(self):
        pass


class Worker(QObject):

    signal = pyqtSignal(str)

    def __init__(self, parent=None, root=None):
        super().__init__(parent)
        self.root = root

    def process_no_editwidget(self):
        pass

    def ocr(self):
        starts = self.root.lineEdit.text().strip('"').strip('\'').strip('')
        id = self.root.run_info['accounts']['id']
        key = self.root.run_info['accounts']['key']
        secret = self.root.run_info['accounts']['secret']
        number = self.root.run_info['recognition']['number']
        delay = int(self.root.run_info['recognition']['delay']) * 1000
        _region = self.root.run_info['advanced']['region']
        region = None if _region == 'none' else _region
        if isdir(starts):
            if number == 'all':
                image_paths = get_file_paths(starts,
                                             filter_files=lambda st: st[-3:] in
                                             ['png', 'jpg', 'peg', 'bmp'])
            else:
                image_paths = get_file_paths(starts,
                                             filter_files=lambda st: st[-3:] in
                                             ['png', 'jpg', 'peg', 'bmp'],
                                             num=int(number))
        else:
            image_paths = [starts]

        if self.root.run_info['recognition']['type'] == '0':
            service_type = BAIDU_GENERAL_TYPE
        elif self.root.run_info['recognition']['type'] == '1':
            service_type = BAIDU_ACCURATE_TYPE
        else:
            service_type = BAIDU_HANDWRITING_TYPE
        ocr_service = BaiduOcrService(id, key, secret, service_type, seq='\n')

        for path in image_paths:
            self.signal.emit(
                f'<p style="font-weight:bold;color:purple">[{info_time()}] {basename(path)}:</p>'
            )
            json = ocr_service.request(region=region,
                                       img=self.root._post_image)
            if 'words_result' in json.keys():
                res = []
                for dic in json.get('words_result'):
                    res.append(dic.get('words'))
                self.signal.emit('<p>%s</p>' % '\n'.join(res))
            else:
                self.signal.emit(str(json))
            self.thread().msleep(delay)
        self.thread().quit()


class RuntimeInfo(dict):
    pass


class Config(object):
    def __init__(self):
        self.cp = ConfigParser()
        self.file_path = abspath(join(expanduser('~'), 'ocr_app.cfg'))
        if not exists(self.file_path):
            self.cp.read_dict(DEFAULT_SETTINGS)
            with open(self.file_path, 'w') as file:
                self.cp.write(file)
        else:
            self.cp.read(self.file_path)

    def to_dict(self):
        dic = {}
        for key, section in self.cp.items():
            if key != 'DEFAULT':
                dic[key] = dict(section)
        return dic

    def reload(self):
        self.cp.clear()
        self.cp.read(self.file_path)

    def get(self, section: str, key: str):
        return self.cp.get(section, key)

    def set(self, section, key, v):
        self.cp.set(section, key, v)

    def save(self, dic):
        with open(self.file_path, 'w') as file:
            self.cp.clear()
            self.cp.read_dict(dic)
            self.cp.write(file)


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
        self.cfg = Config()
        self.desktop = QApplication.desktop()
        self.run_info = RuntimeInfo(self.cfg.to_dict())
        self.dialog = AdvancedDialog(self)
        self.ocr_thread = QThread()

        self.worker = Worker(root=self)
        self.worker.moveToThread(self.ocr_thread)
        self.worker.signal.connect(self.displayOcr)
        self.ocr_thread.started.connect(self.worker.ocr)

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
        if self.comboBox.currentIndex() == 0:
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

        if self.lineEdit.text():
            if self.comboBox.currentIndex() == 0:
                if self.lineEdit.text().strip('"').strip(
                        ' ')[-3:].lower() not in ['jpg', 'png', 'bmp', 'peg']:
                    QMessageBox.warning(self, '警告',
                                        '请添加jpg, png, bmp, jpeg格式的图片')
                else:
                    self.ocr_thread.start()
            else:
                if not isdir(self.lineEdit.text().strip('"').strip(' ')):
                    QMessageBox.warning(self, '警告', '请添加正确的目录')
                else:
                    self.ocr_thread.start()
        else:
            QMessageBox.warning(self, '提示', '选择图片或文件夹')

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
        self.dialog.update_settings()
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