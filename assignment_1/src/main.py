import asyncore
import socket
import sys
import logging
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
                logger.info('Searching for "{0}"'.format(query))
                p2p.search(query)

            # Join network is 'j' followed by 'b' for the bootstrap node or an IP address.
            elif receivedData[0] == 'j' and len(receivedData) > 1:
                
                if receivedData[1] == 'b':
                    self.send('Joining bootstrap node.\n')
                    p2p.join(BOOTSTRAP, PORT)
                else:
                    ipaddr = receivedData[1:]
                    ipaddr = ipaddr.split(':')
                    nport = PORT
                    if len(ipaddr) == 2:
                        nport = int(ipaddr[1])
                    ipaddr = ipaddr[0]
                    p2p.join(ipaddr, nport)
                    self.send('Joining {0}:{1}\n'.format(ipaddr, nport))
            
            # Send Bye
            elif receivedData[0] == 'b' and len(receivedData) > 1:
                cId = int(receivedData[1:])
                logger.info('Got request to send Bye message to connection {0}'.format(cId))
                p2p.sendBye(cId)

            # Display information
            elif receivedData[0] == 'i':
                if len(receivedData[1:]) > 0:
                    self.send("O: {0}\n".format(eval(receivedData[1:])))
                else:
                    self.send("{0}\n".format(p2p))

            # Change loglvl (doesn't work!)
            elif receivedData[0] == 'l' and len(receivedData) > 1:
                loglvl = int(receivedData[1:]) * 10
                logging.getLogger().setLevel(loglvl)
                self.send("Changed loglvl to {0}\n".format(loglvl))

            # Send ping
            elif receivedData[0] == 'p' and len(receivedData) > 1:
                cId = int(receivedData[1:])
                logger.info('Got request to send Ping message (B) to connection {0}'.format(cId))
                p2p.sendPing(cId)

            # Close down.
            elif receivedData[0] == 'q':
                logger.info("Closing down.")
                self.send('Bye\n')
                p2p.shutDown()
                self.close();


# P2P Server
serverPort = PORT
if len(sys.argv) > 1:
    serverPort = int(sys.argv[1])

# init logging
logLevel = logging.INFO
logger = logging.getLogger('p2p')
logger.setLevel(logLevel)

# create console handler and set level to debug
formatter = logging.Formatter("%(asctime)s: %(message)s", "- %I:%M:%S %p")
ch = logging.StreamHandler()
ch.setLevel(logLevel)
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

p2p = P2PMain('localhost', serverPort)
cmdline = CmdlineClient(sys.stdin)
asyncore.loop(10)
