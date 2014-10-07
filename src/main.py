import asyncore
import socket
from settings import *
from messages import *

def log(s):
    print("[{0}] {1}".format(time.ctime(),s))

class P2PMain():
    ControlClients = []
    P2PIn = []
    P2POut = []
    HostIP = struct.unpack("!I",socket.inet_aton(socket.gethostbyname(socket.gethostname())))[0]

# Control server
class MainServerSocket(asyncore.dispatcher):
    def __init__(self, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(('',port))
        self.listen(5)

    def handle_accept(self):
        newSocket, address = self.accept()
        log("Connected from {0}.".format(address))
        cclient = SecondaryServerSocket(newSocket)
        p2p.ControlClients.append(cclient)

# Control connection
class SecondaryServerSocket(asyncore.dispatcher_with_send):
    def handle_read(self):
        receivedData = self.recv(8192)
        if receivedData: 

            # Search command is 's' followed by the search string.
            if receivedData[0] == 's':
                log('Search {0}'.format(receivedData[1:]))
                self.send('Searching {0}\n'.format(receivedData[1:]))

            # Join network is 'j' followed by 'b' for the bootstrap node or an IP address.
            elif receivedData[0] == 'j' and len(receivedData) > 1:
                if receivedData[1] == 'b':
                    self.send('Joining bootstrap node.\n')
                    client = P2PClient(BOOTSTRAP, PORT)
                    p2p.P2POut.append(client)
                else:
                    ipaddr = receivedData[1:]
                    self.send('Joining {0}\n'.format(ipaddr))

            # Close down.
            elif receivedData[0] == 'q':
                log("Closing")
                self.send('Bye\n')
                
                for i in p2p.P2PIn:
                    i.close()
                for i in p2p.P2POut:
                    i.close
                
                main.close()

                for i in p2p.ControlClients:
                    i.close()

        else: 
            self.close()

    def handle_close(self):
        log("Disconnected from {0}.".format(self.getpeername()))
        self.close()

# Client connections
class P2PClient(asyncore.dispatcher):
    out_buffer = b''
    Joined = False
    JoinMessageId = 0
    JoinTime = 0
    def __init__(self, addr, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (addr, port) )
        message = JoinMessage(p2p.HostIP)
        self.out_buffer = message.GetBytes()

        self.JoinMessageId = message.MessageId
        log("Attempting to join with Message:\n {0}".format(message))

    def handle_write(self):
        sent = self.send(self.out_buffer)
        self.out_buffer = self.out_buffer[sent:]

    def writable(self):
        # use this to send periodic Pings
        # if self.Joined and (time.time() - self.JoinTime) > 5:
        return (len(self.out_buffer) > 0)

    def handle_read(self):
        receivedData = self.recv(8192)
        msg = ParseData(receivedData)
        if msg:
            if msg.Type == P2PMessage.MSG_JOIN and \
            msg.MessageId == self.JoinMessageId and \
            not msg.Request:
                self.Joined = True
                log("Joined successfully @ {0}".format(msg.GetSenderIP()))
                self.JoinTime = time.time()
            else:
                log("Unhandled message: \n{0}".format(msg))
        else:
            log('Got trash')

    def handle_close(self):
        log("Disconnected from {0}.".format(self.getpeername()))
        self.close()

    def handle_connect(self):
        log("Connected to {0}.".format(self.getpeername()))

# P2P Server
main = MainServerSocket(Q_PORT)
p2p = P2PMain()
asyncore.loop(1)