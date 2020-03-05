import sys
from math import sqrt
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView

g_dpi = 0
g_width = 0
g_height = 0

def dpi(w_r, h_r, w, h):
    global g_dpi, g_width, g_height
    if g_dpi == 0:
        g_width = w
        g_height = h
        g_dpi = sqrt(w**2 + h**2) / sqrt((w_r / 10 * 0.394)**2 +
                                         (h_r / 10 * 0.394)**2)
    return g_dpi


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
            (g_dpi / 96))  # CurrentFontSize *（DevelopmentDPI / CurrentFontDPI）
        app.setFont(font)
        self.close()


################################################
#######创建主窗口
################################################
class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('My Browser')
        # self.showMaximized()
        file = "file:///C:/githubs/ocr/sources/pdfjs-2.2.228-dist/web/viewer.html"
        self.resize(900, 500)
        self.webview = WebEngineView()

        self.webview.load(QUrl(file))
        self.setCentralWidget(self.webview)
        # 'https://www.baidu.com'


################################################
#######创建浏览器
################################################
class WebEngineView(QWebEngineView):
    windowList = []

    # 重写createwindow()
    def createWindow(self, QWebEnginePage_WebWindowType):
        new_webview = WebEngineView()
        new_window = MainWindow()
        new_window.setCentralWidget(new_webview)
        #new_window.show()
        self.windowList.append(new_window)  #注：没有这句会崩溃！！！
        return new_webview


def main():
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication([])
    # InitDpi(app=app)
    myWin = MainWindow()
    myWin.show()
    exit(app.exec_())

if __name__ == "__main__":
    main()
