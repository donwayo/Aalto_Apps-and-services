import struct
import asyncore
import time
import random
import binascii
import errno
import logging
from messages import *
from settings import *
from utils import *

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
        self.queue = queue

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
                        self.bye(int(action[1]))

                    # Search
                    elif action[0] == 's':
                        self.search(action[1])

                    # Quit
                    elif action[0] == 'q':
                        self.shutDown()

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
            if self.Peers[idx].getPeerName() == peername:
                return True
        return False

    # Send ping type B to a peer
    def sendPing(self, idx):
        logging.info("Sending a Pong (B) message to {0}".format(idx))
        if idx in self.Peers:
            self.Peers[idx].ping('B')
            return True
        return False

    # Periodic stuff goes here:
    def tick(self):
        # Consule from the queue
        self.handle_queue()

        # Things to be executed every 5 secs
        if time.time() - self.LastPingTime > 5:
            self.LastPingTime = time.time()
            self.broadcastPing()
        # Things to be executed every 10 secs
        if time.time() - self.LastBPingTime > 10:
            self.LastBPingTime = time.time()
            self.broadcastPing('B')

            # Check connection to bootstrap and reconnect if necesary
            if not self.isConnected(BOOTSTRAP, PORT):
                self.join(BOOTSTRAP, PORT)
            # Check command line and reconnect
            # if not cmdline.connected:
            #    cmdline = CmdlineClient(sys.stdin)

    # Broadcast a ping message to all peers
    def broadcastPing(self, ptype='A'):
        if len(self.Peers) > 0:
            logging.debug("Sending a broadcast ping type {0}.".format(ptype))
            for peer in self.Peers:
                self.Peers[peer].ping(ptype)

    # Forwarding a query message to all peers
    def forwardQueryMessage(self, msg):
        if msg.TTL <= 1:
            return
        logging.info("Sending a broadcast query from {0}".format(numberToIp(msg.SenderIP)))
        msg.TTL = msg.TTL - 1
        for i in self.Peers:
            self.Peers[i].sendMessage(msg)

    # Forwarding a qhit message to the given peer
    def forwardQueryHitMessage(self, msg, peername):
        if msg.TTL <= 1:
            return
        logging.info("Forwarding a query hit message from {0}".format(numberToIp(msg.SenderIP)))
        msg.TTL = msg.TTL - 1
        for i in self.Peers:
            if self.Peers[i].PeerName == peername:
                self.Peers[i].sendMessage(msg)
                return

    # Join a node in the network.
    def join(self, addr, port):
        # TODO: Should check that the parameters are sane here.
        logging.debug("Attempting to connect to peer {0}:{1}".format(addr,port))
        peer = P2PConnection()
        peer.P2Pmain = self
        peer.join(addr, port)
        self.Peers[self.ConnectionCount] = peer
        self.ConnectionCount = self.ConnectionCount + 1

    # Send a bye message to a selected peer.
    def sendBye(self, idx):
        logging.info("Sending a Bye message to {0}.".format(idx))
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
                logging.info('Querying peer {0}'.format(idx))
                mid = self.Peers[idx].query(query, mid)

        # TODO change this 0 to IP.
        if mid != 0:
            self.storeQueryInfo(mid, 0)
            logging.info("Searching for {0} with Message Id: {1}".format(query, mid))

    # Perform a search on the local data and return matches
    def getMatches(self, query):
        global LOCAL_ENTRIES
        matches = {}
        query = query.partition('\x00')[0]
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
            logging.info("Peer {0} left. ".format(idx))

    # Handle an in coming connection.
    def acceptConnection(self,sock):
        peer = P2PConnection(sock)
        peer.P2Pmain = self
        self.Peers[self.ConnectionCount] = peer
        self.ConnectionCount = self.ConnectionCount + 1
        logging.info("New peer connection from {0}:{1}".format(sock.getpeername()[0], sock.getpeername()[1]))

    # Close all connections and exit.
    def shutDown(self):
        logging.info("Broadcasting bye message.")
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
        self.connect( (addr, port) )
        message = JoinMessage(self.P2Pmain.HostIP)
        self.sendMessage(message)
        self.PeerPort = port
        self.JoinMessageId = message.GetMessageId()
        logging.debug("Attempting to join with Message:\n {0}".format(message))

        self.PeerName = "{0}:{1}".format(addr,port)

    # Send a bye message to a node.
    def bye(self):
        if self.Joined:
            msg = ByeMessage(self.getIP())
            self.sendMessage(msg)
            logging.info("Sending Bye message to {0}".format(self.getPeerName()))
            logging.debug("{0}".format(msg))

    def query(self, query, mid=0):
        if self.Joined:
            msg = QueryMessage(self.getIP())
            msg.SetQuery(query)
            msg.MessageId = mid
            self.sendMessage(msg)
            logging.info("Sending Query message to {0}".format(self.getPeerName()))
            logging.debug("{0}".format(msg))
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
            msg = PingMessage(self.getIP())
            if ptype == 'A':
                logging.debug("Send Ping request (A) to {0}".format(self.getPeerName()))

            else:
                logging.debug("Send Ping request (B) to {0}".format(self.getPeerName()))
                msg.TTL = 5
            
            self.sendMessage(msg)
            self.LastPing = msg.MessageId;

    def pong(self, mid, pongType='A'):
        if self.Joined:
            msg = PongMessage(self.getIP())
            msg.MessageId = mid

            if pongType == 'A':
                logging.debug("Send Pong message (A) to {0}".format(self.getPeerName()))
                
            else:
                msg.SetEntries(self.P2Pmain.getRndPeers(self.getName()))
                logging.debug("Send Pong message (B) to {0}".format(self.getPeerName()))

            self.sendMessage(msg)
                

    def sendMessage(self, msg):
        self.out_buffer = msg.GetBytes()
        logging.debug("Sending message: {0}".format(msg))

    def handle_read(self):
        receivedData = self.recv(8192)
        msg = ParseData(receivedData)
        if msg:
            logging.debug('Receiving: {0}'.format(msg))
            self.handle_message(msg)
            
        elif len(receivedData) > 0:
            logging.debug('Got trash from {0}'.format(self.getPeerName()))

    def handle_message(self, msg):
        
        self.PeerPort = msg.SenderPort

        # Join messages
        if msg.Type == P2PMessage.MSG_JOIN:
            if msg.MessageId == self.JoinMessageId and \
            not msg.Request:
                self.Joined = True
                logging.info("Joined successfully @ {0}".format(self.getPeerName()))
                self.JoinTime = time.time()
            elif msg.Request:
                rmsg = JoinMessage(self.P2Pmain.HostIP, msg.MessageId)
                self.sendMessage(rmsg)
                self.Joined = True
                self.JoinTime = time.time() 
                logging.info("Responded to join request @ {0}".format(self.getPeerName()))
            else:
                logging.info("Message Ids don't match. {0} : {1} ".format(msg.MessageId, self.JoinMessageId))
        
        # Bye messages
        elif msg.Type == P2PMessage.MSG_BYE:
            logging.info("Got Bye message. Closing connection with {0}.".format(self.getPeerName()))
            self.P2Pmain.leave(self)
        
        # Ping messages
        elif msg.Type == P2PMessage.MSG_PING:
            if msg.TTL > 1:
                logging.debug("Got Ping message (B) from {0}.".format(self.getPeerName()))
                self.pong(msg.MessageId, 'B')
            else:
                logging.debug("Got Ping message (A) from {0}.".format(self.getPeerName()))
                self.pong(msg.MessageId, 'A')
                
        # Pong messages
        elif msg.Type == P2PMessage.MSG_PONG:
            if msg.MessageId == self.LastPing:
                if msg.PayloadLength > 0:
                    logging.debug("Got Pong message (B) from {0}.".format(self.getPeerName()))
                    entries = msg.GetEntries()
                    if entries == None:
                        logging.debug("No new peers from last Pong message.")
                    else:
                        logging.debug("Attempting to connect to {0} new peers.".format(len(entries)))
                   
                        # Try to connect to other peers.     
                        for e in entries:
                            ip = socket.inet_ntoa(struct.pack("!I", e[0]))
                            port = e[1]
                            if not self.P2Pmain.isConnected(ip, port):
                                self.P2Pmain.join(ip,port)
                            else:
                                logging.debug("Peer {0}:{1} is already connected.".format(ip,port))
                else:
                    logging.debug("Got Pong message (A) from {0}.".format(self.getPeerName()))
            else:
                logging.debug("Ignored a Pong message.")
        elif msg.Type == P2PMessage.MSG_QUERY:
            logging.debug("Query Message\n{0}".format(msg))

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
                logging.info("Matches: {0}".format(matches))
                if len(matches) > 0:
                    qhitMsg = QueryHitMessage(self.getIP(), mid)
                    qhitMsg.SetEntries(matches)
                    self.sendMessage(qhitMsg)
            else:
                # Ignore the query 
                logging.info("Message ID existed -> drop the message")
        elif msg.Type == P2PMessage.MSG_QHIT:
            logging.debug("QueryHit Message\n{0}".format(msg))

            mid = msg.MessageId
            queryInfo = self.P2Pmain.getQueryInfo(mid)
            if queryInfo != None:
                # display the result if the query is from this node
                if queryInfo['from'] == 0:
                    entries = msg.GetEntries()
                    logging.info("Result from: {0}".format(socket.inet_ntoa(struct.pack('!I',msg.SenderIP))))
                    for eid, val in entries.items():
                        logging.info("ID: {0} - Value: {1}".format(eid, val))
                # otherwise, forward it back based on our history 
                else:
                    self.P2Pmain.forwardQueryHitMessage(msg, queryInfo['from'])

            else:
                logging.info("Not found matched query message -> drop the message")
        else:
            logging.debug("Unhandled message from {0} type {1}.".format(self.getPeerName(), msg.Type))

    # Need to define how to handle errors here and fail safely.
    def handle_error(self):
        nil, t, v, tbinfo = compact_traceback()
        if v[0] == errno.ECONNREFUSED:
            logging.info("Connection refused from {0}.".format(self.PeerName))
            self.handle_close()
        elif v[0] == errno.ETIMEDOUT:
            logging.info("Connection timed out to {0}.".format(self.PeerName))
            self.handle_close()
        elif v[0] == errno.ENETDOWN:
            logging.info("Network is down {0}.".format(self.PeerName))
            self.handle_close()
        else:
            logging.error("Error\n\t{0}\n\t{1}\n\t{2}".format(t, v, tbinfo))
            self.handle_close()

    def handle_close(self):
        logging.info("Disconnected from {0}.".format(self.getPeerName()))
        self.P2Pmain.leave(self)

    def handle_connect(self):
        logging.info("Connected to {0}.".format(self.getPeerName()))

    def thisAsAString(self):
        if self.Joined:
            return "Peer connection to {0}\n\tAlive for {1}".format(self.getPeerName(), time.time()-self.JoinTime)
        elif self.connected:
            return "Attempting connection to {0}\n\tWaiting for Join response.".format(self.getPeerName())
        else:
            return "Attempting connection to {0}\n\tWaiting for TCP handshake.".format(self.getPeerName())
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
            logging.info('Incoming connection from {0}:{1}'.format(addr[0], addr[1]))
            self.P2Pmain.acceptConnection(sock)

    def writable(self):
        self.P2Pmain.tick()
        return asyncore.dispatcher.writable(self)
        
            
