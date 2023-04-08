from collections import deque
from threading import Lock, Thread

from store.memorydatabase.mem_store import MemoryStore
from store.sqlitedb.sqlite_store import SqliteStore
import shelve

'''
TODO:
1. Get should be surrounded by try catch statements. Throw a key error if key is missing
'''

class Database:

	def __init__(self, server_id, logger, type = 'memory'):
		if type == 'memory':
			self.db = MemoryStore(logger)
		else:
			store_name = server_id + ".db"
			self.db = SqliteStore(store_name, logger)

		self.lock = Lock()
		
	def get(self, key):
		return self.db.get(key)

	def put(self, key, value):
		self.db.put(key, value)
