from os import path

import shelve

class MemoryStore:

	def __init__(self, server_id, logger):
		self.logger = logger
		self.logger.info("Initializing Memory store")

		self.backup_dir = 'store'
		self.db_backup_file_name = server_id + '_mem'
		self.db_backup_file_path = path.join(self.backup_dir, self.db_backup_file_name)

		self.db = dict()
		self.recover()

	def clear_backup(self):
		self.logger.info("Deleting disk backup")

		self.db.clear()
		self.backup_file = shelve.open(self.db_backup_file_path, 'c', writeback=True)
		self.backup_file.clear()
		self.backup_file.close()

		self.logger.info("Deletion of disk backup done")

	def recover(self):
		self.logger.info("Recovering in-memory state")
		backup_file = shelve.open(self.db_backup_file_path, 'c', writeback=True)

		try:
			self.db.clear()
			for key in backup_file:
				self.logger.info("Found key: " + str(key) + ", value: " + str(backup_file[key]))
				self.db[int(key)] = int(backup_file[key])
		except Exception as e:
			self.logger.info("Exception in recover method when reading persisted in-memory db")

		backup_file.close()
		self.logger.info("Recover done")

	def flush(self, key, value):
		self.logger.info("Flushing to disk, key: " + str(key) + ", value: " + str(value))
		
		backup_file = shelve.open(self.db_backup_file_path, 'c', writeback=True)
		backup_file[str(key)] = value
		backup_file.close()

		self.logger.info("Flush done")

	def get(self, key):
		self.logger.info("Fetching value for key: " + str(key))
		return self.db.get(key, None)

	def put(self, key, value):
		self.logger.info("Updating key: " + str(key) + ", value: " + str(value))
		for (k, v) in zip(key, value):
			self.db.update({k: v})
			self.flush(k, v)