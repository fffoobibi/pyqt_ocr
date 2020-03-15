
import fitz

def test():
    eng:fitz.Document = fitz.open(r"C:\Users\fqk12\Desktop\progit_v2.1.30.pdf")
    for page in eng:
        pix = page.getPixmap()
    eng.close()
    from guppy import hpy;hxx = hpy();heap = hxx.heap()
    print(heap)

if __name__ == '__main__':
    # main()
    test()
