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
        MainWindow.resize(669, 494)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.pb_search = QtGui.QPushButton(self.centralwidget)
        self.pb_search.setGeometry(QtCore.QRect(480, 60, 180, 32))
        self.pb_search.setObjectName(_fromUtf8("pb_search"))
        self.pb_join = QtGui.QPushButton(self.centralwidget)
        self.pb_join.setGeometry(QtCore.QRect(480, 140, 180, 32))
        self.pb_join.setObjectName(_fromUtf8("pb_join"))
        self.tabWidget = QtGui.QTabWidget(self.centralwidget)
        self.tabWidget.setGeometry(QtCore.QRect(10, 10, 451, 461))
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab = QtGui.QWidget()
        self.tab.setObjectName(_fromUtf8("tab"))
        self.enable_auto_scroll = QtGui.QCheckBox(self.tab)
        self.enable_auto_scroll.setEnabled(True)
        self.enable_auto_scroll.setGeometry(QtCore.QRect(350, 400, 101, 41))
        self.enable_auto_scroll.setObjectName(_fromUtf8("enable_auto_scroll"))
        self.sa_log = QtGui.QTextBrowser(self.tab)
        self.sa_log.setGeometry(QtCore.QRect(10, 20, 421, 391))
        self.sa_log.setObjectName(_fromUtf8("sa_log"))
        self.clear_log = QtGui.QPushButton(self.tab)
        self.clear_log.setGeometry(QtCore.QRect(60, 407, 140, 32))
        self.clear_log.setObjectName(_fromUtf8("clear_log"))
        self.tabWidget.addTab(self.tab, _fromUtf8(""))
        self.tab_2 = QtGui.QWidget()
        self.tab_2.setObjectName(_fromUtf8("tab_2"))
        self.lw_peers = QtGui.QListWidget(self.tab_2)
        self.lw_peers.setGeometry(QtCore.QRect(10, 20, 421, 151))
        self.lw_peers.setObjectName(_fromUtf8("lw_peers"))
        self.lw_messages = QtGui.QListWidget(self.tab_2)
        self.lw_messages.setGeometry(QtCore.QRect(10, 190, 421, 161))
        self.lw_messages.setObjectName(_fromUtf8("lw_messages"))
        self.tabWidget.addTab(self.tab_2, _fromUtf8(""))
        self.pb_bye = QtGui.QPushButton(self.centralwidget)
        self.pb_bye.setGeometry(QtCore.QRect(479, 210, 180, 32))
        self.pb_bye.setObjectName(_fromUtf8("pb_bye"))
        self.le_search = QtGui.QLineEdit(self.centralwidget)
        self.le_search.setGeometry(QtCore.QRect(485, 40, 171, 21))
        self.le_search.setObjectName(_fromUtf8("le_search"))
        self.le_join = QtGui.QLineEdit(self.centralwidget)
        self.le_join.setGeometry(QtCore.QRect(485, 120, 170, 21))
        self.le_join.setObjectName(_fromUtf8("le_join"))
        self.le_bye = QtGui.QLineEdit(self.centralwidget)
        self.le_bye.setGeometry(QtCore.QRect(484, 190, 170, 21))
        self.le_bye.setObjectName(_fromUtf8("le_bye"))
        self.le_log = QtGui.QLineEdit(self.centralwidget)
        self.le_log.setGeometry(QtCore.QRect(484, 320, 170, 21))
        self.le_log.setObjectName(_fromUtf8("le_log"))
        self.pb_log = QtGui.QPushButton(self.centralwidget)
        self.pb_log.setGeometry(QtCore.QRect(478, 340, 180, 32))
        self.pb_log.setObjectName(_fromUtf8("pb_log"))
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        # set log console
        self.sa_log.ensureCursorVisible()
        self.autoScroll = True
        XStream.stdout().messageWritten.connect( self.updateConsole )
        XStream.stderr().messageWritten.connect( self.updateConsole )

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.bindUi(MainWindow)

    def updateConsole(self, text):
        self.sa_log.insertPlainText(text)
        if self.autoScroll:
            vbar = self.sa_log.verticalScrollBar()
            vbar.setValue(vbar.maximum())

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "P2P", None))
        self.pb_search.setText(_translate("MainWindow", "Search", None))
        self.pb_join.setText(_translate("MainWindow", "Join Host", None))
        self.clear_log.setText(_translate("MainWindow", "Clear Log", None))
        self.enable_auto_scroll.setText(_translate("MainWindow", "Auto scroll", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Log", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Status", None))
        self.pb_bye.setText(_translate("MainWindow", "Send Bye", None))
        self.pb_log.setText(_translate("MainWindow", "Set Log Level", None))

    def bindUi(self, MainWindow):
    	self.pb_join.clicked.connect(self.join)
        self.pb_bye.clicked.connect(self.bye)
        self.pb_search.clicked.connect(self.search)
        self.clear_log.clicked.connect(self.clearLog)
        self.enable_auto_scroll.stateChanged.connect(self.setAutoScroll)
        self.enable_auto_scroll.setCheckState(QtCore.Qt.Checked)
        self.pb_log.clicked.connect(self.setLogLevel)

    def __init__(self, queue, endcommand, *args):
        QtGui.QMainWindow.__init__(self, *args)
        self.queue = queue
        self.setupUi(self)
        self.peers = {}
        self.messages = {}
        self.endcommand = endcommand

        serverPort = PORT
        if len(sys.argv) > 1:
            serverPort = int(sys.argv[1])
        self.p2p = P2PMain('0.0.0.0', serverPort, queue)

    def setLogLevel(self):
        level = int(self.le_log.text()) * 10
        logger.info("Setting to log level: {0}".format(level))
        logger.setLevel(level)

    def clearLog(self):
        self.sa_log.setText("")

    def setAutoScroll(self):
        self.autoScroll = (self.enable_auto_scroll.checkState() == QtCore.Qt.Checked)

    def bye(self):
        self.queue.put(['b', int(self.le_bye.text())])

    def join(self):
        self.queue.put(['j', str(self.le_join.text())])

    def search(self):
        self.queue.put(['s', str(self.le_search.text())])

    def closeEvent(self, ev):
        self.queue.put(['q',0])
        self.endcommand()

    def processIncoming(self):
        status = self.p2p.getStatus()

        # Remove messages that are not present anymore
        for m in self.messages.keys():
            if m not in status['messages']:
                self.messages[m].setText('Dead')
                self.lw_messages.takeItem(self.lw_messages.row(self.messages[m]))
                del self.messages[m]

        # Remove peers that are not present anymore
        for p in self.peers.keys():
            if not p in status['peers']:
                self.lw_peers.takeItem(self.lw_peers.row(self.peers[p]))
                del self.peers[p]

        # Update messages (from, time, query)
        for m in status['messages']:
            text = '{2}\t{0} ({1})'.format(status['messages'][m][2],status['messages'][m][0],m)
            if m in self.messages:
                self.messages[m].setText(text)
            else:
                self.messages[m] = QtGui.QListWidgetItem(text)
                self.lw_messages.addItem(self.messages[m])

        # Update peers
        for p in status['peers']:
            text = '{1}\t{0}'.format(status['peers'][p],p)
            if p in self.peers:
                self.peers[p].setText(text)
            else:
                self.peers[p] = QtGui.QListWidgetItem(text)
                self.lw_peers.addItem(self.peers[p])
        


