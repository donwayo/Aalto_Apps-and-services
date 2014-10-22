from settings import *
from utils import *
import struct
import socket
import binascii
import hashlib
import logging
import random

logger = logging.getLogger('p2p')

# Base clas for P2P Messages
class P2PMessage():

    MSG_PING = 0x00
    MSG_PONG = 0x01
    MSG_BYE  = 0x02
    MSG_JOIN = 0x03
    MSG_QUERY= 0x80
    MSG_QHIT = 0x81

    MessageHeader = struct.Struct('!BBBBHHII')

    def __init__(self):
        self.Version = 0x01
        self.TTL = 5
        self.Type = 0
        self.PayloadLength = 0
        self.SenderIP = 0
        self.MessageId = 0
        self.SenderPort = PORT
        self.Payload = ''

    def LoadHeader(self, data):
        self.Version = data[0]
        self.TTL = data[1]
        self.Type = data[2]
        self.SenderPort = data[4]
        self.PayloadLength = data[5]
        self.SenderIP = data[6]
        self.MessageId = data[7]

    def GetSenderIP(self):
        return socket.inet_ntoa(struct.pack('!I',self.SenderIP))

    def GetMessageId(self):
        if self.MessageId == 0:
            self.MessageId = self.GetNewId()
        return self.MessageId

    def __str__(self):

        strMsg = "Message type {3}:\n\t"
        strMsg += "TTL:{0}\n\t"
        strMsg += "SenderPort:{1}\n\t"
        strMsg += "SenderIP:{2}\n\t"
        strMsg += "MessageId:{4}\n\t"
        strMsg += "PayloadLength:{5}\n\t"
        strMsg += "Payload:{6}\n"

        return strMsg.format(\
            self.TTL, \
            self.SenderPort, \
            self.GetSenderIP(), \
            self.Type, \
            self.GetMessageId(), \
            self.PayloadLength,\
            binascii.hexlify(self.Payload))

    def GetNewId(self):
        return struct.unpack('!I', hashlib.md5("{0}{1}".format(self.SenderIP, time.time()+random.random())).digest()[:4])[0]
    
    def GetHeaderBytes(self):
        MessageIdString = str(self.SenderPort) + str(self.SenderPort) +  str(time.time())
        
        return self.MessageHeader.pack( \
            self.Version, \
            self.TTL, \
            self.Type, \
            0x00, \
            self.SenderPort, \
            self.PayloadLength, \
            self.SenderIP, \
            self.GetMessageId() )

    def GetBytes(self):
        if self.PayloadLength == 0:
            return self.GetHeaderBytes()
        else:
            return self.GetHeaderBytes() + self.Payload

def ParseData(data):
    msg = False

    if len(data) > 15:
        header = P2PMessage.MessageHeader.unpack(data[:16])
        payload = data[16:]

        # Check that the header is valid.
        if header[0] == 1 and header[1] > 0 and header[1] <= 5 and header[5] == len(payload):
            if header[2] == P2PMessage.MSG_JOIN:
                msg = JoinMessage(0)
                msg.FromData(header, payload)
            elif header[2] == P2PMessage.MSG_PING:
                msg = PingMessage(0)
                msg.LoadHeader(header)
            elif header[2] == P2PMessage.MSG_QHIT:
                msg = QueryHitMessage(0, 0)
                msg.FromData(header, payload)
            elif header[2] == P2PMessage.MSG_QUERY:
                msg = QueryMessage(0)
                msg.FromData(header, payload)
            elif header[2] == P2PMessage.MSG_PONG:
                msg = PongMessage(0)
                msg.FromData(header, payload)
            elif header[2] == P2PMessage.MSG_BYE:
                msg = ByeMessage(0)
                msg.LoadHeader(header)
            else:
                msg = P2PMessage()
                msg.LoadHeader(header)
        else:
            logger.info("Trash: Header version: {0} TTL: {1} Payload: {2} - {3} Type: {4}".format(header[0], header[1], header[5], len(payload), header[2]))
    return msg

class ByeMessage(P2PMessage):
    def __init__(self, ipaddr):
        P2PMessage.__init__(self)

        self.TTL = 1
        self.Type = P2PMessage.MSG_BYE
        self.SenderIP = ipaddr

class PingMessage(P2PMessage):
    def __init__(self, ipaddr, ttl = 1):
        P2PMessage.__init__(self)

        self.TTL = ttl
        self.Type = P2PMessage.MSG_PING
        self.SenderIP = ipaddr
        self.PayloadLength = 0

    def GetBytes(self):
        return self.GetHeaderBytes()

    def isTypeA(self):
        return self.TTL == 1

