import fitz
from PIL import Image, ImageQt
from PyQt5.QtGui import QPixmap, QImage
pdf:fitz.Document = fitz.open('test.pdf')
# help(pdf[0].getPixmap)
# pix = pdf[0].getPixmap(fitz.Matrix(2, 2))
# print(pix.width)


pdf_pixmap = pdf[0].getPixmap(fitz.Matrix(0.25,0.25)).writePNG('1.png')
print(pdf_pixmap)
# pixmap = QPixmap.fromImage(
#     QImage(pdf_pixmap.samples, pdf_pixmap.width, pdf_pixmap.height,
#             pdf_pixmap.stride, pdf_pixmap.fmt))





    
