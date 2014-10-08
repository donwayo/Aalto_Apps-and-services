
import asyncore
import socket
from settings import *
from messages import *

def log(s):
    print("[{0}] {1}".format(time.ctime(),s))

class P2PMain():
    ControlClients = {}
    Peers = {}
    HostIP = struct.unpack("!I",socket.inet_aton(socket.gethostbyname(socket.gethostname())))[0]
    ConnectionCount = 0

    def join(self, addr, port=PORT):
        # Should check that the parameters are sane here.
        peer = P2PConnection()
        peer.join(addr, port)
        self.Peers[self.ConnectionCount] = peer
        self.ConnectionCount = self.ConnectionCount + 1

    def sendBye(self, idx):
        if idx in self.Peers:
            self.Peers[idx].bye()
            return True
        return False

    def leave(self, peer):
        idx = -1
        for i in self.Peers:
            if self.Peers[i] == peer:
                idx = i
        self.peerDelete(idx)
        
    def peerDelete(self, idx):
        if idx >= 0 and (idx in self.Peers):
            self.Peers[i].close()
            del self.Peers[i]

    def controlConnect(self, client):
        self.ControlClients[self.ConnectionCount] = client
        self.ConnectionCount = self.ConnectionCount + 1

    def controlClose(self, client):
        idx = -1
        for i in self.ControlClients:
            if self.ControlClients[i] == client:
                idx = i
        self.controlDelete(idx)

    def controlDelete(self, idx):
        if idx >= 0 and (idx in self.ControlClients):
            self.ControlClients[i].close()
            del self.Peers[i]

    def shutDown(self):
        for i in p2p.Peers:
            self.Peers[i].close()

        for i in p2p.ControlClients:
            self.ControlClients[i].close()
        
        main.close()

    def __str__(self):
       return "\nControl connections: {0}\nPeer connections: {1}\n{2}\n".format(len(self.ControlClients), len(self.Peers), self.Peers.keys())


# Control server
class MainServerSocket(asyncore.dispatcher):
    def __init__(self, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(('',port))
        self.listen(5)

    def handle_accept(self):
        newSocket, address = self.accept()
        log("Connected from {0}:{1}.".format(address[0], address[1]))
        cclient = SecondaryServerSocket(newSocket)
        p2p.controlConnect(cclient)

# Control connection
class SecondaryServerSocket(asyncore.dispatcher_with_send):
    def handle_read(self):
        receivedData = self.recv(8192)
        if receivedData: 
            receivedData = receivedData.rstrip()
            # Search command is 's' followed by the search string.
            if receivedData[0] == 's':
                log('Search {0}'.format(receivedData[1:]))
                self.send('Searching {0}\n'.format(receivedData[1:]))

            # Join network is 'j' followed by 'b' for the bootstrap node or an IP address.
            elif receivedData[0] == 'j' and len(receivedData) > 1:
                
                if receivedData[1] == 'b':
                    self.send('Joining bootstrap node.\n')
                    p2p.join(BOOTSTRAP, PORT)
                else:
                    ipaddr = receivedData[1:]
                    p2p.join(ipaddr, PORT)
                    self.send('Joining {0}\n'.format(ipaddr))
            
            # Send Bye
            elif receivedData[0] == 'b' and len(receivedData) > 1:
                cId = int(receivedData[1:])
                p2p.sendBye(cId)
                log('Sending bye to {0}'.format(cId))

            # Display information
            elif receivedData[0] == 'i':
                if len(receivedData[1:]) > 0:
                    self.send("O: {0}\n".format(eval(receivedData[1:])))
                else:
                    self.send("{0}".format(p2p))
            # Close down.
            elif receivedData[0] == 'q':
                log("Closing")
                self.send('Bye\n')
                p2p.shutDown()

        else: 
            self.close()

    def handle_close(self):
        log("Disconnected from {0}.".format(self.getpeername()))
        self.close()

# P2P Connections
class P2PConnection(asyncore.dispatcher):

    out_buffer = b''

    Joined = False
    JoinMessageId = 0
    JoinTime = 0
    
    def join(self, addr, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (addr, port) )
        message = JoinMessage(p2p.HostIP)
        self.out_buffer = message.GetBytes()

        self.JoinMessageId = message.MessageId
        log("Attempting to join with Message:\n {0}".format(message))

    def bye(self):
        msg = ByeMessage(self.getIP())
        self.out_buffer = msg.GetBytes()
        log("Sending Bye message: \n{0}".format(msg))
        
    def handle_write(self):
        sent = self.send(self.out_buffer)
        self.out_buffer = self.out_buffer[sent:]

    def getIP(self):
        sockname = self.getsockname()
        ip = struct.unpack("!I", socket.inet_aton(sockname[0]))[0]
        return ip

    def getPort(self):
        sockname = self.getsockname()
        port = sockname[1]
        return port

    def writable(self):
        # use this to send periodic Pings
        # if self.Joined and (time.time() - self.JoinTime) > 5:
        return (len(self.out_buffer) > 0)

    def handle_read(self):
        receivedData = self.recv(8192)
        msg = ParseData(receivedData)
        if msg:
            self.handle_message(msg)
        else:
            log('Got trash')

    def handle_message(self, msg):
        if msg.Type == P2PMessage.MSG_JOIN:
            if msg.MessageId == self.JoinMessageId and \
            not msg.Request:
                self.Joined = True
                log("Joined successfully @ {0}".format(msg.GetSenderIP()))
                self.JoinTime = time.time()
        elif msg.Type == P2PMessage.MSG_BYE:
            log("Got BYE message. Closing connection with {0}:{1}".format(self.getpeername(), self.getPort()))
            p2p.leave(self)
        else:
            log("Unhandled message: \n{0}".format(msg))

    def handle_close(self):
        log("Disconnected from {0}:{1}.".format(self.getpeername()[0], self.getpeername()[1]))
        self.close()

    def handle_connect(self):
        log("Connected to {0}:{1}.".format(self.getpeername()[0], self.getpeername()[1] ))

    def __str__(self):
        return "Peer connection to {0}:{1}\n\tAlive for {2}".format(self.getpeername()[0], self.getpeername()[1], time.time()-self.JoinTime)

# P2P Server
p2p = P2PMain()
main = MainServerSocket(Q_PORT)
asyncore.loop(1)