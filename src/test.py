from pdf import Engine, PdfHandle
from PyQt5.QtWidgets import *


class widget(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(500, 500)
        handle = PdfHandle()
        handle.setEngine(r'C:\githubs\ocr\test.pdf')
        print(handle.screenSize)
        print(handle.pageSize)
        print(handle.previewSize)
        print(handle.displayZoom)
try:       
    app = QApplication([])
    wid = widget()
    wid.show()
    app.exec_()

except Exception as e:
    print(e)
