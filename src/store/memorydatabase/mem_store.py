class MemoryStore:

	def __init__(self):
		self.db = dict()

	def get(self, key):
		return self.db.get(key, None)

	def put(self, key, value):
		self.db.update({key: value})