from sys import argv, exit
from functools import reduce

from pandas import Series, DataFrame, merge, concat
from jinja2 import Template
from PyQt5.QtWidgets import QWidget, QApplication, QTextEdit, QMenu
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QCursor, QIntValidator
from analysisui import Ui_Form


class Analysis(QObject):

    data_signal = pyqtSignal(DataFrame)

    def __init__(self, parent=None, root=None):
        super().__init__(parent)
        self.root = root

    def collect_series(self) -> list:
        count = self.root.splitter.count()
        edits = self.root.splitter.children()[:count]
        ses = []
        for edit in edits:
            if edit.toPlainText().strip(' '):
                se = Series(
                    edit.toPlainText().strip(' ').strip('\n').split('\n'))
            else:
                se = Series()
            ses.append(se)
        ses.reverse()  ## children列表中顺序是反的,可能与qt版本有关注意
        return ses

    def juhe(self):
        ses = self.collect_series()
        df = concat(ses, ignore_index=True).to_frame('项')
        df = df.groupby(by='项', sort=False).size().to_frame('数量')
        df.index.name = '项'
        self.data_signal.emit(df)

    def quanji(self):
        def _(se1, se2):
            lst1 = se1.to_list()
            lst2 = se2.to_list()
            lst1.extend(lst2)
            target = list(set(se1.to_list()).union(set(se2.to_list())))
            target.sort(key=lst1.index)
            return Series(target)

        ses = self.collect_series()
        df = reduce(_, ses).to_frame('全集')
        df.index = range(1, len(df) + 1)
        df.index.name = '序号'
        self.data_signal.emit(df)

    def jiaoji(self):
        def reduced(se1, se2):
            se1.name = '交集'
            se2.name = 'merged'
            df = merge(se1, se2, left_on='交集', right_on='merged', how='inner')
            return df['交集']

        ses = self.collect_series()
        df = reduce(reduced, ses).to_frame('交集')
        df.index = range(1, 1 + len(df))
        df.index.name = '序号'
        self.data_signal.emit(df)

    def zuoji(self):
        se1, se2 = self.collect_series()[:2]
        lst1 = se1.to_list()
        lst2 = se2.to_list()
        lst1.extend(lst2)
        target = list(set(lst1) - set(lst2))
        target.sort(key=lst1.index)
        df = Series(target).to_frame('左集')
        df.index = range(1, 1 + len(df))
        df.index.name = '序号'
        self.data_signal.emit(df)

    def youji(self):
        se1, se2 = self.collect_series()[:2]
        lst1 = se1.to_list()
        lst2 = se2.to_list()
        lst2.extend(lst1)
        target = list(set(lst2) - set(lst1))
        target.sort(key=lst2.index)
        df = Series(target).to_frame('左集')
        df.index = range(1, 1 + len(df))
        df.index.name = '序号'
        self.data_signal.emit(df)

    def fenge(self):
        se = concat(self.collect_series(), ignore_index=True)
        df = se.str.split(pat=self.root.lineEdit.text(),
                          expand=True,
                          n=int(self.root.comboBox_2.currentText()))
        df.index = range(1, 1 + len(df))
        df.index.name = '序号'
        self.data_signal.emit(df)

    def tihuan(self):
        se = concat(self.collect_series(), ignore_index=True)
        se = se.str.replace(pat=self.root.lineEdit.text(),
                            repl=self.root.lineEdit_2.text(),
                            n=int(self.root.comboBox_2.currentText()),
                            case=True,
                            regex=True)
        df = se.to_frame('项')
        df.index = range(1, 1 + len(df))
        df.index.name = '序号'
        self.data_signal.emit(df)

    def tiqu(self):
        se = concat(self.collect_series(), ignore_index=True)
        df = se.str.extract(pat=self.root.lineEdit.text(), expand=True)
        df = df.fillna('NaN')
        df.columns = range(1, len(df.columns) + 1)
        df.index = range(1, 1 + len(df))
        df.index.name = '序号'
        self.data_signal.emit(df)

    def analysis(self):
        if self.root.comboBox.currentIndex() == 0:
            self.juhe()
        elif self.root.comboBox.currentIndex() == 1:
            self.quanji()
        elif self.root.comboBox.currentIndex() == 2:
            self.jiaoji()
        elif self.root.comboBox.currentIndex() == 3:
            self.zuoji()
        elif self.root.comboBox.currentIndex() == 4:
            self.youji()
        elif self.root.comboBox.currentIndex() == 5:
            self.fenge()
        elif self.root.comboBox.currentIndex() == 6:
            self.tihuan()
        elif self.root.comboBox.currentIndex() == 7:
            self.tiqu()
        self.thread().quit()


