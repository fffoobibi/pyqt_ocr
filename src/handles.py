import datetime
from os import listdir
from functools import wraps
from gc import collect
from datetime import datetime
from typing import List, NoReturn

from PIL import Image, ImageQt
from fitz import Matrix
from fitz import open as pdf_open
from os.path import isfile, exists, isdir, abspath, join, basename

from PyQt5.QtCore import QObject, pyqtSignal, Qt, QThread
from PyQt5.QtWidgets import QMessageBox, QApplication, QFileDialog
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
            self.render_type = 'pdf'
        elif exists(path) and isdir(path):
            self.render = path
            self.isPdf = False
            self.isDir = True
            self.isFile = False
            self.render_type = 'dir'
        elif isfile(path) and (path[-4:].lower() in [
                '.png', '.bmp', '.jpg', 'jpeg'
        ]):
            self.isFile = True
            self.isPdf = False
            self.isDir = False
            self.render_type = 'file'

        self.__pagesView = None
        self.target = path

    def getName(self, index) -> str:
        if self.isPdf:
            return self.pagesView()[index]
        else:
            return basename(self.pagesView()[index])

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
                    if file[-4:].lower() in ['.bmp', '.jpg', 'jpeg', '.png']
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
            pdf_pixmap = self.render[index].getPixmap(Matrix(2*x, 2*y))
            fmt = QImage.Format_RGBA8888 if pdf_pixmap.alpha else QImage.Format_RGB888
            pixmap = QPixmap.fromImage(
                QImage(pdf_pixmap.samples, pdf_pixmap.width, pdf_pixmap.height,
                       pdf_pixmap.stride, fmt))
            
            return pixmap
        else:
            pix = QPixmap(self.pagesView()[index])
            width, height = pix.width(), pix.height()
            pix = pix.scaled(width * zoom[0],
                             height * zoom[1],
                             transformMode=Qt.SmoothTransformation)
            return pix

    def close(self):
        if self.isPdf:
            self.render.close()
        self.render = None
        self.__pagesView = None
        collect()

    def __getitem__(self, index) -> QPixmap:
        return self.getPixmap(index)

    def __repr__(self):
        return f'Engine<{self.target}>'


