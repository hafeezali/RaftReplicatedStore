from os import getenv


ELECTION_TIMEOUT = 10
HEARTBEAT_TIMEOUT = 10

STATE = {
	'CANDIDATE': 1,
	'FOLLOWER': 2,
	'LEADER': 3	
}

LOW_TIMEOUT = int(getenv('LOW_TIMEOUT', 150))
HIGH_TIMEOUT =  int(getenv('HIGH_TIMEOUT', 300))

REQUESTS_TIMEOUT = 50
HB_TIME = int(getenv('HB_TIME', 50))
MAX_LOG_WAIT = int(getenv('MAX_LOG_WAIT', 150))



def chunks(l, n):
    n = max(1, n)
    return (l[i:i+n] for i in range(0, len(l), n))