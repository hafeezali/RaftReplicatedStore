from collections import deque
from threading import Lock, Thread

from store.memorydatabase.mem_store import MemoryStore
# from store.sqlitedb.sqlite_store import SqliteStore
import shelve

'''
TODO:
1. Get should be surrounded by try catch statements. Throw a key error if key is missing
'''

class Database:

	def __init__(self, server_id, logger, type = 'memory'):

		if type == 'memory':
			self.db = MemoryStore(server_id, logger)
		# removing the sql part
		# else:
		# 	self.db = SqliteStore(server_id, logger)

		self.lock = Lock()
		
	def get(self, key):
		return self.db.get(key)

	def put(self, key, value, index):
		self.db.put(key, value, index)

	def clear_backup(self):
		self.db.clear_backup()

	def get_last_flushed_index(self):
		self.db.get_last_flushed_index()
