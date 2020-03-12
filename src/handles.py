import datetime

from functools import wraps
from datetime import datetime
from typing import List, NoReturn

from PIL import Image, ImageQt
from fitz import Matrix
from fitz import open as pdf_open
from os.path import isfile, exists, isdir, abspath, join, basename

from PyQt5.QtCore import QObject, pyqtSignal, Qt, QThread
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtGui import QPixmap, QImage

from supports import *
from ruia_ocr import BaiduOcrService, BAIDU_ACCURATE_TYPE, BAIDU_HANDWRITING_TYPE, BAIDU_GENERAL_TYPE

info_time = lambda: datetime.now().strftime('%H:%M:%S')
save_name = lambda: datetime.now().strftime('%Y%m%d_%H_%M_%S')

__all__ = ['PdfHandle', 'OcrHandle', 'ResultHandle']

class BaseHandle(QObject):
    @staticmethod
    def slot(signal: str = '', desc='', sender=''):
        def outer(func):
            @wraps(func)
            def inner(self, *args, **kwargs):
                res = func(self, *args, **kwargs)
                return res
            return inner
        return outer

class Engine(object):
    def __init__(self, path):
        if isfile(path) and (path[-3:].lower() == 'pdf'):
            self.render = pdf_open(path)
            self.isPdf = True
            self.isDir = False
            self.isFile = False
            self.render_type='pdf'
        elif exists(path) and isdir(path):
            self.render = path
            self.isPdf = False
            self.isDir = True
            self.isFile = False
            self.render_type='dir'
        elif isfile(path) and (path[-4:].lower() in [
                '.png', '.bmp', '.jpg', 'jpeg'
        ]):
            self.isFile = True
            self.isPdf = False
            self.isDir = False
            self.render_type='file'

        self.__pagesView = None
        self.target = path

    def pagesView(self) -> list:
        if self.__pagesView is None:
            if self.isPdf:
                self.__pagesView = [
                    'Page_%s' % page
                    for page in range(1, self.render.pageCount + 1)
                ]
            elif self.isDir:
                self.__pagesView = [
                    abspath(join(self.target, file))
                    for file in listdir(self.target)
                ]
            else:
                self.__pagesView = [self.target]
        return self.__pagesView

    def pageCount(self):
        if self.isPdf:
            return self.render.pageCount
        return len(self.pagesView())

    def getPixmap(self, index, zoom=(1.0, 1.0)) -> QPixmap:
        if self.isPdf:
            x, y = zoom
            pdf_pixmap = self.render[index].getPixmap(Matrix(x, y))
            fmt = QImage.Format_RGBA8888 if pdf_pixmap.alpha else QImage.Format_RGB888
            pixmap = QPixmap.fromImage(
                QImage(pdf_pixmap.samples, pdf_pixmap.width, pdf_pixmap.height,
                       pdf_pixmap.stride, fmt))
            return pixmap
        else:
            return QPixmap(self.pagesView()[index])

    def __getitem__(self, index) -> QPixmap:
        return self.getPixmap(index)

    def __repr__(self):
        return f'Engine<{self.target}>'


