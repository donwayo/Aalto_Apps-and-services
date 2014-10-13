import time

PORT = 10001
BOOTSTRAP = '130.233.43.41'
LOG_LVL = 1

def log(s,l):
    if l <= LOG_LVL:
        print("[{0}] {1}".format(time.ctime(),s))
