from collections import deque
from threading import Lock, Thread

import memorydatabase.mem_store
import rocksdatabase.rocks_store
import shelve

class Database:

	def __init__(self, type = 'memory', server_id):
		if type == 'memory':
			self.db = MemoryStore()
		else:
			store_name = server_id + ".db"
			self.db = RocksStore(store_name)

		self.lock = Lock()
		
	def get(self, key):
		return self.db.get(key)

	def put(self, key, value):
		self.db.put(key, value)