class PdfHandle(BaseHandle):

    open_signal = pyqtSignal()
    display_signal = pyqtSignal()
    reload_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    ocr_signal = pyqtSignal(list, list)

    def __init__(self):
        super().__init__()
        self.__screenSize = None
        self.__engine = None

        self.reload = QMessageBox.No
        self.engined_counts = 0
        self.is_editing = False
        self.available_screen = True

        self.pixmaps = []
        self.pixmaps_points = []
        self.edited_pdfs = []

        self.__pdf_preview = None
        self.__pdf_previewZoom = None
        self.__pdf_displaySize = None
        self.__pdf_displayZoom = None

        self.__previewZooms: list = None
        self.__displayZooms: list = None
        self.__pageSizes: list = None

    def clear(self):
        self.__previewZooms: list = None
        self.__displayZooms: list = None
        self.__pageSizes: list = None

        self.__screenSize = None
        self.is_editing = False

        self.__pdf_previewSize = None
        self.__pdf_previewZoom = None
        self.__pdf_displaySize = None
        self.__pdf_displayZoom = None

        self.pixmaps.clear()
        self.pixmaps_points.clear()
        self.edited_pdfs.clear()
        self.clear_signal.emit()

    def setEngine(self, path):
        self.__engine = Engine(path)

    def getEngine(self) -> Engine:
        return self.__engine

    @property
    def screenSize(self) -> Size:
        if self.__screenSize is None:
            desktop = QApplication.desktop()
            if self.available_screen:
                rect = desktop.availableGeometry()
                self.__screenSize = rect.width(), rect.height()
            else:
                self.__screenSize = desktop.width(), desktop.height()  
        return self.__screenSize

    def pageSizes(self) -> List[Size]:
        if self.__pageSizes is None:
            if self.__engine.isPdf:
                pix = self.__engine.getPixmap(index=0, zoom=(1, 1))
                self.__pageSizes = [(pix.width(), pix.height())
                                    for i in range(self.pageCount())]
            elif self.__engine.isFile:
                pix = self.__engine.getPixmap(index=0)
                self.__pageSizes = [(pix.width(), pix.height())]
            else:
                page_size = []
                for index in range(self.pageCount()):
                    pix = self.__engine.getPixmap(index=index)
                    page_size.append((pix.width(), pix.height()))
                self.__pageSizes = page_size
        return self.__pageSizes

    def previewSize(self, index) -> Size:
        if self.__engine.isPdf:
            if self.__pdf_previewSize is None:
                p_width, p_height = self.pageSizes()[0]
                d_width, d_height = self.screenSize
                zoom_width = d_width / 12
                zoom_height = p_height / p_width * zoom_width
                self.__pdf_previewSize = round(zoom_width,
                                               0), round(zoom_height, 0)
            return self.__pdf_previewSize
        else:
            p_width, p_height = self.pageSizes()[index]
            d_width, d_height = self.screenSize
            zoom_width = d_width / 12
            zoom_height = p_height / p_width * zoom_width
            return round(zoom_width, 0), round(zoom_height, 0)

    def previewZoom(self, index) -> Zoom:
        if self.__engine.isPdf:
            if self.__pdf_previewZoom is None:
                p_width, p_height = self.pageSizes()[0]
                width, height = self.previewSize(0)
                self.__pdf_previewZoom = width / p_width, width / p_width
            return self.__pdf_previewZoom
        else:
            p_width, p_height = self.pageSizes()[0]
            width, height = self.previewSize(0)
            return width / p_width, width / p_width

    def displayZoom(self, index, file_auto=False, dir_auto=False) -> Zoom:
        def auto_scaled(target, scaled=True):
            p_width, p_height = target
            d_width, d_height = self.screenSize
            if (p_width, p_height) > (d_width, d_height):
                scaled_x = max(p_width / d_width, p_height / d_height) - 0.1
                displayZoom = scaled_x, scaled_x
                return displayZoom
            else:
                displayZoom = d_height * 0.8 / p_height, d_height * 0.8 / p_height
                if scaled:
                    return displayZoom
                return 1.0, 1.0

        if self.__displayZooms is None:
            if self.__engine.isPdf:
                if self.__pdf_displayZoom is None:
                    target = self.pageSizes()[index]
                    diszoom = auto_scaled(target)
                    self.__displayZooms = (diszoom
                                           for i in range(self.pageCount()))
                    self.__pdf_displayZoom = diszoom
                return self.__pdf_displayZoom
            elif self.__engine.isFile:
                target = self.pageSizes()[index]
                self.__displayZooms = [auto_scaled(target, False)]
            elif self.__engine.isDir:
                zooms = []
                for index in range(self.pageCount()):
                    pix = self.renderPixmap(index)
                    target = pix.width(), pix.height()
                    diszoom = auto_scaled(target, scaled=False)
                    zooms.append(diszoom)
                self.__displayZooms = zooms
        if self.__engine.isPdf:
            return self.__pdf_displayZoom
        return self.__displayZooms[index]

    def displaySize(self, index) -> Size:
        if self.__engine.isPdf:
            if self.__pdf_displaySize is None:
                p_width, p_height = self.pageSizes()[0]
                dis_zoom = self.displayZoom(0)
                width = round(p_width * dis_zoom[0], 0)
                height = round(p_height * dis_zoom[1], 0)
                self.__pdf_displaySize = width, height
            return self.__pdf_displaySize
        else:
            p_width, p_height = self.pageSizes()[index]
            dis_zoom = self.displayZoom(index)
            width, height = round(p_width * dis_zoom[0],
                                  0), round(p_height * dis_zoom[1], 0)
            return width, height

    def pageCount(self) -> int:
        return self.__engine.pageCount()

    def renderPixmap(self, index, zoom=(1, 1)) -> QPixmap:
        pixmap = self.__engine.getPixmap(index, zoom)
        return pixmap

    def rendering(self) -> NoReturn:
        self.is_editing = True
        render_indexes = []
        for index in range(self.pageCount()):
            render_indexes.append(index)

        self.pixmaps = render_indexes
        self.pixmaps_points = [[[]] for points in range(len(self.pixmaps))]

    def open(self, path) -> NoReturn:
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
                if self.reload == QMessageBox.Yes:
                    self.clear()
                    self.setEngine(path)
                    self.rendering()
                    self.display_signal.emit()
                    self.reload = QMessageBox.No
            else:
                self.clear()
                self.setEngine(path)
                self.rendering()
                self.display_signal.emit()

    def init(self):
        pass

    def __repr__(self):
        return f'PdfHandle<{self.__engine}>'


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


