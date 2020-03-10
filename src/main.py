import sys

from functools import wraps

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from mainnew import Ui_MainWindow
from advancedui import Ui_Dialog
from pdfnew import PdfWidget
from other import AnalysisWidget
from supports import *

def slot(signal: str = '', desc='', sender='', target=''):
    def outer(func):
        @wraps(func)
        def inner(self, *args, **kwargs):
            res = func(*args, **kwargs)
            return res
        return inner
    return outer

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


class MainWidget(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.init()
        self.setActions()
        self.setStyles()

    def init(self):
        self.account = Account()
        self.user = self.account.active_user()
        self.dialog = AdvancedDialog(self, user=self.account.active_user())
        # self.ocr_thread = QThread()
        # self.pdf_thread = QThread()

        self.page.pushButton_5.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(1))
        self.page_2.pushButton_5.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(0))

    def setActions(self):
        self.action_advanced.triggered.connect(self.dialogSlot)

    def setStyles(self):
        with open('./sources/flatwhite.css') as file:
            self.setStyleSheet(file.read())

    def closeEvent(self, event):
        super().closeEvent(event)
        self.page.pdf_thread.quit()


    @slot(desc='action_adv triggerd')
    def dialogSlot(self):
        user = self.account.active_user()
        config = user.config
        self.dialog.update_account(from_user=user)
        self.dialog.update_config(from_config=config)
        self.dialog.exec_()


    
        
def main():
    app = QApplication(sys.argv)
    win = MainWidget()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()