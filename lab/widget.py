# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'untitled.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!
from customwidgets import ImgLabel
from PyQt5 import QtCore, QtGui, QtWidgets



class Label(ImgLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.fillRect(self.rect(), QtGui.QColor(120, 120, 120, 100))
        painter.end()

class Frame(QtWidgets.QFrame):

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        self.draw(painter)
        painter.end()

    def draw(self, paint):
        test= QtGui.QColor(120, 120, 120, 100)
        red = QtGui.QColor(255,0,0,0)
        t2 = QtGui.QColor(55,55,55,255)
        paint.fillRect(self.rect(), test)

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(286, 295)
        self.horizontalLayout = QtWidgets.QHBoxLayout(Form)
        self.horizontalLayout.setContentsMargins(30, -1, 30, -1)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame = Frame(Form)
        style= '''
        background: #C9D6FF;  /* fallback for old browsers */
        background: -webkit-linear-gradient(to right, #E2E2E2, #C9D6FF);  /* Chrome 10-25, Safari 5.1-6 */
        background: linear-gradient(to right, #E2E2E2, #C9D6FF); /* W3C, IE 10+/ Edge, Firefox 16+, Chrome 26+, Opera 12+, Safari 7+ */
'''
        self.frame.setStyleSheet("QFrame{border: 1px solid rgb(120,120,120);\n"
"border-radius: 5px}")
        self.frame.setFrameShape(QtWidgets.QFrame.Box)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = Label(self.frame)
        self.label.setStyleSheet("QLabel{border: 3px solid rgb(61, 61, 61); border-radius:2px}")
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.horizontalLayout.addWidget(self.frame)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label.setText(_translate("Form", "TextLabel"))
