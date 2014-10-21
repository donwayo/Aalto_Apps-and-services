import sys, time, threading, random, Queue
import asyncore
import socket
from settings import *
from utils import *
from p2p import *
from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)


class GuiPart(QtGui.QMainWindow):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(601, 425)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.pb_search = QtGui.QPushButton(self.centralwidget)
        self.pb_search.setGeometry(QtCore.QRect(410, 60, 171, 32))
        self.pb_search.setObjectName(_fromUtf8("pb_search"))
        self.pb_join = QtGui.QPushButton(self.centralwidget)
        self.pb_join.setGeometry(QtCore.QRect(410, 130, 171, 32))
        self.pb_join.setObjectName(_fromUtf8("pb_join"))
        self.tabWidget = QtGui.QTabWidget(self.centralwidget)
        self.tabWidget.setGeometry(QtCore.QRect(10, 10, 381, 391))
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab = QtGui.QWidget()
        self.tab.setObjectName(_fromUtf8("tab"))
        self.sa_log = QtGui.QScrollArea(self.tab)
        self.sa_log.setGeometry(QtCore.QRect(10, 10, 351, 341))
        self.sa_log.setWidgetResizable(True)
        self.sa_log.setObjectName(_fromUtf8("sa_log"))
        self.scrollAreaWidgetContents = QtGui.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 349, 339))
        self.scrollAreaWidgetContents.setObjectName(_fromUtf8("scrollAreaWidgetContents"))
        self.sa_log.setWidget(self.scrollAreaWidgetContents)
        self.tabWidget.addTab(self.tab, _fromUtf8(""))
        self.tab_2 = QtGui.QWidget()
        self.tab_2.setObjectName(_fromUtf8("tab_2"))
        self.lw_peers = QtGui.QListWidget(self.tab_2)
        self.lw_peers.setGeometry(QtCore.QRect(10, 20, 351, 151))
        self.lw_peers.setObjectName(_fromUtf8("lw_peers"))
        self.lw_messages = QtGui.QListWidget(self.tab_2)
        self.lw_messages.setGeometry(QtCore.QRect(10, 190, 351, 161))
        self.lw_messages.setObjectName(_fromUtf8("lw_messages"))
        self.tabWidget.addTab(self.tab_2, _fromUtf8(""))
        self.pb_bye = QtGui.QPushButton(self.centralwidget)
        self.pb_bye.setGeometry(QtCore.QRect(410, 200, 171, 32))
        self.pb_bye.setObjectName(_fromUtf8("pb_bye"))
        self.le_search = QtGui.QLineEdit(self.centralwidget)
        self.le_search.setGeometry(QtCore.QRect(420, 40, 151, 21))
        self.le_search.setObjectName(_fromUtf8("le_search"))
        self.le_join = QtGui.QLineEdit(self.centralwidget)
        self.le_join.setGeometry(QtCore.QRect(420, 110, 151, 21))
        self.le_join.setObjectName(_fromUtf8("le_join"))
        self.le_bye = QtGui.QLineEdit(self.centralwidget)
        self.le_bye.setGeometry(QtCore.QRect(420, 180, 151, 21))
        self.le_bye.setObjectName(_fromUtf8("le_bye"))
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.action = QtGui.QAction(MainWindow)
        self.action.setObjectName(_fromUtf8("action"))

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.bindUi(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "P2P", None))
        self.pb_search.setText(_translate("MainWindow", "Search", None))
        self.pb_join.setText(_translate("MainWindow", "Join Host", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Log", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Status", None))
        self.pb_bye.setText(_translate("MainWindow", "Send Bye", None))
        self.action.setText(_translate("MainWindow", "Menu", None))

    def bindUi(self, MainWindow):
    	self.pb_join.clicked.connect(self.join)

    def __init__(self, queue, endcommand, *args):
        QtGui.QMainWindow.__init__(self, *args)
        self.queue = queue
        # We show the result of the thread in the gui, instead of the console
        self.setupUi(self)
        
        self.endcommand = endcommand
        self.p2p = P2PMain('localhost', PORT)

    def join(self):


    def closeEvent(self, ev):
        """
        We just call the endcommand when the window is closed
        instead of presenting a button for that purpose.
        """
        #self.p2p.shutDown()

        self.endcommand()

    def processIncoming(self):
        """
        Handle all the messages currently in the queue (if any).
        """
        #msg = str(self.p2p)
        #self.editor.setPlainText(str(msg))

        #while self.queue.qsize():
        #    try:
        #        # msg = self.queue.get(0)
        #        msg = str(self.p2p)
                # Check contents of message and do what it says
                # As a test, we simply print it
        #        self.editor.insertPlainText(str(msg))
        #    except Queue.Empty:
        #        pass

class ThreadedClient:
    """
    Launch the main part of the GUI and the worker thread. periodicCall and
    endApplication could reside in the GUI part, but putting them here
    means that you have all the thread controls in a single place.
    """
    def __init__(self):
        # Create the queue
        self.queue = Queue.Queue()

        # Set up the GUI part
        self.gui=GuiPart(self.queue, self.endApplication)
        self.gui.show()

        # A timer to periodically call periodicCall :-)
        self.timer = QtCore.QTimer()
        QtCore.QObject.connect(self.timer,
                           QtCore.SIGNAL("timeout()"),
                           self.periodicCall)
        # Start the timer -- this replaces the initial call to periodicCall
        self.timer.start(1000)

        # Set up the thread to do asynchronous I/O
        # More can be made if necessary
        self.running = 1
        self.thread1 = threading.Thread(target=self.workerThread1)
        self.thread1.daemon = True
        self.thread1.start()


    def periodicCall(self):
        """
        Check every 100 ms if there is something new in the queue.
        """
        self.gui.processIncoming()
        if not self.running:
            root.quit()

    def endApplication(self):
        self.running = 0


    def workerThread1(self):
        asyncore.loop(10)

rand = random.Random()
root = QtGui.QApplication(sys.argv)
client = ThreadedClient()
sys.exit(root.exec_())