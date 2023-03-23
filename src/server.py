from raft.election import elect
from raft.consensus import 

STATE = {
	'CANDIDATE': 1,
	'FOLLOWER': 2,
	'LEADER': 3	
}

store = {}
state = STATE['CANDIDATE']
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