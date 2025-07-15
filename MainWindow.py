# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MainWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QHeaderView, QLabel,
    QMainWindow, QMenu, QMenuBar, QProgressBar,
    QPushButton, QSizePolicy, QSpinBox, QTableWidget,
    QTableWidgetItem, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1351, 833)
        self.actionDokumentation = QAction(MainWindow)
        self.actionDokumentation.setObjectName(u"actionDokumentation")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout_2 = QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.progressBar_generate = QProgressBar(self.centralwidget)
        self.progressBar_generate.setObjectName(u"progressBar_generate")
        self.progressBar_generate.setValue(0)

        self.gridLayout_2.addWidget(self.progressBar_generate, 3, 0, 1, 1)

        self.pushButton_generate = QPushButton(self.centralwidget)
        self.pushButton_generate.setObjectName(u"pushButton_generate")

        self.gridLayout_2.addWidget(self.pushButton_generate, 2, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(6)
        self.tableWidget_n_groups = QTableWidget(self.centralwidget)
        if (self.tableWidget_n_groups.columnCount() < 2):
            self.tableWidget_n_groups.setColumnCount(2)
        self.tableWidget_n_groups.setObjectName(u"tableWidget_n_groups")
        self.tableWidget_n_groups.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableWidget_n_groups.sizePolicy().hasHeightForWidth())
        self.tableWidget_n_groups.setSizePolicy(sizePolicy)
        self.tableWidget_n_groups.setAutoScrollMargin(16)
        self.tableWidget_n_groups.setColumnCount(2)

        self.gridLayout.addWidget(self.tableWidget_n_groups, 1, 1, 1, 1)

        self.spinBox_n_rounds = QSpinBox(self.centralwidget)
        self.spinBox_n_rounds.setObjectName(u"spinBox_n_rounds")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.spinBox_n_rounds.sizePolicy().hasHeightForWidth())
        self.spinBox_n_rounds.setSizePolicy(sizePolicy1)
        self.spinBox_n_rounds.setMinimum(1)

        self.gridLayout.addWidget(self.spinBox_n_rounds, 3, 1, 1, 1)

        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")
        sizePolicy2.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy3)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.tableWidget_group_names_jungscharen = QTableWidget(self.centralwidget)
        self.tableWidget_group_names_jungscharen.setObjectName(u"tableWidget_group_names_jungscharen")
        self.tableWidget_group_names_jungscharen.setEnabled(True)
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.tableWidget_group_names_jungscharen.sizePolicy().hasHeightForWidth())
        self.tableWidget_group_names_jungscharen.setSizePolicy(sizePolicy4)

        self.gridLayout.addWidget(self.tableWidget_group_names_jungscharen, 1, 2, 1, 1)

        self.spinBox_n_games = QSpinBox(self.centralwidget)
        self.spinBox_n_games.setObjectName(u"spinBox_n_games")
        sizePolicy1.setHeightForWidth(self.spinBox_n_games.sizePolicy().hasHeightForWidth())
        self.spinBox_n_games.setSizePolicy(sizePolicy1)
        self.spinBox_n_games.setMinimum(1)

        self.gridLayout.addWidget(self.spinBox_n_games, 2, 1, 1, 1)

        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")
        sizePolicy2.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.spinBox_n_jungscharen = QSpinBox(self.centralwidget)
        self.spinBox_n_jungscharen.setObjectName(u"spinBox_n_jungscharen")
        sizePolicy3.setHeightForWidth(self.spinBox_n_jungscharen.sizePolicy().hasHeightForWidth())
        self.spinBox_n_jungscharen.setSizePolicy(sizePolicy3)
        self.spinBox_n_jungscharen.setMinimum(1)

        self.gridLayout.addWidget(self.spinBox_n_jungscharen, 0, 1, 1, 1)

        self.tableWidget_game_names = QTableWidget(self.centralwidget)
        self.tableWidget_game_names.setObjectName(u"tableWidget_game_names")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.tableWidget_game_names.sizePolicy().hasHeightForWidth())
        self.tableWidget_game_names.setSizePolicy(sizePolicy5)

        self.gridLayout.addWidget(self.tableWidget_game_names, 2, 2, 1, 1)


        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1351, 33))
        self.menuInfo = QMenu(self.menubar)
        self.menuInfo.setObjectName(u"menuInfo")
        MainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuInfo.menuAction())
        self.menuInfo.addAction(self.actionDokumentation)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionDokumentation.setText(QCoreApplication.translate("MainWindow", u"Dokumentation", None))
        self.pushButton_generate.setText(QCoreApplication.translate("MainWindow", u"Spielplan generieren", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Anzahl Gruppen", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Anzahl Runden", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Anzahl Jungscharen", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Anzahl Spiele", None))
        self.menuInfo.setTitle(QCoreApplication.translate("MainWindow", u"Info", None))
    # retranslateUi

