import time

PORT = 10001
BOOTSTRAP = '130.233.43.41'
LOG_LVL = 2
DEFAULT_TTL = 5

LOCAL_ENTRIES = {
	1: "How I met your mother",
	2: "Friends",
	3: "Games of thrones",
	4: "The walking dead"
}

def log(s,l):
    if l <= LOG_LVL:
    	# \x1b
        print("[{0}] {1}".format(time.ctime(),s))
