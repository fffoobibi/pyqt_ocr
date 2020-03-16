import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
class SideButton(QPushButton):
    
    def __init__(self, *args, **kwargs):
        attach = kwargs.pop('attach', None)
        super().__init__(*args, **kwargs)
        self.attach_object = attach or None
        self.setCheckable(True)
        self.toggled.connect(self.toggle_sig)
    
    def hidePolicy(self, me=False, attach_object=False):
        self.setHidden(me)
        if self.attach_object:
            self.attach_object.setHidden(attach_object)

    def iconPolicy(self, checked_icon: QPixmap, unchecked_icon: QPixmap):
        pass

    def toggle_sig(self, flag):
        print('toggle:', flag)

class Widget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button = SideButton(self)
        self.resize(500,500)
        

def main():
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()