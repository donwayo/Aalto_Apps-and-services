from settings import *
import struct
import socket
import binascii
import hashlib

class P2PMessage():
    Version = 0x01
    TTL = 5
    Type = 0
    PayloadLength = 0
    SenderIP = 0
    MessageId = 0
    SenderPort = PORT
    Payload = ''

    MSG_PING = 0x00
    MSG_PONG = 0x01
    MSG_BYE  = 0x02
    MSG_JOIN = 0x03
    MSG_QUERY= 0x80
    MSG_QHIT = 0x81

    MessageHeader = struct.Struct('!BBBBHHII')

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

    def __str__(self):
        return "Message type {3}:\n\tTTL:{0}\n\tSenderPort:{1}\n\tSenderIP:{2}\n\tMessageId:{4}\n\tPayloadLength:{5}\n".format(self.TTL, self.SenderPort, self.GetSenderIP(), self.Type, self.MessageId, self.PayloadLength)

    def GetNewId(self):
        return struct.unpack('!I', hashlib.md5("{0}{1}".format(self.SenderIP, time.time())).digest()[:4])[0]
    
    def GetHeaderBytes(self):
        MessageIdString = str(self.SenderPort) + str(self.SenderPort) +  str(time.time());
        
        if self.MessageId == 0:
            self.MessageId = self.GetNewId()
        
        return self.MessageHeader.pack( \
            self.Version, \
            self.TTL, \
            self.Type, \
            0x00, \
            self.SenderPort, \
            self.PayloadLength, \
            self.SenderIP, \
            self.MessageId )

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
        if header[0] == 1 and header[1] > 0 and header[1] <= 5:
            if header[2] == P2PMessage.MSG_JOIN:
                msg = JoinMessage(0)
                msg.FromData(header, payload)
            elif header[2] == P2PMessage.MSG_PING:
                msg = PingMessage(0)
                msg.LoadHeader(header)
            #elif header[2] == P2PMessage.MSG_QHIT:
            #    print('unimplemented\n')
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
        self.TTL = 1
        self.Type = P2PMessage.MSG_BYE
        self.SenderIP = ipaddr

class PingMessage(P2PMessage):
    def __init__(self, ipaddr, ttl = 1):
        self.TTL = ttl
        self.Type = P2PMessage.MSG_PING
        self.SenderIP = ipaddr
        self.PayloadLength = 0

    def GetBytes(self):
        return self.GetHeaderBytes()

    def isTypeA(self):
        return self.TTL == 1



class JoinMessage(P2PMessage):
    Payload = b'\x02\x00'
    Request = True
    def __init__(self, ipaddr, msg_id = -1):
        self.TTL = 1
        self.Type = P2PMessage.MSG_JOIN
        self.SenderIP = ipaddr

        if msg_id == -1:
            self.Request = True
            self.PayloadLength = 0
        else:
            self.Request = False
            self.PayloadLength = 2

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
    Payload = b''
    def __init__(self, ipaddr):
        self.TTL = DEFAULT_TTL
        self.Type = P2PMessage.MSG_QUERY
        self.SenderIP = ipaddr

    def SetQuery(self, payload):
        self.Payload = payload.partition('\x00')[0] + '\x00'
        self.PayloadLength = len(self.Payload)

    def FromData(self, data, payload):
        if len(data) >= 8:
            self.LoadHeader(data)
            self.SetQuery(payload)
