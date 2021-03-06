import struct
import asyncore
import time
import random
import binascii
import threading
import errno
import logging
from messages import *
from settings import *
from utils import *
 
logger = logging.getLogger('p2p')
 
# Main class. 
class P2PMain():
 
    # Class constructor
    def __init__(self, host, port, queue=None):
        self.P2Pserver = P2PListener(host, port, self)
        self.Peers = {}
        self.ConnectionCount = 0
        self.QueryMessages = {}
        self.LastPingTime = 0
        self.LastBPingTime = 0
        self.HostIP = struct.unpack("!I",socket.inet_aton(socket.gethostbyname(socket.gethostname())))[0]
        self.HostPort = port
        self.queue = queue
        self.lock = threading.RLock()
        self.status = ''
 
    # Handle messages from the queue.
    def handle_queue(self):
        if not self.queue == None:
            while not self.queue.empty():
                action = self.queue.get()
                if len(action) > 1:
 
                    # Join
                    if action[0] == 'j':
                        ipaddr = action[1].split(':')
                        nport = PORT
                        if len(ipaddr) == 2:
                            nport = int(ipaddr[1])
                        ipaddr = ipaddr[0]
                        self.join(ipaddr, nport)
 
                    # Bye
                    elif action[0] == 'b':
                        self.sendBye(int(action[1]))
 
                    # Search
                    elif action[0] == 's':
                        self.search(action[1])
 
                    # Quit
                    elif action[0] == 'q':
                        self.shutDown()
 
 
    # Get an object describing the status
    def getStatus(self):
        with self.lock:
            return self.status
 
    def updateStatus(self):
        with self.lock:
            self.status = { \
                'peers': {}, \
                'messages': {} \
                }
            for i in self.Peers:    
                self.status['peers'][str(i)] = self.Peers[i].thisAsAString()
            for q in self.QueryMessages:
                self.status['messages'][str(q)] = [self.QueryMessages[q]['from'], time.time()-self.QueryMessages[q]['time'], self.QueryMessages[q]['query']]
 
    # Get 5 random peers except peer.
    def getRndPeers(self, peer):
        retPeers = []
        rndPeerlist = random.sample(self.Peers, min(6, len(self.Peers)))
        for p in rndPeerlist:
            if not (self.Peers[p].getName() == peer) and not self.Peers[p].getPeerIp() == None:
                retPeers.append([self.Peers[p].getPeerIp(), self.Peers[p].PeerPort])
            if len(retPeers) == 5:
                return retPeers
        return retPeers
 
    # Check if a peer is already connected.
    def isConnected(self, addr, port):
        peername = "{0}:{1}".format(addr,port)
 
        for idx in self.Peers:
            if self.Peers[idx].getPeerName() == peername \
                or self.Peers[idx].getPeerListeningAddress() == peername:
                return True
        return False

    # Check if the given address and port is of 
    def isLocalListeningAddress(self, addr, port):
        if port == self.HostPort:
            for idx in self.Peers:
                if self.Peers[idx].getsockname()[0] == addr:
                    return True
        return False
 
    # # Send ping type B to a peer
    # def sendPing(self, idx):
    #     logger.info("Sending a Pong (B) message to {0}".format(idx))
    #     if idx in self.Peers:
    #         self.Peers[idx].ping('B')
    #         return True
    #     return False
 
    # Periodic stuff goes here:
    def tick(self):
        # Consule from the queue
        self.handle_queue()
        self.updateStatus()
 
        # Things to be executed every 5 secs
        if time.time() - self.LastPingTime > 5:
            self.LastPingTime = time.time()
            self.broadcastPing()
        # Things to be executed every 10 secs
        if time.time() - self.LastBPingTime > 10:
            self.LastBPingTime = time.time()
            self.broadcastPing('B')
 
            # Check connection to bootstrap and reconnect if necesary
            if not self.isConnected(BOOTSTRAP, PORT) and AUTOJOIN:
                self.join(BOOTSTRAP, PORT)
 
    # Broadcast a ping message to all peers
    def broadcastPing(self, ptype='A'):
        if len(self.Peers) > 0:
            logger.debug("Sending a broadcast ping type {0}.".format(ptype))
            for peer in self.Peers:
                self.Peers[peer].ping(ptype)
 
    # Forwarding a query message to all peers
    def forwardQueryMessage(self, msg):
        if msg.TTL <= 1:
            return
        logger.info("Sending a broadcast query from {0}".format(numberToIp(msg.SenderIP)))
        msg.TTL = msg.TTL - 1
        for i in self.Peers:
            self.Peers[i].sendMessage(msg)
 
    # Forwarding a qhit message to the given peer
    def forwardQueryHitMessage(self, msg, peername):
        if msg.TTL <= 1:
            return
        logger.info("Forwarding a query hit message from {0}".format(numberToIp(msg.SenderIP)))
        msg.TTL = msg.TTL - 1
        for i in self.Peers:
            if self.Peers[i].PeerName == peername:
                self.Peers[i].sendMessage(msg)
                return
 
    # Join a node in the network.
    def join(self, addr, port):
        # TODO: Should check that the parameters are sane here.
        logger.debug("Attempting to connect to peer {0}:{1}".format(addr,port))
        peer = P2PConnection()
        peer.P2Pmain = self
        self.Peers[self.ConnectionCount] = peer
        self.ConnectionCount = self.ConnectionCount + 1
        peer.join(addr, port)
         
 
    # Send a bye message to a selected peer.
    def sendBye(self, idx):
        logger.info("Sending a Bye message to {0}.".format(idx))
        if idx in self.Peers:
            self.Peers[idx].bye()
            return True
        return False
 
    # Search
    def search(self, query):
        # TODO do local search
        mid = 0
        for idx in self.Peers:
            if self.Peers[idx].Joined:
                logger.info('Querying peer {0}'.format(idx))
                mid = self.Peers[idx].query(query, mid)
 
        # TODO change this 0 to IP.
        if mid != 0:
            self.storeQueryInfo(mid, 0, query)
            logger.info("Searching for {0} with Message Id: {1}".format(query, mid))
 
    # Perform a search on the local data and return matches
    def getMatches(self, query):
        global LOCAL_ENTRIES
        matches = {}
        for key, info in LOCAL_ENTRIES.items():
            if query.strip() == key.strip():
                matches[info['id']] = info['value']
        return matches
 
    # Get info of the given query message id
    def getQueryInfo(self, mid):
        if mid in self.QueryMessages:
            return self.QueryMessages[mid]
        return None
 
    # Store the given query message to our message list
    def storeQueryInfo(self, mid, senderIp, query=''):
        self.QueryMessages[mid] = { \
            'from': senderIp, \
            'time': time.time(), \
            'query': query\
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
            logger.info("Peer {0} left. ".format(idx))
 
    # Handle an in coming connection.
    def acceptConnection(self,sock):
        peer = P2PConnection(sock)
        peer.P2Pmain = self
        self.Peers[self.ConnectionCount] = peer
        self.ConnectionCount = self.ConnectionCount + 1
        logger.info("New peer connection from {0}:{1}".format(sock.getpeername()[0], sock.getpeername()[1]))
 
    # Close all connections and exit.
    def shutDown(self):
        logger.info("Broadcasting bye message.")
        for i in self.Peers:
            self.Peers[i].bye()
            self.Peers[i].close()
        self.P2Pserver.close()
 
    # Return a string representation of the current state.
    def __str__(self):
        str_con = ""
        str_q = ""
        for q in self.QueryMessages.keys():
            str_q = str_q + "\t{2}\t{0}\t({1}s)\n".format(self.QueryMessages[q]['from'],time.time()-self.QueryMessages[q]['time'], q) 
        for i in self.Peers.keys():
            str_con = str_con + "{0}\t{1}\n".format(i,self.Peers[i].thisAsAString())
        return "Query messages:\n{2}\nPeer connections: {0}\n{1}\n".format(len(self.Peers), str_con, str_q)
 
# P2P Connections
class P2PConnection(asyncore.dispatcher):
 
    # Constructor
    def __init__(self, sock=None, tmap=None):
        asyncore.dispatcher.__init__(self,sock,tmap)
        self.Joined = False
        self.JoinMessageId = 0
        self.JoinTime = 0
        self.LastPing = 0
        self.P2Pmain = None
        self.out_buffer = b''
        self.PeerPort = 0
        self.PeerName = None
        if not sock == None:
            self.PeerName = self.getPeerName()
 
    # Join a node.
    def join(self, addr, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.connect( (addr, port) )
            message = JoinMessage(self.P2Pmain.HostIP, port=self.P2Pmain.HostPort)
            self.sendMessage(message)
            self.JoinMessageId = message.GetMessageId()
            self.PeerPort = port
            logger.debug("Attempting to join with Message:\n {0}".format(message))
            self.PeerName = "{0}:{1}".format(addr,port)
 
        except Exception, e:
            logger.error("Error connecting to: {0}:{1}".format(addr,port))
            self.handle_close()
 
    # Send a bye message to a node.
    def bye(self):
        if self.Joined:
            msg = ByeMessage(self.getIP(), port=self.P2Pmain.HostPort)
            self.sendMessage(msg)
            logger.info("Sending Bye message to {0}".format(self.getPeerName()))
            logger.debug("{0}".format(msg))
 
    def query(self, query, mid=0):
        if self.Joined:
            msg = QueryMessage(self.getIP(), port=self.P2Pmain.HostPort)
            msg.SetQuery(query)
            msg.MessageId = mid
            self.sendMessage(msg)
            logger.info("Sending Query message to {0}".format(self.getPeerName()))
            logger.debug("{0}".format(msg))
            return msg.GetMessageId()
        else:
            return 0
 
    def handle_write(self):
        sent = self.send(self.out_buffer)
        self.out_buffer = self.out_buffer[sent:]
 
    def getPeerIp(self):
        ip = None
        if self.connected:
            peername = self.getpeername()
            ip = struct.unpack("!I", socket.inet_aton(peername[0]))[0]
        return ip
  
    def getIP(self):
        ip = None
        if self.connected:
            sockname = self.getsockname()
            ip = struct.unpack("!I", socket.inet_aton(sockname[0]))[0]
        return ip
 
    def getPort(self):
        sockname = self.getsockname()
        port = sockname[1]
        return port

    def getPeerListeningAddress(self):
        if self.connected:
            try:
                return "{0}:{1}".format(self.getpeername()[0], self.PeerPort)
            except:
                return None
        else:
            return None
 
    def getPeerName(self):
        if self.connected:
            try:
                return "{0}:{1}".format(self.getpeername()[0], self.getpeername()[1])
            except:
                return self.PeerName
        else:
            return self.PeerName
 
    def getName(self):
        return "{0}:{1}".format(self.getsockname()[0], self.getsockname()[1])
 
    def writable(self):
        return (len(self.out_buffer) > 0)
 
    def ping(self, ptype='A'):
        if self.Joined:
            msg = PingMessage(self.getIP(), port=self.P2Pmain.HostPort)
            if ptype == 'A':
                logger.debug("Send Ping request (A) to {0}".format(self.getPeerName()))
 
            else:
                logger.debug("Send Ping request (B) to {0}".format(self.getPeerName()))
                msg.TTL = 5
                
            self.sendMessage(msg)
            self.LastPing = msg.MessageId;
 
    def pong(self, mid, pongType='A'):
        if self.Joined:
            msg = PongMessage(self.getIP(), port=self.P2Pmain.HostPort)
            msg.MessageId = mid
 
            if pongType == 'A':
                logger.debug("Send Pong message (A) to {0}".format(self.getPeerName()))
                 
            else:
                msg.SetEntries(self.P2Pmain.getRndPeers(self.getName()))
                logger.debug("Send Pong message (B) to {0}".format(self.getPeerName()))
 
            self.sendMessage(msg)
                 
 
    def sendMessage(self, msg):
        self.out_buffer += msg.GetBytes()
        logger.debug("Sending message: {0}".format(msg))
 
    def handle_read(self):
        receivedData = self.recv(8192)
        msgs = []
        while len(receivedData) > 0:
            msg, receivedData = ParseData(receivedData)
            if msg:
                msgs += [msg]
            else:
                logger.debug('Got trash from {0}'.format(self.getPeerName()))    

        for msg in msgs:
            logger.debug('Receiving: {0}'.format(msg))
            self.handle_message(msg)
 
    def handle_message(self, msg):
         
        self.PeerPort = msg.SenderPort
 
        # Join messages
        if msg.Type == P2PMessage.MSG_JOIN:
            if msg.MessageId == self.JoinMessageId and \
            not msg.Request:
                self.Joined = True
                logger.critical("Joined successfully @ {0}".format(self.getPeerName()))
                self.JoinTime = time.time()
            elif msg.Request:
                rmsg = JoinMessage(self.P2Pmain.HostIP, msg.MessageId, port=self.P2Pmain.HostPort)
                self.sendMessage(rmsg)
                self.Joined = True
                self.JoinTime = time.time() 
                logger.critical("Responded to join request @ {0}".format(self.getPeerName()))
            else:
                logger.info("Message Ids don't match. {0} : {1} @ {2} ".format(msg.MessageId, self.JoinMessageId, self.getPeerName()))
         
        # Bye messages
        elif msg.Type == P2PMessage.MSG_BYE:
            logger.info("Got Bye message. Closing connection with {0}.".format(self.getPeerName()))
            self.P2Pmain.leave(self)
         
        # Ping messages
        elif msg.Type == P2PMessage.MSG_PING:
            if msg.TTL > 1:
                logger.debug("Got Ping message (B) from {0}.".format(self.getPeerName()))
                self.pong(msg.MessageId, 'B')
            else:
                logger.debug("Got Ping message (A) from {0}.".format(self.getPeerName()))
                self.pong(msg.MessageId, 'A')
                 
        # Pong messages
        elif msg.Type == P2PMessage.MSG_PONG:
            if msg.MessageId == self.LastPing:
                if msg.PayloadLength > 0:
                    logger.info("Got Pong message (B) from {0}.".format(self.getPeerName()))
                    entries = msg.GetEntries()
                    if entries == None:
                        logger.info("No new peers from last Pong message.")
                    else:
                        logger.debug("Attempting to connect to {0} new peers: {1}".format(len(entries), entries))
                    
                        # Try to connect to other peers.     
                        for e in entries:
                            ip = socket.inet_ntoa(struct.pack("!I", e[0]))
                            port = e[1]
                            if (not self.P2Pmain.isConnected(ip, port)) and (not self.P2Pmain.isLocalListeningAddress(ip, port)):
                                self.P2Pmain.join(ip,port)
                            else:
                                logger.debug("Peer {0}:{1} is already connected.".format(ip,port))
                else:
                    logger.debug("Got Pong message (A) from {0}.".format(self.getPeerName()))
            else:
                logger.debug("Ignored a Pong message.")
        elif msg.Type == P2PMessage.MSG_QUERY:
            logger.debug("Query Message\n{0}".format(msg))
 
            # Check if we have already recieved a query with the same id.
            mid = msg.MessageId
            queryInfo = self.P2Pmain.getQueryInfo(mid)
            if queryInfo == None and msg.PayloadLength > 0:
                senderIP = msg.SenderIP
                query = msg.Payload.partition('\x00')[0]
                # store in the list of query messages
                self.P2Pmain.storeQueryInfo(mid, self.PeerName, query)
                # Resend the query to all other peers.
                self.P2Pmain.forwardQueryMessage(msg)
                # Check local files and answer the query.
                matches = self.P2Pmain.getMatches(query)
                if len(matches) > 0:
                    logger.critical("QHIT match for key '{1}': {0}".format(matches, query))
                    qhitMsg = QueryHitMessage(self.getIP(), mid, port=self.P2Pmain.HostPort)
                    qhitMsg.SetEntries(matches)
                    self.sendMessage(qhitMsg)
            else:
                # Ignore the query 
                logger.info("Message ID existed -> drop the query message")
        elif msg.Type == P2PMessage.MSG_QHIT:
            logger.debug("QueryHit Message\n{0}".format(msg))
 
            mid = msg.MessageId
            queryInfo = self.P2Pmain.getQueryInfo(mid)
            if queryInfo != None:
                # display the result if the query is from this node
                if queryInfo['from'] == 0:
                    entries = msg.GetEntries()
                    logger.critical("Result from: {0}".format(socket.inet_ntoa(struct.pack('!I',msg.SenderIP))))
                    for eid, val in entries.items():
                        logger.critical("ID: {0} - Value: {1}".format(eid, val))
                # otherwise, forward it back based on our history 
                else:
                    self.P2Pmain.forwardQueryHitMessage(msg, queryInfo['from'])
 
            else:
                logger.info("Not found matched query message -> drop the message")
        else:
            logger.debug("Unhandled message from {0} type {1}.".format(self.getPeerName(), msg.Type))
 
    # Need to define how to handle errors here and fail safely.
    def handle_error(self):
        nil, t, v, tbinfo = compact_traceback()
        if v[0] == errno.ECONNREFUSED:
            logger.info("Connection refused from {0}.".format(self.PeerName))
            self.handle_close()
        elif v[0] == errno.ETIMEDOUT:
            logger.info("Connection timed out to {0}.".format(self.PeerName))
            self.handle_close()
        elif v[0] == errno.ENETDOWN:
            logger.info("Network is down {0}.".format(self.PeerName))
            self.handle_close()
        else:
            logger.error("Error\n\t{0}\n\t{1}\n\t{2}".format(t, v, tbinfo))
            self.handle_close()
 
    def handle_close(self):
        logger.info("Disconnected from {0}.".format(self.getPeerName()))
        self.P2Pmain.leave(self)
 
    def handle_connect(self):
        logger.info("Connected to {0}.".format(self.getPeerName()))
 
    def thisAsAString(self):
        if self.Joined:
            return "{0}\tPeer connected.\n\tAlive for {1}".format(self.getPeerName(), time.time()-self.JoinTime)
        elif self.connected:
            return "{0}\tAttempting connection.\n\tWaiting for Join response.".format(self.getPeerName())
        else:
            return "{0}\tAttempting connection.\n\tWaiting for TCP handshake.".format(self.getPeerName())
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
            logger.info('Incoming connection from {0}:{1}'.format(addr[0], addr[1]))
            self.P2Pmain.acceptConnection(sock)
 
    def writable(self):
        self.P2Pmain.tick()
        return asyncore.dispatcher.writable(self)
