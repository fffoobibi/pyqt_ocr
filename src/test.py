
import fitz
import time

def test():
    a = []
    eng:fitz.Document = fitz.open(r"C:\Users\fqk12\Desktop\progit_v2.1.30.pdf")
    for page in eng:
        pix = page.getPixmap()

    eng.close()
    eng.loadPage(1).getPixmap()
    from guppy import hpy;hxx = hpy();heap = hxx.heap()
    print(heap)
    time.sleep(10)

if __name__ == '__main__':

    test()
