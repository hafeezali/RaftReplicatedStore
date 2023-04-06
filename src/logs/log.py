import sys

sys.path.append('../')

from os import path, getenv, makedirs
from threading import Lock, Thread

import time
import shelve

from raft.config import STATE

'''
Log layer responsible for
1. Interaction with the store
2. Appending, committing, and applying log entries (put requests)
3. Persisting and receovering node state
4. Central state manager for 
	- log
	- log_idx
	- last_commit_idx
	- last_applied_idx
	- term
	- status
	- voted_for
	- leader_id
	- last_applied_command_per_client

TODO:
1. All persistent state can be collated into one dict. Easier persistence and recovery
2. clear_log_backup() can live inside clear()
3. When do we close the files opened using shelve?
4. We probably want the locks to become more finer for some performance gains
5. Looks like shelve not working
'''

class Log:

	'''
	server_id: Used to name the persistent log and config files. Also used whenever setting oneself as leader
	database: instance of mem_store or rocks_store used by this server
	'''
	def __init__(self, server_id, database, logger):
		
		self.server_id = server_id
		self.database = database
		self.logger = logger

		self.backup_dir = 'backup'
		log_backup_file_name = server_id + '_log.dbm'
		config_backup_file_name = server_id + '_config.dbm'

		self.log_path = path.join(self.backup_dir, log_backup_file_name)
		self.config_path = path.join(self.backup_dir, config_backup_file_name)

		self.check_backup_dir()

		self.log = list()
		self.commit_done = list()

		# persistent state
		self.last_commit_idx = -1
		self.log_idx = -1
		self.last_applied_idx = -1
		self.term = 0
		self.status = STATE['FOLLOWER']
		self.voted_for = {
			'term': -1,
			'server_id': None
		}
		self.leader_id = None
		self.last_applied_command_per_client = dict()

		# used to check if a config has changed so we can persist it
		self.config_change = dict()

		# central lock for all configs that can be accessed by multiple threads
		self.lock = Lock()

		self.recover()

		# This thread keeps applying log entries to state and persisting applied logs (Write Ahead-like)
		Thread(target=self.apply).start()
		# This thread keeps checking for changes to server state and persisting them
		Thread(target=self.flush_config).start()

	def check_backup_dir(self):
		self.logger.info("Check backup dir")

		if not path.exists(self.backup_dir):
			makedirs('backup')

	'''
	In a scenario we are clearing the log in memory, we want to clear it on the persistent store as well
	IMP! This is only to be called from log.clear()
	'''
	def clear_log_backup(self):
		self.logger.info("Clear log backup")

		self.log_file['log'] = self.log
		self.config_file['last_commit_idx'] = self.last_commit_idx
		self.config_file['log_idx'] = self.log_idx
		self.config_file['last_applied_idx'] = self.last_applied_idx

	'''
	On node restart, we want to recover node state and pickup from where we left off. This involves recovering log apart from server state
	'''
	def recover(self):
		self.logger.info("Recover")

		self.log_file = shelve.open(self.log_path, 'c', writeback=True)
		self.config_file = shelve.open(self.config_path, 'c', writeback=True)

		try:
			if self.log_file['log']:
				self.log = self.log_file['log']
		except KeyError as e:
			self.logger.info("KeyError ")
			self.log_file['log'] = self.log

		try:
			if self.config_file['last_commit_idx']:
				self.last_commit_idx = self.config_file['last_commit_idx']
			if self.config_file['log_idx']:
				self.log_idx = self.config_file['log_idx']
			if self.config_file['last_applied_idx']:
				self.last_applied_idx = self.config_file['last_applied_idx']
			if self.config_file['term']:
				self.term = self.config_file['term']
			if self.config_file['status']:
				self.status = self.config_file['status']
			if self.config_file['voted_for']:
				self.voted_for = self.config_file['voted_for']
			if self.config_file['leader_id']:
				self.leader_id = self.config_file['leader_id']
			if self.config_file['last_applied_command_per_client']:
				self.last_applied_command_per_client = self.config_file['last_applied_command_per_client']
		except KeyError as e:
			self.logger.info("KeyError")
			self.config_file['last_commit_idx'] = self.last_commit_idx
			self.config_file['log_idx'] = self.log_idx
			self.config_file['last_applied_idx'] = self.last_applied_idx
			self.config_file['term'] = self.term
			self.config_file['status'] = self.status
			self.config_file['voted_for'] = self.voted_for
			self.config_file['leader_id'] = self.leader_id
			self.config_file['last_applied_command_per_client'] = self.last_applied_command_per_client

	'''
	Flush entry at index to disk
	'''
	def flush(self, index):
		self.logger.info("Flush")

		self.log_file['log'].append(self.log[index])
		self.log_file.sync()

	'''
	If any config has changed, persist that change. Dedicated thread created to achieve this
	'''
	def flush_config(self):
		self.logger.info("Flush config")

		while True:
			with self.lock:
				for key in self.config_change:
					if self.config_change[key] is True:
						self.logger.info(key + " changed")
						self.config_file[key] = getattr(self, key)
						self.config_change[key] = False
			self.config_file.sync()
			time.sleep(100/1000)

	'''
	This will only be called by the leader node. This commits log entry at index. Entries can be committed out of order in leader
	'''
	def commit(self, index):
		self.logger.info("Commit")

		with self.lock:
			self.commit_done[index] = True
			while self.last_commit_idx < index and self.commit_done[self.last_commit_idx+1]:
				self.last_commit_idx += 1
			self.config_change['last_commit_idx'] = True

	def get_log_idx(self):
		self.logger.info("Get log idx")

		with self.lock:
			return self.log_idx

	def get_term(self):
		self.logger.info("Get term")

		with self.lock:
			return self.term

	def update_term(self, term):
		self.logger.info("Update term")

		with self.lock:
			self.term = term
		self.config_change['term'] = True

	'''
	This will be called by follower nodes. This marks all logs till index as ready to be committed
	'''
	def commit_upto(self, index):
		self.logger.info("Commit upto")

		with self.lock:
			while self.last_commit_idx < index:
				self.commit_done[self.last_commit_idx] = True
				self.last_commit_idx += 1
		self.config_change['last_commit_idx'] = True

	'''
	This will be called by thread periodically to apply log entries to the database
	'''
	def apply(self):
		self.logger.info("Apply called")

		while True:
			c_idx = self.last_commit_idx
			idx = self.last_applied_idx + 1
			while idx <= c_idx:
				flush_res = self.flush(idx)
				if flush_res:
					entry = self.get(idx)
					self.database.put(entry.key, entry.value)
					idx = idx + 1
					self.last_applied_idx = self.last_applied_idx + 1
					self.last_applied_command_per_client.update({entry.client_id, idx})
					self.config_change['last_applied_idx'] = True
					self.config_change['last_applied_command_per_client'] = True
				else:
					break
			time.sleep(100/1000)

	def get(self, index):
		self.logger.info("Get")

		return self.log[index]

	def append(self, entry):
		self.logger.info("Append")

		with self.lock:
			self.log.append(entry)
			self.commit_done.append(False)
			self.log_idx += 1
			self.config_change['log_idx'] = True
			return self.log_idx

	def insert_at(self, index, entry):
		self.logger.info("Insert at")

		with self.lock:
			if index <= self.log_idx:
				self.log[index] = entry
				self.commit_done[index] = False
				return index
			else:
				self.log.append(entry)
				self.commit_done.append(False)
				self.log_idx += 1
				self.config_change['log_idx'] = True
				return self.log_idx

	def is_applied(self, index):
		self.logger.info("Is applied")

		return index <= self.last_applied_idx

	def get_leader(self):
		self.logger.info("Get leader")

		with self.lock:
			return self.leader_id

	def update_leader(self, leader):
		self.logger.info("Update leader")

		with self.lock:
			self.leader_id = leader
		self.config_change['leader_id'] = True

	def update_status(self, status):
		self.logger.info("Update status")

		with self.lock:
			self.status = status
		self.config_change['status'] = True

	def get_status(self):
		self.logger.info("Get status")

		return self.status
	
	def set_self_candidate(self):
		self.logger.info("Set self candidate")

		with self.lock:
			self.term += 1
			self.status = STATE['CANDIDATE']
		self.config_change['status'] = True
		self.config_change['term'] = True

	def set_self_leader(self):
		self.logger.info("Set self leader")

		with self.lock:
			self.status = STATE['LEADER']
			self.leader_id = self.server_id
		self.config_change['status'] = True
		self.config_change['leader_id'] = True

	def revert_to_follower(self, new_term, new_leader_id):
		self.logger.info("Revert to follower")

		with self.lock:
			if self.status == STATE['CANDIDATE'] or self.status == STATE['LEADER']:
				self.status = STATE['FOLLOWER']
			self.term = new_term
			self.leader_id = new_leader_id
		self.config_change['status'] = True
		self.config_change['leader_id'] = True
		self.config_change['term'] = True

	def get_voted_for(self):
		self.logger.info("Get vorted for")

		return self.voted_for['term'], self.voted_for['server_id']
	
	def cast_vote(self, candidate_term, candidate_id):
		self.logger.info("Cast vote")

		with self.lock:
			self.term = candidate_term
			self.voted_for['term'] = candidate_id
			self.voted_for['server_id'] = candidate_id
		self.config_change['term'] = True
		self.config_change['voted_for'] = True
			
	def get_last_committed_sequence_for(self, client_id):
		self.logger.info("Get last committed sequence for")

		with self.lock:
			return self.last_applied_command_per_client[client_id]

	def clear(self):
		self.logger.info("clear")

		with self.lock:
			self.log.clear()
			self.last_commit_idx = -1
			self.log_idx = -1
			self.last_applied_idx = -1
			self.clear_log_backup()
			
