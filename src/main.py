import sys
import srcs

from functools import wraps
from math import sqrt

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from mainnew import Ui_MainWindow
from pdfnew import PdfWidget
from analysis import AnalysisWidget
from customwidgets import AdvancedDialog
from supports import *

G_DPI = 0
G_WIDTH = 0
G_HEIGHT = 0


def dpi(w_r, h_r, w, h):
    global G_DPI, G_WIDTH, G_HEIGHT
    if G_DPI == 0:
        G_WIDTH = w
        G_HEIGHT = h
        G_DPI = sqrt(w**2 + h**2) / sqrt((w_r / 10 * 0.394)**2 +
                                         (h_r / 10 * 0.394)**2)
    return G_DPI


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
            (G_DPI / 96))  # CurrentFontSize *（DevelopmentDPI / CurrentFontDPI）
        app.setFont(font)
        self.close()


class MainWidget(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.init()
        self.setActions()
        self.setStyles()

    def init(self):
        self.account = Account()
        print(1)
        self.dialog = AdvancedDialog(self, account=self.account)
        print(2)
        self.ocrWidget.account = self.account
        print(3)
        self.ocrWidget.pushButton_5.clicked.connect(
            lambda: self.stackedWidget.setCurrentIndex(1))
        self.analysisWidget.pushButton_5.clicked.connect(
            lambda: self.stackedWidget.setCurrentIndex(0))
        print(4)

    def setActions(self):
        self.action_advanced.triggered.connect(self.dialogSlot)
        self.dialog.radio_signal.connect(self.updateRadio)
        print(5)

    def setStyles(self):
        self.setWindowIcon(QIcon(':/image/img/app.ico'))
        self.setWindowTitle('文字识别')
        print(6)
        flag = self.account.active_user().config.get('recognition', 'type', int)
        print(7, flag)
        if flag == 0:
            self.ocrWidget.radioButton.setChecked(True)
        elif flag == 1:
            self.ocrWidget.radioButton_2.setChecked(True)
            print('dddd')
        else:
            self.ocrWidget.radioButton_3.setChecked(True)
        print(8)
        self.ocrWidget.checkBox.setChecked(True)

        with open('./sources/flatwhite.css') as file:
            self.setStyleSheet(file.read())
        tmp_h = 500 / 768
        tmp_w = 900 / 1366
        self.resize(int(G_WIDTH * tmp_w), int(G_HEIGHT * tmp_h))  # w, h

    @slot(desc='action_adv triggerd')
    def dialogSlot(self, flag):
        user = self.account.active_user()
        self.dialog.account = self.account
        self.dialog.update_account(from_user=user)
        self.dialog.update_config(from_config=user.config)
        self.dialog.exec_()

    @slot(signal='radio_signal')
    def updateRadio(self, flag):
        if flag == 0:
            self.ocrWidget.radioButton.setChecked(True)
        elif flag == 1:
            self.ocrWidget.radioButton_2.setChecked(True)
        else:
            self.ocrWidget.radioButton_3.setChecked(True)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.ocrWidget.pdf_thread.quit()
        self.ocrWidget.ocr_thread.quit()
        self.account.flush()


def main():
    app = QApplication(sys.argv)
    init = InitDpi(app=app)
    win = MainWidget()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()