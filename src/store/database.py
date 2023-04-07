from collections import deque
from threading import Lock, Thread

from store.memorydatabase.mem_store import MemoryStore
# from store.rocksdatabase.rocks_store import RocksStore
import shelve

class Database:

	def __init__(self, server_id, type = 'memory'):
		if type == 'memory':
			self.db = MemoryStore()
		# else:
		# 	store_name = server_id + ".db"
		# 	self.db = RocksStore(store_name)

		self.lock = Lock()
		
	def get(self, key):
		return self.db.get(key)
		## Should we add a try catch?? What do we return if the key is not present
		## Does it throw a key error?

	def put(self, key, value):
		self.db.put(key, value)

		## Should this return true/false????
