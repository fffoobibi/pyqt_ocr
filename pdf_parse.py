import fitz
from PIL import Image, ImageQt

pdf:fitz.Document = fitz.open('test.pdf')
pix = pdf[0].getPixmap()
for page in pdf:
    pixmap = page.getPixmap()
    print(pixmap.width,pixmap.height) 
    