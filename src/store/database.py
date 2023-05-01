from store.memorydatabase.mem_store import MemoryStore

'''
TODO:
1. [IN_PROGRESS] Get should be surrounded by try catch statements. Throw a key error if key is missing
'''

class Database:

	def __init__(self, server_id, logger, type = 'memory'):
		self.db = MemoryStore(server_id, logger)
		
	def get(self, key):
		return self.db.get(key)

	def put(self, key, value, index):
		self.db.put(key, value, index)

	def clear_backup(self):
		self.db.clear_backup()

	def get_last_flushed_index(self):
		return self.db.get_last_flushed_index()
