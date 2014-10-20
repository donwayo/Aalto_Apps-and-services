import asyncore
import socket
import sys
from settings import *
from utils import *
from p2p import *


# Command line control
class CmdlineClient(asyncore.file_dispatcher):
    def __init__(self, file):
        asyncore.file_dispatcher.__init__(self, file)

    def handle_read(self):
        receivedData = self.recv(1024)
        receivedData = receivedData.rstrip()
        if len(receivedData) > 0: 
            
            # Search command is 's' followed by the search string.
            if receivedData[0] == 's':
                query = receivedData[1:]
                log('Searching for "{0}"'.format(query), 1)
                p2p.search(query)

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
            # Change loglvl
            elif receivedData[0] == 'l' and len(receivedData) > 1:
                LOG_LVL = int(receivedData[1:])

            # Send ping
            elif receivedData[0] == 'p' and len(receivedData) > 1:
                cId = int(receivedData[1:])
                log('Got request to send Ping message (B) to connection {0}'.format(cId), 1)
                p2p.sendPing(cId)

            # Close down.
            elif receivedData[0] == 'q':
                log("Closing down.",1)
                self.send('Bye\n')
                p2p.shutDown()
                self.close();


# P2P Server
p2p = P2PMain('localhost', PORT)
cmdline = CmdlineClient(sys.stdin)
asyncore.loop(60)