import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class Widget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(500, 1000)
        self.button = QPushButton('动画', self)
        self.text = QTextBrowser(self)
        self.text.resize(250, 500)
        self.text.append('111111')
        self.text.move(-20, 100)
        self.button.clicked.connect(self.shoot)

    def shoot(self):
        self.anim = QPropertyAnimation(self.text, b'geometry') # 设置动画的对象及其属性
        self.anim.setDuration(100) # 设置动画间隔时间
        self.anim.setStartValue(self.text.geometry()) # 设置动画对象的起始属性
        self.anim.setEndValue(QRect(0, 100, 0, 500)) # 设置动画对象的结束属性
        self.anim.start() # 启动动画
        

def main():
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()