class OcrHandle(BaseHandle):
    ocr_signal = pyqtSignal(User)
    results_signal = pyqtSignal(object)

    def __init__(self, pdf_handle: PdfHandle):
        super().__init__()
        self.pdf_handle = pdf_handle
        self.result_handle = ResultsHandle()

    @slot(signal='ocr_signal', sender='self')
    def ocr(self, user: User):
        platform = user.platform
        if platform == 'b':
            self.baidu(user)
        else:
            pass

    def _parse_to_region(self, points: RectCoords) -> Region:
        region = ''
        for rect_coord in points:
            region += ','.join(map(str, rect_coord)) + ';'
        return region.strip(';')

    def baidu(self, user: User):
        config: Config = user.config
        if user.legal:
            workpath = config.get('parseinfo', 'workpath')
            service = config.get('recognition', 'type')
            number = config.get('recognition', 'number')
            delay = int(config.get('recognition', 'delay')) * 1000
            if service == '0':
                service_type = BAIDU_GENERAL_TYPE
            elif service == '1':
                service_type = BAIDU_ACCURATE_TYPE
            else:
                service_type = BAIDU_HANDWRITING_TYPE

            ocr_service = BaiduOcrService(user.id, user.key, user.secret, service_type, seq='\n')

            if self.pdf_handle.getEngine().render_type == 'file':  
                region = self._parse_to_region(self.pdf_handle.pixmaps_points[0])

                self.results_signal.emit(
                    f'<p style="font-weight:bold;color:purple">[{info_time()}] {basename(workpath)}:</p>'
                )

                json = ocr_service.request(region=region, image_path=workpath)
                self.thread().sleep(2)
                print('baidu')
                print(QThread.currentThreadId())
                res, flag = self.result_handle.process(json)
                print(res)
                if flag:
                    self.results_signal.emit('<p>%s</p>' % '\n'.join(res))
                else:
                    self.results_signal.emit(str(json))

            else:
                for index, points in enumerate(self.pdf_handle.pixmaps):
                    w, h = self.pdf_handle.displaySize(index)
                    pix = self.pdf_handle.renderPixmap(index)
                    qimage = pix.scaled(w, h).toImage()
                    img = ImageQt.fromqimage(qimage)
                    points = self.pdf_handle.pixmaps_points[index]
                    region = self._parse_to_region(points) if points else None
                    json = ocr_service.request(region=region, img=img)
                    res, flag = self.result_handle.process(json)
                    if flag:
                        self.results_signal.emit('<p>%s</p>' % '\n'.join(res))
                    else:
                        self.results_signal.emit(str(json))
                    self.thread().msleep(delay)