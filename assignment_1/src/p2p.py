import struct
import asyncore
import time
import binascii
from messages import *
from settings import *

# Main class. 
class P2PMain():
    Peers = {}
    HostIP = struct.unpack("!I",socket.inet_aton(socket.gethostbyname(socket.gethostname())))[0]
    ConnectionCount = 0
    P2Pserver = None
    QueryMessages = {}
    LastPingTime = 0

    def __init__(self, host, port):
        self.P2Pserver = P2PListener(host, port, self)

    # Periodic stuff goes here:
    def tick(self):
        # Things to be executed every 5 secs
        if time.time() - self.LastPingTime > 5:
            self.LastPingTime = time.time()
            self.broadcastPing()

    def broadcastPing(self):
        for peer in self.Peers:
            self.Peers[peer].ping()

    # Join a node in the network.
    def join(self, addr, port=PORT):
        # TODO: Should check that the parameters are sane here.
        peer = P2PConnection()
        peer.P2Pmain = self
        peer.join(addr, port)
        self.Peers[self.ConnectionCount] = peer
        self.ConnectionCount = self.ConnectionCount + 1

    # Send a bye message to a selected peer.
    def sendBye(self, idx):
        if idx in self.Peers:
            self.Peers[idx].bye()
            return True
        return False

    # Perform a query to a specific node
    def sendQuery(self, idx, query, mid):
        if idx in self.Peers:
            self.Peers[idx].query(query, mid)
            return True
        return False

    # Search
    def search(self, query):
        mid = 0
        for idx in self.Peers:
            log('Querying peer {0}'.format(idx), 2)
            mid = self.Peers[idx].query(query, mid)

        # TODO change this 0 to IP.
        self.QueryMessages[mid] = [0, time.time()]

    # Remove peer from connection list.
    def leave(self, peer):
        idx = -1
        for i in self.Peers:
            if self.Peers[i] == peer:
                idx = i
        self.peerDelete(idx)
    
    # Remove peer from connection list.    
    def peerDelete(self, idx):
        if idx >= 0 and (idx in self.Peers):
            self.Peers[idx].close()
            del self.Peers[idx]

    # Handle an in coming connection.
    def acceptConnection(self,sock):
        peer = P2PConnection(sock)
        peer.P2Pmain = self
        self.Peers[self.ConnectionCount] = peer
        self.ConnectionCount = self.ConnectionCount + 1

    # Close all connections and exit.
    def shutDown(self):
        for i in self.Peers:
            self.Peers[i].bye()
            #self.Peers[i].close()
        self.P2Pserver.close()

    # Return a string representation of the current state.
    def __str__(self):
        str_con = ""
        str_q = ""
        for q in self.QueryMessages:
            str_q = str_q + "\t{0} ({1})\n".format(q[0],q[1]) 
        for i in self.Peers.keys():
            str_con = str_con + "{0}\t{1}\n".format(i,self.Peers[i].thisAsAString())
        return "Query messages:\n{2}\nPeer connections: {0}\n{1}\n".format(len(self.Peers), str_con, str_q)

# P2P Connections
class P2PConnection(asyncore.dispatcher):

    out_buffer = b''

    Joined = False
    JoinMessageId = 0
    JoinTime = 0
    LastPing = 0
    P2Pmain = None
    PeerName = ''

    def join(self, addr, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (addr, port) )
        message = JoinMessage(self.P2Pmain.HostIP)
        self.out_buffer = message.GetBytes()

        self.JoinMessageId = message.MessageId
        log("Attempting to join with Message:\n {0}".format(message),2)

        self.PeerName = "{0}:{1}".format(addr,port)

    def bye(self):
        msg = ByeMessage(self.getIP())
        self.out_buffer = msg.GetBytes()
        log("Sending Bye message to {0}".format(self.getpeername()[0]),1)
        log("{0}".format(msg), 3)

    def query(self, query, mid=0):
        msg = QueryMessage(self.getIP())
        msg.SetQuery(query)
        msg.MessageId = mid
        self.out_buffer = msg.GetBytes()
        log("Sending Query message to {0}".format(self.getpeername()[0]),1)
        log("{0}".format(msg),2)
        log("{0}".format(self.out_buffer),3)
        return msg.MessageId

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
        return (len(self.out_buffer) > 0)

    def ping(self):
        # Code to send Ping message goes here.
        if self.Joined:
            log("Send ping request (A).", 2)
            msg = PingMessage(self.getIP())
            self.out_buffer = msg.GetBytes()
            self.LastPing = time.time();

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
            elif msg.Request:
                rmsg = JoinMessage(self.P2Pmain.HostIP, msg.MessageId)
                self.out_buffer = rmsg.GetBytes()
                self.Joined = True
                self.JoinTime = time.time()
                log("Responded to join request @ {0}".format(msg.GetSenderIP()), 1)
            else:
                log("Message Ids don't match. {0} : {1} ".format(msg.MessageId, self.JoinMessageId), 2)

        elif msg.Type == P2PMessage.MSG_BYE:
            log("Got Bye message. Closing connection with {0}:{1}.".format(self.getpeername()[0], self.getpeername()[1]),1)
            self.P2Pmain.leave(self)

        elif msg.Type == P2PMessage.MSG_PING:
            log("Got Ping message from {0}:{1}.".format(self.getpeername()[0], self.getpeername()[1]), 1)
        elif msg.Type == P2PMessage.MSG_QUERY:
            # Check if we have already recieved a query with the same id.
                # Resend the query to all other peers.
                # Check local files and answer the query.
                # 
                # Ignore the query 
            log("Query Message\n{0}".format(msg), 2)
        else:
            log("Unhandled message from {0}:{1}".format(self.getpeername()[0], self.getpeername()[1]),1)

    #def handle_error(self):
    #    log("Can't connect to {0}.".format(self.PeerName), 1)
    #    self.P2Pmain.leave(self)

    def handle_close(self):
        log("Disconnected from {0}:{1}.".format(self.getpeername()[0], self.getpeername()[1]),1)
        self.P2Pmain.leave(self)

    def handle_connect(self):
        log("Connected to {0}:{1}.".format(self.getpeername()[0], self.getpeername()[1] ),1)

    def thisAsAString(self):
        if self.Joined:
            return "Peer connection to {0}:{1}\n\tAlive for {2}".format(self.getpeername()[0], self.getpeername()[1], time.time()-self.JoinTime,1)
        else:
            return "Attempting connection to {0}\n\tWaiting.".format(self.PeerName, 1)

    def __str__(self):
        return self.thisAsAString()

class P2PListener(asyncore.dispatcher):
    P2Pmain = None
    def __init__(self, host, port, p2pmain):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind((host, port))
        self.listen(5)
        self.P2Pmain = p2pmain

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            log('Incoming connection from {0}:{1}'.format(addr[0], addr[1]),1)
            self.P2Pmain.acceptConnection(sock)

    def writable(self):
        self.P2Pmain.tick()
        return True
        
            
