'''
TODO:
1. Handle key not present in table scenario (get)
2. Implement persistent in-memory state (use shelve to persist in-memory)
3. Implement recovery logic (load from shelve)
'''
class MemoryStore:

	def __init__(self, logger):
		self.logger = logger
		self.logger.info("Initializing Memory store")

		self.db = dict()

	def recover(self):
		pass

	def get(self, key):
		self.logger.info("Fetching value for key: " + str(key))
		return self.db.get(key, None)

	def put(self, key, value):
		self.logger.info("Updating key: " + str(key) + ", value: " + str(value))
		self.db.update({key: value})