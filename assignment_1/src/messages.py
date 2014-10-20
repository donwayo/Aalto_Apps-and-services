from settings import *
import struct
import socket
import binascii
import hashlib

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
        return "Message type {3}:\n\tTTL:{0}\n\tSenderPort:{1}\n\tSenderIP:{2}\n\tMessageId:{4}\n\tPayloadLength:{5}\n".format(self.TTL, self.SenderPort, self.GetSenderIP(), self.Type, self.GetMessageId(), self.PayloadLength)

    def GetNewId(self):
        return struct.unpack('!I', hashlib.md5("{0}{1}".format(self.SenderIP, time.time())).digest()[:4])[0]
    
    def GetHeaderBytes(self):
        MessageIdString = str(self.SenderPort) + str(self.SenderPort) +  str(time.time());
        
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
            #elif header[2] == P2PMessage.MSG_PONG:
            #    print('unimplemented\n')
            elif header[2] == P2PMessage.MSG_BYE:
                msg = ByeMessage(0)
                msg.LoadHeader(header)
            else:
                msg = P2PMessage()
                msg.LoadHeader(header)
    
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


class JoinMessage(P2PMessage):
    #Request = True
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
            
        self.PayloadLength = len(self.Payload)

    def FromData(self, data, payload=b''):
        if len(data) == 8:
            self.LoadHeader(data)
            if payload == self.Payload:
                self.PayloadLength = 2
                self.Request = False
            else:
                self.Request = True
                self.PayloadLength = 0

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
