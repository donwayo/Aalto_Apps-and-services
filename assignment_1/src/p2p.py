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

    # Broadcast a ping message to all peers
    def broadcastPing(self):
        if len(self.Peers) > 0:
            log("Sending a broadcast ping.", 1)
            for peer in self.Peers:
                self.Peers[peer].ping()

    # Forwarding a query message to all peers
    def forwardQueryMessage(self, msg):
        if msg.TTL <= 1:
            return
        log("Sending a broadcast query.", 1)
        msg.TTL = msg.TTL - 1
        for i in self.Peers:
            self.Peers[i].sendMessage(msg)

    # Forwarding a qhit message to the given peer
    def forwardQueryHitMessage(self, msg, peername):
        if msg.TTL <= 1:
            return
        log("Forwarding a query hit message.", 1)
        msg.TTL = msg.TTL - 1
        for i in self.Peers:
            if self.Peers[i].PeerName == peername:
                self.Peers[i].sendMessage(msg)
                return

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
        log("Sending a broadcast Bye.", 1)
        if idx in self.Peers:
            self.Peers[idx].bye()
            return True
        return False

    # # Perform a query to a specific node
    # def sendQuery(self, idx, query, mid):
    #     if idx in self.Peers:
    #         self.Peers[idx].query(query, mid)
    #         return True
    #     return False

    # Search
    def search(self, query):
        # TODO do local search
        mid = 0
        for idx in self.Peers:
            log('Querying peer {0}'.format(idx), 2)
            mid = self.Peers[idx].query(query, mid)

        # TODO change this 0 to IP.
        self.storeQueryInfo(mid, 0)
        log("Searching for {0} with Message Id: {1}".format(query, mid), 1)

    # Perform a search on the local data and return matches
    def getMatches(self, query):
        matches = {}
        for eid, val in LOCAL_ENTRIES.items():
            if query in val:
                matches[eid] = val
        return matches

    # Get info of the given query message id
    def getQueryInfo(self, mid):
        if mid in self.QueryMessages:
            return self.QueryMessages[mid]
        return None

    # Store the given query message to our message list
    def storeQueryInfo(self, mid, senderIp):
        self.QueryMessages[mid] = { \
            'from': senderIp, \
            'time': time.time() \
        }

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
            log("Peer {0} left. ".format(idx), 1)

    # Handle an in coming connection.
    def acceptConnection(self,sock):
        peer = P2PConnection(sock)
        peer.P2Pmain = self
        self.Peers[self.ConnectionCount] = peer
        self.ConnectionCount = self.ConnectionCount + 1
        log("New peer connection from {0}:{1}".format(sock.getpeername()[0], sock.getpeername()[1]),1)

    # Close all connections and exit.
    def shutDown(self):
        log("Broadcasting bye message.", 1)
        for i in self.Peers:
            self.Peers[i].bye()
            self.Peers[i].close()
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

    def join(self, addr, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (addr, port) )
        message = JoinMessage(self.P2Pmain.HostIP)
        self.sendMessage(message)

        self.JoinMessageId = message.GetMessageId()
        log("Attempting to join with Message:\n {0}".format(message), 3)

        self.PeerName = "{0}:{1}".format(addr,port)

    def bye(self):
        if self.Joined:
            msg = ByeMessage(self.getIP())
            self.sendMessage(msg)
            log("Sending Bye message to {0}".format(self.getPeerName()), 2)
            log("{0}".format(msg), 3)

    def query(self, query, mid=0):
        if self.Joined:
            msg = QueryMessage(self.getIP())
            msg.SetQuery(query)
            msg.MessageId = mid
            self.sendMessage(msg)
            log("Sending Query message to {0}".format(self.getPeerName()), 2)
            log("{0}".format(msg), 3)
            return msg.GetMessageId()

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

    def getPeerName(self):
        return "{0}:{1}".format(self.getpeername()[0],self.getpeername()[1])

    def writable(self):
        return (len(self.out_buffer) > 0)

    def ping(self):
        if self.Joined:
            log("Send Ping request (A).", 2)
            msg = PingMessage(self.getIP())
            self.sendMessage(msg)
            self.LastPing = time.time();

    def sendMessage(self, msg):
        log("Sending message: {0}".format(msg), 3)
        self.out_buffer = msg.GetBytes()

    def handle_read(self):
        receivedData = self.recv(8192)
        msg = ParseData(receivedData)
        if msg:
            self.handle_message(msg)
            log('{0}'.format(msg), 3)
        elif len(receivedData) > 0:
            log('Got trash', 2)

    def handle_message(self, msg):
        # Join messages
        if msg.Type == P2PMessage.MSG_JOIN:
            if msg.MessageId == self.JoinMessageId and \
            not msg.Request:
                self.Joined = True
                log("Joined successfully @ {0}".format(self.getPeerName()), 2)
                self.JoinTime = time.time()
            elif msg.Request:
                rmsg = JoinMessage(self.P2Pmain.HostIP, msg.MessageId)
                self.sendMessage(rmsg)
                self.Joined = True
                self.JoinTime = time.time() 
                log("Responded to join request @ {0}".format(self.getPeerName()), 2)
            else:
                log("Message Ids don't match. {0} : {1} ".format(msg.MessageId, self.JoinMessageId), 2)
        # Bye messages
        elif msg.Type == P2PMessage.MSG_BYE:
            log("Got Bye message. Closing connection with {0}.".format(self.getPeerName()), 2)
            self.P2Pmain.leave(self)
        # Ping messages
        elif msg.Type == P2PMessage.MSG_PING:
            if msg.TTL > 1:
                log("Got Ping message (B) from {0}.".format(self.getPeerName()), 2)
            else:
                log("Got Ping message (A) from {0}.".format(self.getPeerName()), 2)
        # Pong messages
        elif msg.Type == P2PMessage.MSG_PONG:
            if msg.PayloadLength > 0:
                log("Got Pong message (B) from {0}.".format(self.getPeerName()), 2)
            else:
                log("Got Pong message (A) from {0}.".format(self.getPeerName()), 2)
        elif msg.Type == P2PMessage.MSG_QUERY:
            log("Query Message\n{0}".format(msg), 2)

            # Check if we have already recieved a query with the same id.
            mid = msg.MessageId
            queryInfo = self.P2Pmain.getQueryInfo(mid)
            if queryInfo == None and msg.PayloadLength > 0:
                senderIP = msg.SenderIP
                query = msg.Payload
                # store in the list of query messages
                self.P2Pmain.storeQueryInfo(mid, self.PeerName)
                # Resend the query to all other peers.
                self.P2Pmain.forwardQueryMessage(msg)
                # Check local files and answer the query.
                matches = self.P2Pmain.getMatches(query)
                if len(matches) > 0:
                    qhitMsg = QueryHitMessage(self.getIP(), mid)
                    qhitMsg.SetEntries(matches)
                    self.sendMessage(qhitMsg)
            else:
                # Ignore the query 
                log("Message ID existed -> drop the message", 2)
        elif msg.Type == P2PMessage.MSG_QHIT:
            log("QueryHit Message\n{0}".format(msg), 3)

            mid = msg.MessageId
            queryInfo = self.P2Pmain.getQueryInfo(mid)
            if queryInfo != None:
                # display the result if the query is from this node
                if queryInfo['from'] == 0:
                    entries = msg.GetEntries()
                    log("Result from: {0}\n".format(msg.SenderIP), 2)
                    for eid, val in entries.items():
                        log("ID: {0} - Value: {1}".format(eid, val), 2)
                # otherwise, forward it back based on our history 
                else:
                    self.P2Pmain.forwardQueryHitMessage(msg, queryInfo['from'])

            else:
                log("Not found matched query message -> drop the message", 2)
        else:
            log("Unhandled message from {0} type {1}.".format(self.getPeerName(), msg.Type), 2)

    # Need to define how to handle errors here and fail safely.
    #def handle_error(self):
    #    log("Can't connect to {0}.".format(self.PeerName), 1)
    #    self.P2Pmain.leave(self)

    def handle_close(self):
        log("Disconnected from {0}.".format(self.getPeerName()), 2)
        self.P2Pmain.leave(self)

    def handle_connect(self):
        log("Connected to {0}.".format(self.getPeerName()), 2)

    def thisAsAString(self):
        if self.Joined:
            return "Peer connection to {0}\n\tAlive for {1}".format(self.getPeerName(), time.time()-self.JoinTime)
        else:
            return "Attempting connection to {0}\n\tWaiting.".format(self.getPeerName())

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
            log('Incoming connection from {0}:{1}'.format(addr[0], addr[1]), 1)
            self.P2Pmain.acceptConnection(sock)

    def writable(self):
        self.P2Pmain.tick()
        return asyncore.dispatcher.writable(self)
        
            
