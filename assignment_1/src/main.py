import asyncore
import socket
import sys
from settings import *
from messages import *

def log(s,l):
    if l <= LOG_LVL:
        print("[{0}] {1}".format(time.ctime(),s))

class P2PMain():
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

    def shutDown(self):
        for i in p2p.Peers:
            self.Peers[i].close()
        cmdline.close()
        
    def __str__(self):
       return "\nPeer connections: {1}\n".format(len(self.Peers), self.Peers.keys())


# Command line control
class CmdlineClient(asyncore.file_dispatcher):
    def __init__(self, file):
        asyncore.file_dispatcher.__init__(self, file)

    def handle_read(self):
        receivedData = self.recv(1024)
        if receivedData: 
            receivedData = receivedData.rstrip()
            # Search command is 's' followed by the search string.
            if receivedData[0] == 's':
                log('Search {0}'.format(receivedData[1:]), 2)
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
                log('Got request to send Bye message to connection {0}'.format(cId), 1)
                p2p.sendBye(cId)
                
            # Display information
            elif receivedData[0] == 'i':
                if len(receivedData[1:]) > 0:
                    self.send("O: {0}\n".format(eval(receivedData[1:])))
                else:
                    self.send("{0}\n".format(p2p))
            # Close down.
            elif receivedData[0] == 'q':
                log("Closing down.",1)
                self.send('Bye\n')
                p2p.shutDown()

        else: 
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
        log("Attempting to join with Message:\n {0}".format(message),2)

    def bye(self):
        msg = ByeMessage(self.getIP())
        self.out_buffer = msg.GetBytes()
        log("Sending Bye message to {0}".format(self.getpeername()[0]),1)
        log("{0}".format(msg),2)
        
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
            log('{0}'.format(msg), 3)
        elif len(receivedData) > 0:
            log('Got trash', 1)

    def handle_message(self, msg):
        if msg.Type == P2PMessage.MSG_JOIN:
            if msg.MessageId == self.JoinMessageId and \
            not msg.Request:
                self.Joined = True
                log("Joined successfully @ {0}".format(msg.GetSenderIP()), 1)
                self.JoinTime = time.time()
        elif msg.Type == P2PMessage.MSG_BYE:
            log("Got BYE message. Closing connection with {0}:{1}".format(self.getpeername(), self.getPort()),1)
            p2p.leave(self)
        else:
            log("Unhandled message from {0}:{1}".format(self.getpeername()[0], self.getpeername()[1]),1)
            log("{0}".format(msg), 2)

    def handle_close(self):
        log("Disconnected from {0}:{1}.".format(self.getpeername()[0], self.getpeername()[1]),1)
        p2p.leave(self)

    def handle_connect(self):
        log("Connected to {0}:{1}.".format(self.getpeername()[0], self.getpeername()[1] ),1)

    def __str__(self):
        return "Peer connection to {0}:{1}\n\tAlive for {2}".format(self.getpeername()[0], self.getpeername()[1], time.time()-self.JoinTime,1)

# P2P Server
p2p = P2PMain()
cmdline = CmdlineClient(sys.stdin)
asyncore.loop(1)