import sys

from functools import wraps
from math import sqrt

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from mainnew import Ui_MainWindow
from advancedui import Ui_Dialog
from pdfnew import PdfWidget
from analysis import AnalysisWidget
from supports import *
from srcs import *

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


class AdvancedDialog(QDialog, Ui_Dialog):

    radio_signal = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account', None)
        super().__init__(*args, **kwargs)
        self.setWindowIcon(QIcon(':/image/img/cogs.svg'))
        self.setupUi(self)
        self.account: Account = account

        self.comboBox_2.currentIndexChanged.connect(self.switch_user)
        self.comboBox_2.currentTextChanged.connect(self.switch_user_policy)

    @slot(signal='currentTextChanged', sender='comboBox_2')
    def switch_user_policy(self, text):
        texts = [
            self.comboBox_2.itemText(index)
            for index in range(self.comboBox_2.count())
        ]
        if text not in texts:
            self.login_lineEdit_id.setText('')
            self.login_lineEdit_key.setText('')
            self.login_lineEdit_secret.setText('')
        else:
            user = self.account.info[text]
            self.login_lineEdit_id.setText(user['id'])
            self.login_lineEdit_key.setText(user['key'])
            self.login_lineEdit_secret.setText(user['secret'])

    @slot(signal='currentIndexChanged', sender='comboBox_2')
    def switch_user(self, index):
        if not self.auto:
            alias = self.comboBox_2.currentText()
            active_user = self.account.get_user(alias)
            self.account.set_active_user(alias)
            self.login_lineEdit_id.setText(active_user.id)
            self.login_lineEdit_key.setText(active_user.key)
            self.login_lineEdit_secret.setText(active_user.secret)
            self.update_config(active_user.config)
            self.auto = False

    def update_account(self, from_user: User):
        self.auto = True
        alias = self.account.active_alias()
        self.comboBox_2.clear()
        self.comboBox_2.addItems(self.account.alias())
        self.comboBox_2.setCurrentText(alias)
        self.auto = False

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

    @slot(signal='clicked', sender='reset_button')
    def set_resetSlot(self, value: int):
        self.update_config(DEFAULT_CONFIG)
        self.update()

    @slot(signal='clicked', sender='ok_button')
    def set_applySlot(self, clicked):
        user = self.account.active_user()
        user.id = self.login_lineEdit_id.text()
        user.key = self.login_lineEdit_key.text()
        user.secret = self.login_lineEdit_secret.text()
        user.alias = self.comboBox_2.lineEdit().text()
        user.config.update_from_dict({
            'recognition': {
                'delay': self.reg_timeEdit.text()[:-1],
                'number': int(self.reg_timeEdit.text()[:-1]),
                'type': self.comboBox.currentIndex()
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
        self.account.set_active_user(user.alias)
        user.sync(self.account)
        # self.account.flush()
        self.radio_signal.emit(user.config.get('recognition', 'type', int))
        self.close()

    def out_buttonSlot(self):
        pass

    def out_fmtSlot(self, index: int):
        user = self.account.active_user()
        if index == 0:
            if user.config.get('out', 'format') == 'txt':
                self.out_lineEdit_title.setEnabled(False)
        else:
            if user.config.get('out', 'format') == 'xlsx':
                self.out_lineEdit_title.setEnabled(True)

    def reg_buttonSlot(self):
        pass

    def adv_buttonAddSlot(self):
        pass

    def adv_buttonHelpSlot(self):
        pass


class MainWidget(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.init()
        self.setActions()
        self.setStyles()

    def init(self):
        self.account = Account()
        self.dialog = AdvancedDialog(self, account=self.account)
        self.ocrWidget.account = self.account
        self.ocrWidget.pushButton_5.clicked.connect(
            lambda: self.stackedWidget.setCurrentIndex(1))
        self.analysisWidget.pushButton_5.clicked.connect(
            lambda: self.stackedWidget.setCurrentIndex(0))

    def setActions(self):
        self.action_advanced.triggered.connect(self.dialogSlot)
        self.dialog.radio_signal.connect(self.update_radio)

    def setStyles(self):
        self.setWindowIcon(QIcon(':/image/img/app.ico'))
        self.setWindowTitle('文字识别')
        flag = self.account.active_user().config.get('recognition', 'type', int)
        if flag == 0:
            self.ocrWidget.radioButton.setChecked(True)
        elif flag == 1:
            self.ocrWidget.radioButton_2.setChecked(True)
        else:
            self.ocrWidget.radioButton_3.setChecked(True)
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
    def update_radio(self, flag):
        if flag == 0:
            self.ocrWidget.radioButton.setChecked(True)
        elif flag == 1:
            self.ocrWidget.radioButton_2.setChecked(True)
        else:
            self.ocrWidget.radioButton_3.setChecked(True)


def main():
    app = QApplication(sys.argv)
    init = InitDpi(app=app)
    win = MainWidget()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()