class PongMessage(P2PMessage):
    
    PongEntry = struct.Struct('!IHH')

    def __init__(self, ipaddr):
        P2PMessage.__init__(self)
        self.TTL = 1
        self.Type = P2PMessage.MSG_PONG
        self.SenderIP = ipaddr
        self.Entries = None

    def AddEntry(self, ip, port):
        self.Entries.append([ip, port])

    def GetEntries(self):
        return self.Entries

    def SetEntries(self, entries):
        self.Entries = entries

    def ParseEntries(self, data, e_size):
        self.Entries = []
        if e_size == (len(data) / self.PongEntry.size):
            # Read up to 5 entries.
            for e in xrange(min(e_size, 5)):
                offset = e * self.PongEntry.size
                entry = self.PongEntry.unpack(data[offset:offset+self.PongEntry.size])
                self.AddEntry(entry[0], entry[1])
        else:
            logger.info("PongMessage reported payload size doesn't match: {0}:{1}".format(e_size, len(payload[2:])/8))


    def FromData(self, header, payload):
        if len(header) == 8:
            self.LoadHeader(header)

            if self.PayloadLength == len(payload) \
            and self.PayloadLength >= 4 \
            and (self.PayloadLength - 4) % 8 == 0:
                e_size = struct.unpack('!HH', payload[:4])[0]
                self.ParseEntries(payload[4:], e_size)
   
    def GetBytes(self):
        # Build entry payload.
        self.Payload = b""

        if not self.Entries == None: 
            self.Payload = struct.pack('!HH', len(self.Entries), 0)
            for e in self.Entries:
                self.Payload += self.PongEntry.pack(e[0], e[1], 0)

            self.PayloadLength = len(self.Payload)

        return self.GetHeaderBytes() + self.Payload

class JoinMessage(P2PMessage):
    def __init__(self, ipaddr, msg_id = -1):
        P2PMessage.__init__(self)

        self.TTL = 1
        self.Type = P2PMessage.MSG_JOIN
        self.SenderIP = ipaddr

        if msg_id == -1:
            self.Request = True
            self.Payload = b''
        else:
            self.Request = False
            self.Payload = b'\x02\x00'
            self.MessageId = msg_id
            
        self.PayloadLength = len(self.Payload)

    def FromData(self, data, payload=b''):
        if len(data) == 8:
            self.LoadHeader(data)
            self.Payload = payload
            if self.PayloadLength == 2:
                self.Request = False
            else:
                self.Request = True

class QueryMessage(P2PMessage):
    def __init__(self, ipaddr):
        P2PMessage.__init__(self)

        self.TTL = DEFAULT_TTL
        self.Type = P2PMessage.MSG_QUERY
        self.SenderIP = ipaddr
        self.Payload = b''

    def SetQuery(self, query):
        self.Payload = query.partition('\x00')[0] + '\x00'
        self.PayloadLength = len(self.Payload)

    def FromData(self, header, payload):
        if len(header) == 8:
            self.LoadHeader(header)
            self.SetQuery(payload)

class QueryHitMessage(P2PMessage):
    EntryPairStruct = struct.Struct('!HHI')
    EntrySizeStruct = struct.Struct('!HH')

    def __init__(self, ipaddr, mid):
        P2PMessage.__init__(self)

        self.TTL = DEFAULT_TTL
        self.Type = P2PMessage.MSG_QHIT
        self.SenderIP = ipaddr
        self.MessageId = mid
        self.Payload = b''

    def SetEntries(self, entries):
        if entries == None or len(entries) == 0:
            return
        entrySize = len(entries)
        self.Payload = QueryHitMessage.EntrySizeStruct.pack(entrySize, 0x00)

        for eid, val in entries.items():
            entryStr = QueryHitMessage.EntryPairStruct.pack( \
                    eid, \
                    0x00, \
                    val \
            )
            self.Payload += entryStr
        self.PayloadLength = len(self.Payload)
        self.entries = entries

    def GetEntries(self):
        tmp = self.Payload
        entrySize = QueryHitMessage.EntrySizeStruct.unpack(tmp[:4])[0]
        tmp = tmp[4:]
        entries = {}
        for i in xrange(entrySize):
            entryData = QueryHitMessage.EntryPairStruct.unpack(tmp[:8])
            entries[entryData[0]] = entryData[2]
            tmp = tmp[8:]

        return entries

    def FromData(self, header, payload):
        if len(header) == 8:
            self.LoadHeader(header)
            self.Payload = payload
