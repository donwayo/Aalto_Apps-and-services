import sys, time, threading, random, Queue
import asyncore
import socket
from settings import *
from utils import *
from p2p import *
from PyQt4 import QtGui, QtCore as qt

class GuiPart(QtGui.QMainWindow):

    def __init__(self, queue, endcommand, *args):
        QtGui.QMainWindow.__init__(self, *args)
        self.queue = queue
        # We show the result of the thread in the gui, instead of the console
        self.editor = QtGui.QTextEdit(self)
        self.setCentralWidget(self.editor)
        self.endcommand = endcommand
        self.p2p = P2PMain('localhost', PORT)



    def closeEvent(self, ev):
        """
        We just call the endcommand when the window is closed
        instead of presenting a button for that purpose.
        """
        self.p2p.shutDown()

        self.endcommand()

    def processIncoming(self):
        """
        Handle all the messages currently in the queue (if any).
        """
        msg = str(self.p2p)
        self.editor.setPlainText(str(msg))

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
        self.timer = qt.QTimer()
        qt.QObject.connect(self.timer,
                           qt.SIGNAL("timeout()"),
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
        """
        This is where we handle the asynchronous I/O. For example, it may be
        a 'select()'.
        One important thing to remember is that the thread has to yield
        control.
        """
        asyncore.loop(10)

        #while self.running:
            # To simulate asynchronous I/O, we create a random number at
            # random intervals. Replace the following 2 lines with the real
            # thing.
        #    time.sleep(rand.random() * 0.3)
        #    msg = rand.random()
        #    self.queue.put(msg)

rand = random.Random()
root = QtGui.QApplication(sys.argv)
client = ThreadedClient()
sys.exit(root.exec_())