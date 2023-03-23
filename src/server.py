from raft.election import elect
from raft.consensus import appendEntry

STATE = {
	'CANDIDATE': 1,
	'FOLLOWER': 2,
	'LEADER': 3	
}

store = {}
state = STATE['FOLLOWER']
log = []

def recover():
	pass

def listen():
	pass

def handleGet(key):
	pass

def handlePut(key, value):
	pass

def insertToLog(message):
	pass

def commitLog(index):
	pass

def accept(message):
	pass