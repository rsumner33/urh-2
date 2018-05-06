# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '../ui/tab_interpretation.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Interpretation(object):
    def setupUi(self, Interpretation):
        Interpretation.setObjectName("Interpretation")
        Interpretation.resize(631, 561)
        self.verticalLayout = QtWidgets.QVBoxLayout(Interpretation)
        self.verticalLayout.setObjectName("verticalLayout")
        self.scrollArea = ScrollArea(Interpretation)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setAcceptDrops(True)
        self.scrollArea.setStyleSheet("")
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrlAreaSignals = QtWidgets.QWidget()
        self.scrlAreaSignals.setGeometry(QtCore.QRect(0, 0, 611, 513))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrlAreaSignals.sizePolicy().hasHeightForWidth())
        self.scrlAreaSignals.setSizePolicy(sizePolicy)
        self.scrlAreaSignals.setAutoFillBackground(True)
        self.scrlAreaSignals.setStyleSheet("")
        self.scrlAreaSignals.setObjectName("scrlAreaSignals")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.scrlAreaSignals)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter = QtWidgets.QSplitter(self.scrlAreaSignals)
        self.splitter.setStyleSheet("QSplitter::handle:vertical {\n"
"margin: 4px 0px;\n"
"    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, \n"
"stop:0 rgba(255, 255, 255, 0), \n"
"stop:0.5 rgba(100, 100, 100, 100), \n"
"stop:1 rgba(255, 255, 255, 0));\n"
"    image: url(:/icons/data/icons/splitter_handle_horizontal.svg);\n"
"}")
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(6)
        self.splitter.setObjectName("splitter")
        self.labelGettingStarted = QtWidgets.QLabel(self.splitter)
        font = QtGui.QFont()
        font.setPointSize(32)
        self.labelGettingStarted.setFont(font)
        self.labelGettingStarted.setStyleSheet("")
        self.labelGettingStarted.setAlignment(QtCore.Qt.AlignCenter)
        self.labelGettingStarted.setWordWrap(True)
        self.labelGettingStarted.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.labelGettingStarted.setObjectName("labelGettingStarted")
        self.placeholderLabel = QtWidgets.QLabel(self.splitter)
        self.placeholderLabel.setText("")
        self.placeholderLabel.setObjectName("placeholderLabel")
        self.verticalLayout.addWidget(self.splitter)
        self.scrollArea.setWidget(self.scrlAreaSignals)
        self.verticalLayout.addWidget(self.scrollArea)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lLoadingFile = QtWidgets.QLabel(Interpretation)
        self.lLoadingFile.setObjectName("lLoadingFile")
        self.horizontalLayout.addWidget(self.lLoadingFile)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.lCtrlStatus = QtWidgets.QLabel(Interpretation)
        self.lCtrlStatus.setObjectName("lCtrlStatus")
        self.horizontalLayout.addWidget(self.lCtrlStatus)
        self.lShiftStatus = QtWidgets.QLabel(Interpretation)
        self.lShiftStatus.setObjectName("lShiftStatus")
        self.horizontalLayout.addWidget(self.lShiftStatus)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Interpretation)
        QtCore.QMetaObject.connectSlotsByName(Interpretation)

    def retranslateUi(self, Interpretation):
        _translate = QtCore.QCoreApplication.translate
        Interpretation.setWindowTitle(_translate("Interpretation", "Form"))
        self.lLoadingFile.setText(_translate("Interpretation", "Loading file 1/42"))
        self.lCtrlStatus.setText(_translate("Interpretation", "Ctrl Status"))
        self.lShiftStatus.setText(_translate("Interpretation", "Statusinformationen like a Bozz"))

from urh.ui.ScrollArea import ScrollArea
