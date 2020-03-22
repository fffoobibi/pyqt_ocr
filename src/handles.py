from dataclasses import dataclass, field
import datetime
import gc
from os import listdir
from functools import wraps
from datetime import datetime
from typing import List, NoReturn
from dataclasses import dataclass

from PIL import Image, ImageQt
from fitz import Matrix
from fitz import open as pdf_open
from os.path import isfile, exists, isdir, abspath, join, basename

from PyQt5.QtCore import QObject, pyqtSignal, Qt, QThread, QMutex
from PyQt5.QtWidgets import QMessageBox, QApplication, QFileDialog, QLabel
from PyQt5.QtGui import QPixmap, QImage, QTransform

from supports import *
from customwidgets import Validpoints
from ruia_ocr import BaiduOcrService, BAIDU_ACCURATE_TYPE, BAIDU_HANDWRITING_TYPE, BAIDU_GENERAL_TYPE


def info_time(): return datetime.now().strftime('%H:%M:%S')


def save_name(): return datetime.now().strftime('%Y%m%d_%H_%M_%S')


__all__ = ['PdfHandle', 'OcrHandle', 'ResultHandle']


class Engine(object):

    PDF_RENDER_ZOOM = 2

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
        self.__transform = QTransform()
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

    def getPixmap(self, index, zoom=(1.0, 1.0), rotate=None) -> QPixmap:
        if self.isPdf:
            x, y = zoom
            pdf_pixmap = self.render[index].getPixmap(
                Matrix(self.PDF_RENDER_ZOOM * x, self.PDF_RENDER_ZOOM * y))
            fmt = QImage.Format_RGBA8888 if pdf_pixmap.alpha else QImage.Format_RGB888
            pixmap = QPixmap.fromImage(
                QImage(pdf_pixmap.samples, pdf_pixmap.width, pdf_pixmap.height,
                       pdf_pixmap.stride, fmt))
        else:
            pix = QPixmap(self.pagesView()[index])
            width, height = pix.width(), pix.height()
            pixmap = pix.scaled(width * zoom[0],
                                height * zoom[1],
                                transformMode=Qt.SmoothTransformation)
        if not rotate:
            return pixmap
        else:
            pixmap = pixmap.transformed(self.__transform.rotate(rotate),
                                        Qt.SmoothTransformation)
            self.__transform.reset()
            return pixmap

    def close(self):
        if self.isPdf:
            self.render.close()
        self.render = None
        self.__pagesView = None
        gc.collect()

    def __getitem__(self, index) -> QPixmap:
        return self.getPixmap(index)

    def __repr__(self):
        return f'Engine<{self.target}>'


@dataclass
class PageState(object):
    page_index: int = -1
    fake_page_index: int = -1
    rotate: int = 0
    select_state: bool = False
    rect_coords: List[List[int]] = field(default_factory=list)


