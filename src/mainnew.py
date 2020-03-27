# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(659, 523)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setMouseTracking(True)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.stackedWidget = QtWidgets.QStackedWidget(self.centralwidget)
        self.stackedWidget.setMouseTracking(True)
        self.stackedWidget.setObjectName("stackedWidget")
        self.ocrWidget = PdfWidget()
        self.ocrWidget.setObjectName("ocrwidget")
        self.stackedWidget.addWidget(self.ocrWidget)
        self.analysisWidget = AnalysisWidget()
        self.analysisWidget.setObjectName("analysiswidget")
        self.stackedWidget.addWidget(self.analysisWidget)
        self.verticalLayout_3.addWidget(self.stackedWidget)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 659, 26))
        self.menubar.setObjectName("menubar")
        self.menu = QtWidgets.QMenu(self.menubar)
        self.menu.setObjectName("menu")
        self.menu_2 = QtWidgets.QMenu(self.menubar)
        self.menu_2.setObjectName("menu_2")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.action_config = QtWidgets.QAction(MainWindow)
        self.action_config.setObjectName("action_config")
        self.action_advanced = QtWidgets.QAction(MainWindow)
        self.action_advanced.setObjectName("action_advanced")
        self.action_ana = QtWidgets.QAction(MainWindow)
        self.action_ana.setObjectName("action_ana")
        self.action_main = QtWidgets.QAction(MainWindow)
        self.action_main.setObjectName("action_main")
        self.menu.addAction(self.action_config)
        self.menu.addAction(self.action_advanced)
        self.menu_2.addAction(self.action_ana)
        self.menu_2.addAction(self.action_main)
        self.menubar.addAction(self.menu.menuAction())
        self.menubar.addAction(self.menu_2.menuAction())

        self.retranslateUi(MainWindow)
        self.stackedWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.menu.setTitle(_translate("MainWindow", "设置"))
        self.menu_2.setTitle(_translate("MainWindow", "其他"))
        self.action_config.setText(_translate("MainWindow", "配置"))
        self.action_advanced.setText(_translate("MainWindow", "高级"))
        self.action_ana.setText(_translate("MainWindow", "分析"))
        self.action_main.setText(_translate("MainWindow", "主界面"))
from pdfnew import PdfWidget
from analysis import AnalysisWidget