class AnalysisWidget(QWidget, Ui_Form):

    backsig = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.init()

    def init(self):
        self.display_df = None
        self.edits = []
        self.ana_thread = QThread()
        self.worker = Analysis(root=self)
        self.worker.moveToThread(self.ana_thread)
        self.ana_thread.started.connect(self.worker.analysis)
        self.worker.data_signal.connect(self.disPlayDf)
        self.worker.data_signal.connect(self.updateData)
        self.comboBox.currentIndexChanged.connect(self._)
        self.customTextBrowserContextMenu()

        self.lineEdit.hide()
        self.lineEdit_2.hide()
        self.label_2.hide()
        self.comboBox_2.hide()

        line_edit = self.comboBox_2.lineEdit()
        line_edit.setValidator(QIntValidator(-1, 10000))
        self.comboBox_2.setLineEdit(line_edit)
        self.pushButton.setToolTip('<b>帮助如下所示</b>')

    def updateData(self, df):
        self.display_df = df

    def customTextBrowserContextMenu(self):
        self.textBrowser.setContextMenuPolicy(Qt.CustomContextMenu)
        self.textBrowser.customContextMenuRequested.connect(self.contextMenu)

    def contextMenu(self):
        menu = QMenu(self.textBrowser)
        a1 = menu.addAction('清空')
        a2 = menu.addAction('复制表格')
        a4 = menu.addAction('导出txt')
        a5 = menu.addAction('导出excel')
        action = menu.exec_(QCursor.pos())
        if action == a1:
            self.textBrowser.clear()
        elif action == a2:
            self.display_df.to_clipboard()
        elif action == a4:
            pass
        else:
            pass

    def _(self, index):
        if index in [3, 4]:  # [3, 4, 5, 6, 7]
            self.pushButton_3.setEnabled(False)
            self.pushButton_6.setEnabled(False)
            for edit in self.edits:
                edit.hide()
        else:
            self.pushButton_3.setEnabled(True)
            self.pushButton_6.setEnabled(True)
            for edit in self.edits:
                edit.show()

        if index in [5, 6, 7]:
            self.lineEdit.show()
            if index == 5:
                self.label_2.hide()
                self.comboBox_2.show()
            elif index == 6:
                self.label_2.show()
                self.lineEdit_2.show()
                self.comboBox_2.show()
            else:
                self.label_2.hide()
                self.lineEdit_2.hide()
                self.comboBox_2.hide()
        else:
            self.lineEdit.hide()
            self.lineEdit_2.hide()
            self.comboBox_2.hide()
            self.label_2.hide()

    def backSlot(self):
        self.backsig.emit()

    def helpSlot(self):
        # print(111)
        pass

    def resetSlot(self):
        for edit in self.edits:
            edit.deleteLater()
        self.edits.clear()
        self.textEdit.clear()
        self.textEdit_2.clear()
        self.lineEdit.clear()
        self.lineEdit_2.clear()
        self.textBrowser.clear()
        self.splitter.setSizes([50, 50])

    def addSlot(self):
        edit = QTextEdit(self.splitter)
        self.edits.append(edit)
        # self.splitter.addWidget(edit)

    def subSlot(self):
        try:
            edit = self.edits.pop()
            edit.deleteLater()
        except IndexError:
            ...

    def startSlot(self):
        self.ana_thread.start()

    def disPlayDf(self, df):
        index = self.comboBox.currentIndex()
        template = Template('''<table cellpadding="8" border="1" >
            <tr>
                <th>序号</th>
                {% for col in columns %}<th>{{ col }}</th>{% endfor %}
            </tr>
            {% for tu in data %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        {% for value in tu %}<td>{{ value }}</td>{% endfor %}
                    </tr>
            {% endfor %}
            </table>''')
        if index == 0:
            ses = [Series(df.index), df['数量']]
            self.textBrowser.setHtml(
                template.render(columns=['项', '数量'], data=zip(*ses)))
        else:
            ses = [df[col] for col in df.columns.tolist()]
            self.textBrowser.setHtml(
                template.render(columns=df.columns.tolist(), data=zip(*ses)))


def main():
    app = QApplication(argv)
    win = AnalysisWidget()
    win.show()
    exit(app.exec_())


if __name__ == "__main__":
    main()