class PdfHandle(QObject):

    PRE_SCREEN_SHRINK = 12  # 预览图片宽度占据屏幕的1/12
    PRE_SHADOW_SHRINK = 14  # 阴影占据preview图片宽度的1/14

    open_signal = pyqtSignal()
    reload_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    display_signal = pyqtSignal(int, list)  # dis_index, showindexes
    ocr_signal = pyqtSignal(list, list)
    save_signal = pyqtSignal(object)

    def scaledPixmaptoPreview(self, pixmap) -> QPixmap:
        p_width, p_height = pixmap.width(), pixmap.height()
        true_width = self.screenSize[0] / self.PRE_SCREEN_SHRINK
        scaled = true_width / p_width
        p_height = p_height * scaled
        scaled_pix = pixmap.scaled(
            true_width, p_height, transformMode=Qt.SmoothTransformation)
        return scaled_pix

    def shadowWidth(self):
        if self.__shadowWidth is None:
            self.__shadowWidth = self.screenSize[
                0] / self.PRE_SCREEN_SHRINK / self.PRE_SHADOW_SHRINK
        return self.__shadowWidth

    def __init__(self):
        super().__init__()
        self.__screenSize = None
        self.__shadowWidth = None
        self.__engine = None

        self.reload = QMessageBox.No
        self.engined_counts = 0
        self.is_editing = False
        self.available_screen = True

        self.pixmaps_indexes = []
        self.fake_pixmaps_indexes = []
        self.pixmaps_points = []
        self.select_state = []

        self.page_states: List[PageState] = []

        self.__pdf_previewSize = None
        self.__pdf_previewZoom = None
        self.__pdf_displaySize = None
        self.__pdf_displayZoom = None

        self.__previewZooms: list = None
        self.__previewSizes: list = None
        self.__displayZooms: list = None
        self.__displaySizes: list = None
        self.__pageSizes: list = None
        self.rotates: list = None

        self.save_signal.connect(self.tolocalPdf)

    def clear(self):
        self.__previewZooms: list = None
        self.__previewSizes: list = None
        self.__displayZooms: list = None
        self.__displaySizes: list = None
        self.__pageSizes: list = None
        self.rotates: list = None

        self.__screenSize = None
        self.__shadowWidth = None
        self.is_editing = False

        self.__pdf_previewSize = None
        self.__pdf_previewZoom = None
        self.__pdf_displaySize = None
        self.__pdf_displayZoom = None

        self.pixmaps_indexes.clear()
        self.fake_pixmaps_indexes.clear()
        self.pixmaps_points.clear()
        self.select_state.clear()

        try:
            self.__engine.close()
        except AttributeError:
            ...
        finally:
            self.__engine = None
            gc.collect()
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

    def pageSizes(self, rotate=Rotates.ZERO_CLOCK) -> List[Size]:
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
            self.__previewSizes_h_w = [(h, w) for w, h in self.__pageSizes]

        if (rotate is Rotates.ZERO_CLOCK) or (rotate is Rotates.SIX_CLOCK):
            return self.__pageSizes
        elif (rotate is Rotates.TRE_CLOCK) or (rotate is Rotates.NIE_CLOCK):
            return self.__previewSizes_h_w

    def previewSize(self, index, rotate=Rotates.ZERO_CLOCK) -> Size:  # 默认预览图片屏幕分辨率的1/12
        if self.__engine.isPdf:
            if self.__pdf_previewSize is None:
                p_width, p_height = self.pageSizes(rotate)[0]
                d_width, d_height = self.screenSize
                zoom_width = d_width / self.PRE_SCREEN_SHRINK
                zoom_height = p_height / p_width * zoom_width
                self.__pdf_previewSize = round(zoom_width,
                                               0), round(zoom_height, 0)
            # return self.__pdf_previewSize
        else:
            if self.__previewSizes is None:
                temp = []
                for size in self.pageSizes(rotate):
                    p_width, p_height = size
                    d_width, d_height = self.screenSize
                    zoom_width = d_width / self.PRE_SCREEN_SHRINK
                    zoom_height = p_height / p_width * zoom_width
                    temp.append((round(zoom_width, 0), round(zoom_height, 0)))
                self.__previewSizes = temp
            # return self.__previewSizes[index]

        if (rotate is Rotates.ZERO_CLOCK) or (rotate is Rotates.SIX_CLOCK):
            if self.__engine.isPdf:
                return self.__pdf_previewSize
            return self.__previewSizes[index]
        elif (rotate is Rotates.TRE_CLOCK) or (rotate is Rotates.NIE_CLOCK):
            if self.__engine.isPdf:
                p_width, p_height = self.__pdf_previewSize[1], self.__pdf_previewSize[0]
            else:
                p_width, p_height = self.__previewSizes[index][1], self.__previewSizes[index][0]
            d_width, d_height = self.screenSize
            zoom_width = d_width / self.PRE_SCREEN_SHRINK
            zoom_height = p_height / p_width * zoom_width
            return round(zoom_width, 0), round(zoom_height, 0)

    def previewZoom(self, index, rotate=Rotates.ZERO_CLOCK) -> Zoom:
        if self.__engine.isPdf:
            if self.__pdf_previewZoom is None:
                p_width, p_height = self.pageSizes(rotate)[0]
                width, height = self.previewSize(0, rotate)
                self.__pdf_previewZoom = width / p_width, width / p_width
            # return self.__pdf_previewZoom
        else:
            if self.__previewZooms is None:
                temp = []
                for size in self.pageSizes(rotate):
                    p_width, p_height = size
                    width, height = self.previewSize(0, rotate)
                    temp.append((width / p_width, width / p_width))
                self.__previewZooms = temp
            # return self.__previewZooms[index]

        if (rotate is Rotates.ZERO_CLOCK) or (rotate is Rotates.SIX_CLOCK):
            if self.__engine.isPdf:
                return self.__pdf_previewZoom
            return self.__previewZooms[index]

        elif (rotate is Rotates.TRE_CLOCK) or (rotate is Rotates.NIE_CLOCK):
            if self.__engine.isPdf:
                return self.__pdf_previewZoom[1], self.__pdf_previewZoom[0]
            w_scale, h_sacle = self.__pdf_previewZooms[index]
            return h_sacle, w_scale

    def displayZoom(self, index, max_percent=0.80, rotate=Rotates.ZERO_CLOCK) -> Zoom:
        def auto_scaled(target):
            p_width, p_height = target
            print(2222)
            d_width, d_height = self.screenSize
            print(3333)
            if (d_height * max_percent <= p_height) or (d_width * max_percent <= p_width):
                print(4444)
                displayZoom = d_height * max_percent / \
                    p_height, d_height * max_percent / p_height
                return displayZoom
            return 1.0, 1.0

        if self.__engine.isPdf:
            if self.__pdf_displayZoom is None:
                target = self.pageSizes(rotate)[0]
                print(target)
                diszoom = auto_scaled(target)
                self.__displayZooms = (diszoom
                                       for i in range(self.pageCount()))
                self.__pdf_displayZoom = diszoom

            # return self.__pdf_displayZoom
        if self.__displayZooms is None:
            if self.__engine.isFile:
                target = self.pageSizes(rotate)[index]
                self.__displayZooms = [auto_scaled(target)]
            elif self.__engine.isDir:
                zooms = []
                for size in self.pageSizes(rotate):
                    diszoom = auto_scaled(size)
                    zooms.append(diszoom)
                self.__displayZooms = zooms
        # return self.__displayZooms[index]

        if (rotate is Rotates.ZERO_CLOCK) or (rotate is Rotates.SIX_CLOCK):
            if self.__engine.isPdf:
                return self.__pdf_displayZoom
            return self.__displayZooms[index]
        elif rotate is Rotates.TRE_CLOCK or rotate is Rotates.NIE_CLOCK:
            if self.__engine.isPdf:
                return self.__pdf_displayZoom[1], self.__pdf_displayZoom[0]
            w_scale, h_scale = self.__displayZooms[index]
            return h_scale, w_scale

    def displaySize(self, index, rotate=Rotates.ZERO_CLOCK) -> Size:
        if self.__engine.isPdf:
            if self.__pdf_displaySize is None:
                p_width, p_height = self.pageSizes(rotate)[0]
                dis_zoom = self.displayZoom(0, rotate=rotate)
                width = round(p_width * dis_zoom[0], 0)
                height = round(p_height * dis_zoom[1], 0)
                self.__pdf_displaySize = width, height
            # return self.__pdf_displaySize
        if self.__displaySizes is None:
            temp = []
            for ind, size in enumerate(self.pageSizes(rotate)):
                p_width, p_height = size
                dis_zoom = self.displayZoom(ind, rotate=rotate)
                width, height = round(p_width * dis_zoom[0],
                                      0), round(p_height * dis_zoom[1], 0)
                temp.append((width, height))
            self.__displaySizes = temp
        # return self.__displaySizes[index]

        if (rotate is Rotates.ZERO_CLOCK) or (rotate is Rotates.SIX_CLOCK):
            if self.__engine.isPdf:
                return self.__pdf_displaySize
            return self.__displaySizes[index]
        elif (rotate is Rotates.TRE_CLOCK) or (rotate is Rotates.NIE_CLOCK):
            if self.__engine.isPdf:
                return self.__pdf_displaySize[1], self.__pdf_displaySize[0]
            w, h = self.__displaySizes[index]
            return h, w

    def pageCount(self) -> int:
        return self.__engine.pageCount()

    def renderPixmap(self, index, zoom=(1, 1), rotate=None) -> QPixmap:
        return self.__engine.getPixmap(index, zoom, rotate)

    def rendering(self) -> NoReturn:
        self.is_editing = True
        render_indexes = []
        for index in range(self.pageCount()):
            render_indexes.append(index)

        length = len(render_indexes)

        self.pageSizes()
        self.displaySize(0)
        self.displayZoom(0)
        self.previewSize(0)
        self.previewZoom(0)

        self.pixmaps_indexes = render_indexes
        self.fake_pixmaps_indexes = render_indexes.copy()
        self.pixmaps_points = [[[]]] * length
        self.rotates = [False] * length
        self.select_state = [True] * length

        for index in render_indexes:
            pagestate = PageState(index, index, 0, True, [[]])
            self.page_states.append(pagestate)

    def open(self, path) -> NoReturn:
        self.engined_counts += 1
        if self.engined_counts == 1:
            flag = False
        else:
            flag = self.__engine.target == path

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

    def tolocalPdf(self, pages: List[int] = None):
        base_name = basename(self.getEngine().target)
        pdf_name, file_types = QFileDialog.getSaveFileName(
            None, 'pdf', join(home, base_name), 'PDF(*.pdf)')
        if pdf_name:
            if self.__engine.isPdf:
                if pages is None:
                    pgs = []
                    for state, index in zip(self.select_state,
                                            self.pixmaps_indexes):
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


