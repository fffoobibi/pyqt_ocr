from PyQt5.QtWidgets import (QWidget, QListWidget, QListWidgetItem,
                             QApplication, QListView, QAction, QMenu, QLabel,
                             QLineEdit)
from PyQt5.QtCore import QEvent, Qt, QObject, QMimeData, QPoint
from PyQt5.QtGui import QCursor, QDrag, QPixmap, QPainter


class Demo(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(400, 800)
        self.listwidget = QListWidget(self)
        self.listwidget.setGeometry(0, 0, 400, 400)
        self.listwidget.addItems(map(range(15, str)))
        # self.listwidget.setMovement(QListView.Free)Q

        self.menu = QMenu()
        self.menu.addAction('test1')
        self.menu.addAction('test2')
        self.menu_2 = QMenu()
        action = self.menu_2.addAction('clear')
        action.triggered.connect(lambda: self.listwidget.clear())
        self.listwidget.installEventFilter(self)

    def eventFilter(self, object, event):
        if object == self.listwidget:
            if event.type() == QEvent.ContextMenu:
                item = self.listwidget.itemAt(event.pos())
                if item:
                    self.menu.exec_(QCursor.pos())
                else:
                    self.menu_2.exec_(QCursor.pos())
        return QWidget.eventFilter(self, object, event)


class DragListWidget(QListWidget):

    moved_item = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.moved_item = self.itemAt(event.pos())


    def mouseMoveEvent(self, event):
        if event.buttons() and Qt.LeftButton:
            if self.moved_item:
                label = QLabel()
                label.setText(self.moved_item.text())
                label.setFixedSize(self.width(), 50)
                drag = QDrag(self)
                data = QMimeData()
                data.setText(self.moved_item.text())
                
                pixmap = label.grab()
                drag.setPixmap(pixmap)
                drag.setMimeData(data)
                drag.setHotSpot(QPoint(25, 25))
                action = drag.exec_(Qt.CopyAction | Qt.MoveAction,
                                    Qt.MoveAction)
                if action == Qt.MoveAction:
                    # print('copy', action == Qt.CopyAction, 'move', action == Qt.MoveAction)
                    self.takeItem(self.row(self.moved_item))
        

    def dragEnterEvent(self, event):
        event.setDropAction(Qt.MoveAction)
        if event.mimeData().text() == '1':
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.setDropAction(Qt.MoveAction)
        event.accept()

    def dropEvent(self, event):
        item = self.itemAt(event.pos())
        current_index = self.row(item)
        moved_index = self.row(self.moved_item)
        if not item:
            self.addItem(self.moved_item)
            event.setDropAction(Qt.CopyAction)
        else:
            if moved_index < current_index:
                self.insertItem(current_index + 1, event.mimeData().text())
            else:
                self.insertItem(current_index, event.mimeData().text())
            event.setDropAction(Qt.MoveAction)
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    win = Demo()
    win.show()
    app.exec_()
