import time
import sys
import struct
import socket
from settings import *

# def log(s,l):
#     if l <= LOG_LVL:
#     	# \x1b
#         print("[{0}] {1}".format(time.ctime(),s))

def ipToNumber(ip):
    return struct.unpack("!I",socket.inet_aton(ip))

def numberToIp(n):
    return socket.inet_ntoa(struct.pack("!I", n))

# Copied from asyncore source
def compact_traceback():
    t, v, tb = sys.exc_info()
    tbinfo = []
    if not tb: # Must have a traceback
        raise AssertionError("traceback does not exist")
    while tb:
        tbinfo.append((
            tb.tb_frame.f_code.co_filename,
            tb.tb_frame.f_code.co_name,
            str(tb.tb_lineno)
            ))
        tb = tb.tb_next

    # just to be safe
    del tb

    file, function, line = tbinfo[-1]
    info = ' '.join(['[%s|%s|%s]\n' % x for x in tbinfo])
    return (file, function, line), t, v, info