class PdfHandle(QSingle):

    open_signal = pyqtSignal()
    display_signal = pyqtSignal(int, list)  # dis_index, showindexes
    reload_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    ocr_signal = pyqtSignal(list, list)
    save_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.__screenSize = None
        self.__engine = None

        self.reload = QMessageBox.No
        self.engined_counts = 0
        self.is_editing = False
        self.available_screen = True

        self.pixmaps_indexes = []
        self.fake_pixmaps_indexes = []
        self.pixmaps_points = []
        self.select_state = []
        self.edited_pdfs = []

        self.__pdf_preview = None
        self.__pdf_previewZoom = None
        self.__pdf_displaySize = None
        self.__pdf_displayZoom = None

        self.__previewZooms: list = None
        self.__previewSizes: list = None
        self.__displayZooms: list = None
        self.__displaySizes: list = None
        self.__pageSizes: list = None

        self.save_signal.connect(self.tolocalPdf)

    def clear(self):
        self.__previewZooms: list = None
        self.__previewSizes: list = None
        self.__displayZooms: list = None
        self.__displaySizes: list = None
        self.__pageSizes: list = None

        self.__screenSize = None
        self.is_editing = False
        
        self.__pdf_previewSize = None
        self.__pdf_previewZoom = None
        self.__pdf_displaySize = None
        self.__pdf_displayZoom = None

        self.pixmaps_indexes.clear()
        self.fake_pixmaps_indexes.clear()
        self.pixmaps_points.clear()
        self.edited_pdfs.clear()
        self.select_state.clear()
        
        try:
            self.__engine.close()
        finally:
            self.__engine = None
            collect()

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

    def previewSize(self, index, shrink=12) -> Size: # 默认预览图片屏幕分辨率的1/12
        if self.__engine.isPdf:
            if self.__pdf_previewSize is None:
                p_width, p_height = self.pageSizes()[0]
                d_width, d_height = self.screenSize
                zoom_width = d_width / shrink
                zoom_height = p_height / p_width * zoom_width
                self.__pdf_previewSize = round(zoom_width,
                                               0), round(zoom_height, 0)
            return self.__pdf_previewSize
        else:
            if self.__previewSizes is None:
                temp = []
                for size in self.pageSizes():
                    p_width, p_height = size
                    d_width, d_height = self.screenSize
                    zoom_width = d_width / 12
                    zoom_height = p_height / p_width * zoom_width
                    temp.append((round(zoom_width, 0), round(zoom_height, 0)))
                self.__previewSizes = temp
            return self.__previewSizes[index]

    def previewZoom(self, index, shrink=12) -> Zoom:
        if self.__engine.isPdf:
            if self.__pdf_previewZoom is None:
                p_width, p_height = self.pageSizes()[0]
                width, height = self.previewSize(0, shrink)
                self.__pdf_previewZoom = width / p_width, width / p_width
            return self.__pdf_previewZoom
        else:
            if self.__previewZooms is None:
                temp = []
                for size in self.pageSizes():
                    p_width, p_height = size
                    width, height = self.previewSize(0)
                    temp.append((width / p_width, width / p_width))
                self.__previewZooms = temp
            return self.__previewZooms[index]

    def displayZoom(self, index, max_percent=0.80) -> Zoom:
        def auto_scaled(target):
            p_width, p_height = target
            d_width, d_height = self.screenSize
            if (d_height * max_percent <=
                    p_height) or (d_width * max_percent <= p_width):
                displayZoom = d_height * max_percent / p_height, d_height * max_percent / p_height
                return displayZoom
            return 1.0, 1.0

        if self.__engine.isPdf:
            if self.__pdf_displayZoom is None:
                target = self.pageSizes()[0]
                diszoom = auto_scaled(target)
                self.__displayZooms = (diszoom
                                       for i in range(self.pageCount()))
                self.__pdf_displayZoom = diszoom


            return self.__pdf_displayZoom
        if self.__displayZooms is None:
            if self.__engine.isFile:
                target = self.pageSizes()[index]
                self.__displayZooms = [auto_scaled(target)]
            elif self.__engine.isDir:
                zooms = []
                for size in self.pageSizes():
                    diszoom = auto_scaled(size)
                    zooms.append(diszoom)
                self.__displayZooms = zooms
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
        if self.__displaySizes is None:
            temp = []
            for ind, size in enumerate(self.pageSizes()):
                p_width, p_height = size
                dis_zoom = self.displayZoom(ind)
                width, height = round(p_width * dis_zoom[0],
                                      0), round(p_height * dis_zoom[1], 0)
                temp.append((width, height))
            self.__displaySizes = temp
        return self.__displaySizes[index]

    def pageCount(self) -> int:
        return self.__engine.pageCount()

    def renderPixmap(self,
                     index,
                     zoom=(1, 1),
                     *,
                     pdf_zoom: Zoom = None,
                     pdf_prezoom: bool = False) -> QPixmap:
        if self.__engine.isPdf:
            pixmap = self.__engine.getPixmap(index, zoom)
        else:
            pixmap = self.__engine.getPixmap(index, zoom)
        return pixmap

    def rendering(self) -> NoReturn:
        self.is_editing = True
        render_indexes = []
        for index in range(self.pageCount()):
            render_indexes.append(index)

        self.pageSizes()
        self.displaySize(0)
        self.displayZoom(0)
        self.previewSize(0)
        self.previewZoom(0)

        self.pixmaps_indexes = render_indexes
        self.fake_pixmaps_indexes = render_indexes.copy()
        self.pixmaps_points = [[[]] for points in range(len(self.pixmaps_indexes))]
        self.select_state = [True] * self.pageCount()

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
                    self.display_signal.emit(0, self.pixmaps_indexes)
                    self.reload = QMessageBox.No
            else:
                self.clear()
                self.setEngine(path)
                self.rendering()
                self.display_signal.emit(0, self.pixmaps_indexes)

    def tolocalPdf(self, pages: List[int]=None):
        base_name = basename(self.getEngine().target)
        pdf_name, file_types = QFileDialog.getSaveFileName(
                None, 'pdf', join(home, base_name), 'PDF(*.pdf)')
        if pdf_name:
            if self.__engine.isPdf:
                if pages is None:
                    pgs = []
                    for state, index in zip(self.select_state, self.pixmaps_indexes):
                        if state:
                            pgs.append(index)
                else:
                    pgs = pages
                doc = pdf_open(self.__engine.target)
                doc.select(pgs)
                doc.save(pdf_name)
                doc.close()

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
            return res, True
        else:
            return results, False


