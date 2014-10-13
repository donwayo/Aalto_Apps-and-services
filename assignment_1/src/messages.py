from settings import *
import struct
import socket
import hashlib

class P2PMessage():
    Version = 0x01
    TTL = 5
    Type = 0
    PayloadLength = 0
    SenderIP = 0
    MessageId = 0
    SenderPort = PORT

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
        self.SenderPort = data[4]
        self.PayloadLength = data[5]
        self.SenderIP = data[6]
        self.MessageId = data[7]

    def GetSenderIP(self):
        return socket.inet_ntoa(struct.pack('!I',self.SenderIP))

    def __str__(self):
        return "Message type {3}:\n\tTTL:{0}\n\tSenderPort:{1}\n\tSenderIP:{2}\n\tMessageId:{4}\n\tPayloadLength:{5}\n".format(self.TTL, self.SenderPort, self.GetSenderIP(), self.Type, self.MessageId, self.PayloadLength)

    def GetHeaderBytes(self):
        MessageIdString = str(self.SenderPort) + str(self.SenderPort) +  str(time.time());
        
        if self.MessageId == 0:
            self.MessageId = struct.unpack('!I', hashlib.md5("{0}{1}".format(self.SenderIP, time.time())).digest()[:4])[0]
        
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
        return self.GetHeaderBytes()

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
            #elif header[2] == P2PMessage.MSG_PING:
            #    print('unimplemented\n')
            #elif header[2] == P2PMessage.MSG_QHIT:
            #    print('unimplemented\n')
            #elif header[2] == P2PMessage.MSG_QUERY:
            #    print('unimplemented\n')
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

        if(ttl > 1):
            # Do type B
            log('Ping response shoud send neighbors.')
        else:
            self.PayloadLength = 0

    def GetBytes(self):
        if self.PayloadLength == 0:
            return self.GetHeaderBytes()
        else:
            log('Not implemented!')
            return b'\x00'

class JoinMessage(P2PMessage):
    Payload = b'\x02\x00'
    Request = 1
    def __init__(self, ipaddr, msg_id=-1):
        self.TTL = 1
        self.Type = P2PMessage.MSG_JOIN
        self.SenderIP = ipaddr
        self.Request = (msg_id == -1)

    def FromData(self, data, payload=b''):
        if len(data) == 8:
            self.LoadHeader(data)

            if payload == self.Payload:
                self.Request = False
                self.PayloadLength = 2

    def GetBytes(self):
        if self.Request:
            return self.GetHeaderBytes()
        else:
            return self.GetHeaderBytes() + self.Payload