class ThreadedClient:
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
        self.timer.start(500)

        # Set up the thread to do asynchronous I/O
        # More can be made if necessary
        self.running = 1
        self.thread1 = threading.Thread(target=self.workerThread1)
        self.thread1.daemon = True
        self.thread1.start()

    def periodicCall(self):
        self.gui.processIncoming()
        if not self.running:
            root.quit()

    def endApplication(self):
        self.running = 0

    def workerThread1(self):
        asyncore.loop(1)

class QtHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
    def emit(self, record):
        record = self.format(record)
        if record: XStream.stdout().write('%s\n'%record)

class XStream(QtCore.QObject):
    _stdout = None
    _stderr = None
    messageWritten = QtCore.pyqtSignal(str)
    def flush( self ):
        pass
    def fileno( self ):
        return -1
    def write( self, msg ):
        if ( not self.signalsBlocked() ):
            self.messageWritten.emit(unicode(msg))
    @staticmethod
    def stdout():
        if ( not XStream._stdout ):
            XStream._stdout = XStream()
            sys.stdout = XStream._stdout
        return XStream._stdout
    @staticmethod
    def stderr():
        if ( not XStream._stderr ):
            XStream._stderr = XStream()
            sys.stderr = XStream._stderr
        return XStream._stderr

# init logging
logger = logging.getLogger('p2p')
handler = QtHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", '[%H:%M:%S]'))
logger.addHandler(handler)
logger.setLevel(logging.CRITICAL)

rand = random.Random()
root = QtGui.QApplication(sys.argv)
client = ThreadedClient()
sys.exit(root.exec_())