class OcrHandle(QSingle):

    ocr_signal = pyqtSignal(User)
    results_signal = pyqtSignal(object)

    def __init__(self, pdf_handle: PdfHandle=None):
        super().__init__()
        self.pdf_handle = pdf_handle
        self.result_handle = ResultsHandle()
        self.latest_result = ['']

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

    def pixmapToImage(self, pixmap, sacled_size=None):
        if sacled_size is None:
            qimage = pixmap.toImage()
        else:
            qimage = pixmap.scaled(
                *sacled_size, transformMode=Qt.SmoothTransformation).toImage()

        image = ImageQt.fromqimage(qimage)
        return image

    def _ocrByindex(self, index=0, is_pdf=False):
        if self.pdf_handle.select_state[index] == True:
            points = self.pdf_handle.pixmaps_points[index]
            region = self._parse_to_region(points) if points else None
            pix = self.pdf_handle.renderPixmap(index)
            displaysize = self.pdf_handle.displaySize(index)
            img = self.pixmapToImage(pix, displaysize)
            if not is_pdf:
                msg = basename(self.workpath)
            else:
                msg = basename(self.workpath) + f' page_{index + 1}'
            self.results_signal.emit(
                f'<p style="font-weight:bold;color:purple">[{info_time()}] {msg}:</p>'
            )
            json = self.ocr_service.request(region=region, img=img)
            res, flag = self.result_handle.process(json)
            emit_res = '\n'.join(res)
            if flag:
                self.results_signal.emit(
                    f'<pre style="white-space:pre-wrap;">{emit_res}</pre>')
                self.latest_result[-1] = emit_res
            else:
                self.results_signal.emit(str(json))
                self.latest_result[-1] = str(json)

    def baidu(self, user: User):
        config: Config = user.config
        if user.legal:
            self.workpath = config.get('parseinfo', 'workpath')
            service = config.get('recognition', 'type')
            number = config.get('recognition', 'number')
            delay = int(config.get('recognition', 'delay')) * 1000
            if service == '0':
                service_type = BAIDU_GENERAL_TYPE
            elif service == '1':
                service_type = BAIDU_ACCURATE_TYPE
            else:
                service_type = BAIDU_HANDWRITING_TYPE

            self.ocr_service = BaiduOcrService(user.id,
                                               user.key,
                                               user.secret,
                                               service_type,
                                               seq='\n')
            render_type = self.pdf_handle.getEngine().render_type

            if render_type == 'file':
                self._ocrByindex(0)
            elif render_type == 'pdf' or render_type == 'dir':
                if self.workpath[:9] == '---此页---:':
                    true, current_text = self.workpath[9:].split(':')
                    self.workpath = f'page_{current_text}'
                    self._ocrByindex(int(true))
                else:
                    for true_page_index in self.pdf_handle.fake_pixmaps_indexes:
                        index = self.pdf_handle.pixmaps_indexes.index(true_page_index)
                        self._ocrByindex(index, is_pdf=True)
                        self.thread().msleep(delay)
