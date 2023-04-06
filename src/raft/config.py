from os import getenv

STATE = {
	'CANDIDATE': 1,
	'FOLLOWER': 2,
	'LEADER': 3	
}

MIN_TIMEOUT = int(getenv('MIN_TIMEOUT', 50000))
MAX_TIMEOUT =  int(getenv('MAX_TIMEOUT', 100000))

REQUESTS_TIMEOUT = 50
HB_TIME = int(getenv('HB_TIME', 50))
MAX_LOG_WAIT = int(getenv('MAX_LOG_WAIT', 150))

RESPONSE_CODE_OK = 200
RESPONSE_CODE_REJECT = 500

# RPC timeout in seconds
RPC_TIMEOUT = 5

def chunks(l, n):
    n = max(1, n)
    return (l[i:i+n] for i in range(0, len(l), n))