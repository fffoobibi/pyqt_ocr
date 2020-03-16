import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from typing import *


class ListModel(QAbstractListModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_list: List[QPixmap] = []
    
    def rowCount(self, index):
        return len(self.data_list)

    def data(self, index: QModelIndex, role):
        if index.isValid() and (0 <= index.row() < len(self.data_list)):
            if role == Qt.DisplayRole or role == Qt.EditRole:
                return self.data_list[index.row()]
            elif role == Qt.BackgroundColorRole:
                return QVariant(QColor(Qt.gray))
            elif role == Qt.TextAlignmentRole:
                return QVariant(Qt.AlignCenter)
            elif role == Qt.SizeHintRole:
                return QVariant(QSize(200, 100))
            elif role == Qt.TextColorRole:
                return QColor(Qt.black)
            elif role == Qt.FontRole:
                font = QFont()
                font.setBold(True)
                return font
        else:
            return QVariant()

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def setData(self, index, value, role):
        if value != None:
            self.data_list[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def addData(self, datas):
        self.data_list.extend(datas)

    def getItem(self, index):
        return self.data_list[index]

class ListWidget(QListView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMovement(QListView.Free)
        self.model = ListModel()
        self.model.addData(list('12345678'))
        self.delegate = ItemDelegate()
        self.setModel(self.model)
        # # self.setItemDelegateForRow(0, self.delegate)
        # self.setItemDelegate(self.delegate)
        self.setSpacing(5)
        self.setEnabled(True)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.clicked.connect(self.dis)

    
    def dis(self, index):
        print(index.row(), self.model.getItem(index.row()))


class ItemDelegate(QItemDelegate):

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        rect = option.rect
        option.displayAlignment = Qt.AlignCenter
        self.drawDisplay(painter, option, option.rect, index.data())
        if option.state & QStyle.State_Selected:
            rect.adjust(2,2,-2,-2)
            painter.drawRoundedRect(rect, 4, 4)
        elif option.state & QStyle.State_On:
            painter.fillRect(rect, Qt.black)
        else:
            super().paint(painter, option, index)
        
     
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(100)
        return size

    def createEditor(self, parent, option, index):       
        wdgt = QLineEdit(parent)        
        return wdgt    

    def setEditorData(self, editor, index):        
        value = index.model().data(index, Qt.EditRole)
        editor.setText(str(value))
        editor.show()

    def setModelData(self, editor, model, index):        
        model.setData(index, editor.text(), Qt.DisplayRole)


class Widget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delegate = ItemDelegate()
        self.listwidget = ListWidget(self)
        self.listwidget.setFixedHeight(700)
        self.listwidget.setItemDelegate(self.delegate)
        self.resize(300, 800)

        

def main():
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()