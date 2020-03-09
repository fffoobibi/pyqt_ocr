import datetime
from os.path import basename
from functools import wraps
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtGui import QPixmap
from customwidgets import Engine
from supports import Account, User, Config
from ruia_ocr import BaiduOcrService, BAIDU_ACCURATE_TYPE, BAIDU_HANDWRITING_TYPE, BAIDU_GENERAL_TYPE

info_time = lambda: datetime.now().strftime('%H:%M:%S')
save_name = lambda: datetime.now().strftime('%Y%m%d_%H_%M_%S')

__all__ = ['PdfHandle', 'OcrHandle', 'ResultHandle']


class PdfHandle(QObject):

    open_signal = pyqtSignal()
    display_signal = pyqtSignal()
    reload_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    ocr_signal = pyqtSignal(list, list)

    @staticmethod
    def slot(signal: str = '', desc=''):
        def outer(func):
            @wraps(func)
            def inner(self, *args, **kwargs):
                res = func(self, *args, **kwargs)
                return res

            return inner

        return outer

    def __init__(self):
        super().__init__()
        self.__previewZoom = None
        self.__previewSize = None
        self.__displayZoom = None
        self.__displaySize = None
        self.__pageSize = None
        self.__screenSize = None
        self.__engine = None
        self.__reload = False

        self.engined_counts = 0
        self.is_editing = False
        self.pixmaps = []
        self.pixmaps_points = []
        self.preview_pixmaps_points = []
        self.edited_pdfs = []

    def clear(self):
        if not self.__reload:
            self.__previewZoom = None
            self.__displayZoom = None
            self.__previewSize = None
            self.__pageSize = None
            self.__screenSize = None
            self.is_editing = False
        self.pixmaps.clear()
        self.pixmaps_points.clear()
        self.edited_pdfs.clear()
        self.clear_signal.emit()

    def setEngine(self, path):
        self.__engine = Engine(path)

    @property
    def screenSize(self) -> tuple:
        if self.__screenSize is None:
            desktop = QApplication.desktop()
            self.__screenSize = desktop.width(), desktop.height()
        return self.__screenSize

    @property
    def pageSize(self) -> tuple:
        if self.__pageSize is None:
            pix = self.__engine.getPixmap(index=0, zoom=(1, 1))
            self.__pageSize = pix.width(), pix.height()
        return self.__pageSize

    @property
    def previewSize(self) -> tuple:
        if self.__previewSize is None:
            p_width, p_height = self.pageSize
            d_width, d_height = self.screenSize
            zoom_width = d_width / 12
            zoom_height = p_height / p_width * zoom_width
            self.__previewSize = round(zoom_width, 0), round(zoom_height, 0)
        return self.__previewSize

    @property
    def previewZoom(self) -> tuple:
        if self.__previewZoom is None:
            p_width, p_height = self.pageSize
            width, height = self.previewSize
            self.__previewZoom = width / p_width, width / p_width
        return self.__previewZoom

    @property
    def displayZoom(self) -> tuple:
        if self.__displayZoom is None:
            p_width, p_height = self.pageSize
            d_width, d_height = self.screenSize
            if (p_width, p_height) > (d_width, d_height):
                scaled_x = max(p_width / d_width, p_height / d_height) - 0.1
                self.__displayZoom = scaled_x, scaled_x
            else:
                self.__displayZoom = d_height * 0.8 / p_height, d_height * 0.8 / p_height

        return self.__displayZoom

    @displayZoom.setter
    def displayZoom(self, zoom: tuple):
        self.__displayZoom = zoom

    @property
    def displaySize(self):
        if self.__displaySize is None:
            display_zoom = self.displayZoom[0]
            p_width, p_height = self.pageSize
            width, height = round(p_width * display_zoom,
                                  0), round(p_height * display_zoom, 0)
            self.__displaySize = width, height
        return self.__displaySize

    def pageCount(self):
        return self.__engine.pageCount()

    def renderPixmap(self, index, zoom=(1, 1)) -> QPixmap:
        pixmap = self.__engine.getPixmap(index, zoom)
        return pixmap

    def rendering(self):
        self.is_editing = True
        render_indexes = []
        for index in range(self.pageCount()):
            render_indexes.append(index)

        self.pixmaps = render_indexes
        self.pixmaps_points = [[[]] for points in range(len(self.pixmaps))]

    def open(self, path, parent_widget):
        self.engined_counts += 1
        self.edited_pdfs.append(path)

        try:
            if self.engined_counts == 1:
                flag = False
            else:
                flag = self.__engine.target == self.edited_pdfs[-1]
        except IndexError:
            flag = False
        finally:
            if flag:
                self.reload_signal.emit()  # 阻塞
                if parent_widget.reloaded == QMessageBox.Yes:
                    self.__reload = True
                    self.clear()
                    self.setEngine(path)
                    self.rendering()
                    self.display_signal.emit()
                    self.__reload = False
                    parent_widget.reloaded = -1
                elif parent_widget.reloaded == QMessageBox.No:
                    parent_widget.reloaded = -1
            else:
                self.clear()
                self.setEngine(path)
                self.rendering()
                self.display_signal.emit()

    def init(self):
        pass


class ResultsHandle():
    def __init__(self, platform='b'):
        self.platform = platform

    def process(self, results: dict):
        if 'words_result' in results.keys():
            res = []
            for dic in results.get('words_result'):
                res.append(dic.get('words'))
            return results, True
        else:
            return results, False


class OcrHandle(QObject):

    ocr_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.use_pdf_handle = False
        self.result_handle = ResultsHandle()

    def ocr(self, user: User):
        platform = user.platform
        if platform == 'b':
            self.baidu(user)
        else:
            pass

    def baidu(self, user: User):
        config: Config = user.config
        if user.legal:
            workpath = config.get('parseinfo', 'workpath')
            service = config.get('recognition', 'type')
            number = config.get('recognition', 'number')
            delay = int(config.get('recognition', 'delay')) * 1000

            _region = config.get('advanced', 'region')
            region = None if _region == 'none' else _region
            if not self.use_pdf_handle:
                if service == '0':
                    service_type = BAIDU_GENERAL_TYPE
                elif service == '1':
                    service_type = BAIDU_ACCURATE_TYPE
                else:
                    service_type = BAIDU_HANDWRITING_TYPE
                ocr_service = BaiduOcrService(user.id,
                                              user.key,
                                              user.secret,
                                              service_type,
                                              seq='\n')

                self.signal.emit(
                    f'<p style="font-weight:bold;color:purple">[{info_time()}] {basename(workpath)}:</p>'
                )

                json = ocr_service.request(region=region, image_path=workpath)
                res, flag = self.result_handle.process(json)
                if flag:
                    self.signal.emit('<p>%s</p>' % '\n'.join(res))
                else:
                    self.signal.emit(str(json))
                self.thread().msleep(delay)
            else:
                for index in self.use_pdf_handle.pixmaps:
                    pass