from raft.election import elect
from raft.consensus import appendEntry

import grpc

STATE = {
	'CANDIDATE': 1,
	'FOLLOWER': 2,
	'LEADER': 3	
}

class Server:

	def __init__():
		self.store = dict()
		self.state = STATE['FOLLOWER']
		self.log = list()
		self.port = '50051'

	def recover():
		pass

	def listen():
		self.server = grpc.server(futures.ThreadPoolExecutor(max_worker=10))
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

if __name__ == '__main__':
	Server()