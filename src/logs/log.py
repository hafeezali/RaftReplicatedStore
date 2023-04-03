from os import path
from collections import deque

# must have some sort of locking I think? when updating index???
class Log:

	def __init__(self, server_id, database):
		backup_name = server_id + '.log'
		self.backup_path = path.join('backup', backup_name)
		self.queue = deque()
		self.last_commit_idx = 0
		self.log_idx = 0
		self.last_applied_idx = 0
		self.term = 0
		self.database = database
		recover()

	def recover(self):
		pass

	def append(self, entry):
		pass

	def commit(self, index):
		pass

	def apply(self, index):
		pass

	def get(self, index):
		pass

	def clear(self):
		pass