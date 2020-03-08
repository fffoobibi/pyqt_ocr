import sys, time
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class Test(QObject):
    sig = pyqtSignal()
    sig2 = pyqtSignal()

    def test(self):
        print('slot:', QThread.currentThread())
        # self.thread().quit()
        
    def emitfunc(self):
        self.sig.emit()
        
    
    def testNO(self):
        print('noslot:', QThread.currentThread())
        self.thread().quit()


app = QApplication(sys.argv)
print('main1:', QThread.currentThread())
ob = Test()
t = QThread()
print('main2:', QThread.currentThread())
ob.moveToThread(t)
print('main3:', QThread.currentThread())

t.started.connect(ob.emitfunc)
ob.sig.connect(ob.test)
ob.sig2.connect(ob.testNO)

t.start()
print('afterastart', QThread.currentThread())
time.sleep(2)
print(t.isFinished())
print('mainend:', QThread.currentThread())
# ob.testNO()
ob.sig.emit()
ob.sig2.emit()
app.exec_()