class OcrHandle(QObject):

    ocr_signal = pyqtSignal(User)
    results_signal = pyqtSignal(object)

    def __init__(self, pdf_handle: PdfHandle = None):
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

    def _ocrByindex(self, index, user, is_pdf=False):
        if self.pdf_handle.select_state[index] == True:
            points = self.pdf_handle.pixmaps_points[index]
            region = self._parse_to_region(
                Validpoints.adjustCoords(points)) if points else None
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
            service = user.config.get('recognition', 'type', int)
            json = self.ocr_service.request(region=region, img=img)
            res, flag = self.result_handle.process(json)
            emit_res = '\n'.join(res)
            if flag:
                self.results_signal.emit(
                    f'<pre style="white-space:pre-wrap;">{emit_res}</pre>')
                self.latest_result[-1] = emit_res
                if service == 0:
                    user.config.info['parseinfo']['accurate'] += 1
                elif service == 1:
                    user.config.info['parseinfo']['basic'] += 1
                elif service == 2:
                    user.config.info['parseinfo']['handwriting'] += 1
                user.sync(Account())
                print(Account().active_user().config.info['parseinfo'])

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
            elif service == '2':
                service_type = BAIDU_HANDWRITING_TYPE

            self.ocr_service = BaiduOcrService(user.id,
                                               user.key,
                                               user.secret,
                                               service_type,
                                               seq='\n')
            render_type = self.pdf_handle.getEngine().render_type

            if render_type == 'file':
                self._ocrByindex(0, user)
            elif render_type == 'pdf' or render_type == 'dir':
                if self.workpath[:9] == '---此页---:':
                    true, current_text = self.workpath[9:].split(':')
                    self.workpath = f'page_{current_text}'
                    self._ocrByindex(int(true), user)
                else:
                    for true_page_index in self.pdf_handle.fake_pixmaps_indexes:
                        index = self.pdf_handle.pixmaps_indexes.index(
                            true_page_index)
                        self._ocrByindex(index, user, is_pdf=True)
                        self.thread().msleep(delay)


def test():
    import sys
    from PyQt5.QtWidgets import QWidget, QApplication

    class Widget(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # self.pdf_handle = PdfHandle()
            # self.pdf_handle.setEngine(r"C:\Users\fqk12\Desktop\test.jpg")
            # print(self.pdf_handle.pageSizes())
            # print(self.pdf_handle.getEngine().pagesView())
            # self.pdf_handle.previewSize(0)
            # self.pdf_handle.displaySize(0)
            self.label = QLabel(self)
            pix = QPixmap(r"C:\\Users\\fqk12\\Desktop\\test.png")
            print(pix.isNull())
            print(pix.size())
            self.label.setPixmap(pix)
            self.label.setScaledContents(True)
        
    app = QApplication(sys.argv)
    win = Widget()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
