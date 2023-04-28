from os import path
from threading import Thread
from queue import Queue
import time
import raft.config as config
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
		self.apply_queue = Queue()
		self.last_flushed_ind = -1

		Thread(target=self.flush_apply_queue).start()


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

	def get(self, key):
		self.logger.info("Fetching value for key: " + str(key))
		# error handling for get when key not found
		if key in self.db :
			return self.db.get(key)
		else :
			return config.KEY_NOT_FOUND

	def put(self, key, value, index):
		self.logger.info("Updating key: " + str(key) + ", value: " + str(value))
		for (k, v) in zip(key, value):
			self.db.update({k: v})
		
		self.apply_queue.put((key, value, index))

	def get_last_flushed_index(self):
		return self.last_flushed_ind

	def flush_apply_queue(self):
		self.logger.info("Flushing from apply queue to disk")
		
		backup_file = shelve.open(self.db_backup_file_path, 'c', writeback=True)
		batch_counter = 0
		start_time = time.time()

		while True:
			key, value, index = self.apply_queue.get()
			for (k, v) in zip(key, value):
				backup_file[str(k)] = v
				
			batch_counter += 1
			if batch_counter == config.FLUSH_APPLIED_BATCH_SIZE or time.time() - start_time >= config.FLUSH_APPLIED_TIMEOUT:
				backup_file.sync()

				# Update to the last index of the batch that was flushed 
				self.last_flushed_ind = index
				self.logger.info(f"Flush upto index {index} done.")

				self.logger.info(f"Flush batch done, batch count: {batch_counter}")
				batch_counter = 0
				start_time = time.time()



		
