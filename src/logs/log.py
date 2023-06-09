import sys

sys.path.append('../')

from os import path, getenv, makedirs
from threading import Lock, Thread

import time
import shelve

from raft.config import STATE
from raft.config import SERVER_SLEEP_TIME

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
1. All persistent state can be collated into one dict. Easier persistence and recovery (but cant implement finer locks)
2. clear_log_backup() can live inside clear()
3. Shelve is having some weird behavior when appending the first element to the list - investigate this later (fixed by using a dict instead of list for log)
4. We probably want the locks to become more finer for some performance gains
5. Can ignore committed logs from disk on recover. Can remove committed logs from log dict
'''

class Log:

	'''
	server_id: Used to name the persistent log and config files. Also used whenever setting oneself as leader
	database: instance of mem_store or rocks_store used by this server
	logger: common logger used across node
	'''
	def __init__(self, server_id, database, logger):
		
		self.server_id = server_id
		self.database = database
		self.logger = logger

		self.backup_dir = 'backup'
		log_backup_file_name = server_id + '_log'
		config_backup_file_name = server_id + '_config'

		self.log_path = path.join(self.backup_dir, log_backup_file_name)
		self.config_path = path.join(self.backup_dir, config_backup_file_name)

		self.check_backup_dir()

		self.log = dict()

		# persistent state
		self.last_commit_idx = -1
		self.log_idx = -1
		self.last_applied_idx = -1
		self.term = 0

		self.status = STATE['FOLLOWER']
		self.voted_for = {
			'term': 0,
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

		self.logger.info("Check backup dir done")

	'''
	In a scenario we are clearing the log in memory, we want to clear it on the persistent store as well
	IMP! This is only to be called from log.clear()
	'''
	def clear_log_backup(self):
		self.logger.info("Clear log backup")

		log_file = shelve.open(self.log_path, 'c', writeback=True)
		config_file = shelve.open(self.config_path, 'c', writeback=True)

		log_file.clear()

		config_file['last_commit_idx'] = self.last_commit_idx
		config_file['log_idx'] = self.log_idx
		config_file['last_applied_idx'] = self.last_applied_idx

		log_file.close()
		config_file.close()

		self.database.clear_backup()

		self.logger.info("Clear log backup done")

	'''
	On node restart, we want to recover node state and pickup from where we left off. This involves recovering log apart from server state
	'''
	def recover(self):
		self.logger.info("Recover")

		log_file = shelve.open(self.log_path, 'c', writeback=True)
		config_file = shelve.open(self.config_path, 'c', writeback=True)

		try:
			self.log.clear()
			for key in log_file:
				self.log[int(key)] = log_file[key]
		except Exception as e:
			self.logger.info("Exception in recover method when reading log")

		try:
			if config_file['last_commit_idx']:
				self.last_commit_idx = config_file['last_commit_idx']
			if config_file['log_idx']:
				self.log_idx = config_file['log_idx']
			if config_file['last_applied_idx']:
				self.last_applied_idx = config_file['last_applied_idx']
			if config_file['term']:
				self.term = config_file['term']
			if config_file['status']:
				self.status = config_file['status']
			if config_file['voted_for']:
				self.voted_for = config_file['voted_for']
			if config_file['leader_id']:
				self.leader_id = config_file['leader_id']
			if config_file['last_applied_command_per_client']:
				self.last_applied_command_per_client = config_file['last_applied_command_per_client']
		except KeyError as e:
			self.logger.info("KeyError")
			config_file['last_commit_idx'] = self.last_commit_idx
			config_file['log_idx'] = self.log_idx
			config_file['last_applied_idx'] = self.last_applied_idx
			config_file['term'] = self.term
			config_file['status'] = self.status
			config_file['voted_for'] = self.voted_for
			config_file['leader_id'] = self.leader_id
			config_file['last_applied_command_per_client'] = self.last_applied_command_per_client

		log_file.close()
		config_file.close()

		# remove this
		self.debug_print_log()
		self.debug_print_config()

		self.logger.info("Recover done")

	def debug_check_log_file(self, log_file):
		if not log_file:
			print("Error: Failed to create log file")
		else:
			# Inspect the contents of the file
			print("Log file contents:")
			for key, value in log_file.items():
				print(f"{key}: {value}")

	'''
	Flush entry at index to disk
	'''
	def flush(self, index):
		self.logger.info("Flush for index: " + str(index))

		try:
			log_file = shelve.open(self.log_path, 'c', writeback=True)
			# self.debug_check_log_file(log_file)
			self.logger.info("Trying to persist: " + str(self.log[index]))
			log_file[str(index)] = self.log[index]
			self.logger.info("now im here")
			log_file.close()
		except Exception as e:
			self.logger.info(f'Exception, details: {e}') 
			return False

		self.logger.info("Flush done")
		return True

	'''
	If any config has changed, persist that change. Dedicated thread created to achieve this
	'''
	def flush_config(self):
		# self.logger.info("Flush config")

		while True:
			config_file = shelve.open(self.config_path, 'c', writeback=True)
			with self.lock:
				for key in self.config_change:
					if self.config_change[key] is True:
						self.logger.info("Inside flush config: " + str(key) + " changed. Persisting change")
						config_file[key] = getattr(self, key)
						self.config_change[key] = False

			config_file.close()
			time.sleep(SERVER_SLEEP_TIME)

	'''
	This will only be called by the leader node. This commits log entry at index. Entries can be committed out of order in leader
	'''
	def commit(self, index):
		self.logger.info("Commit for index: " + str(index))

		with self.lock:
			self.log[index]['commit_done'] = True
			self.logger.info("Start commit index: " + str(self.last_commit_idx))
			while self.last_commit_idx + 1 <= self.log_idx and self.log[self.last_commit_idx+1]['commit_done'] is True:
				self.last_commit_idx += 1
			self.logger.info("End commit index: " + str(self.last_commit_idx))
			self.config_change['last_commit_idx'] = True

		self.logger.info("Commit done")

	def get_log_idx(self):
		self.logger.info("Get log idx")

		with self.lock:
			self.logger.info("Got the lock for idx")
			return self.log_idx
		
		
	def get_last_commit_index(self):
		self.logger.info("Get last commit idx")
		with self.lock:
			self.logger.info("Got the lock for commit idx")
			return self.last_commit_idx

	def get_term(self):
		# self.logger.info("Get term")
		with self.lock:
			# self.logger.info("Got the lock for term")
			return self.term

	def update_term(self, term):
		self.logger.info("Update term to: " + str(term))

		with self.lock:
			self.term = term
		self.config_change['term'] = True

		self.logger.info("Update term done")

	'''
	This will be called by follower nodes. This marks all logs till index as ready to be committed
	'''
	def commit_upto(self, index):
		self.logger.info("Commit upto index: " + str(index))

		with self.lock:
			self.logger.info("Start last commit idx: " + str(self.last_commit_idx))
			idx = self.last_commit_idx
			while idx + 1 <= index and idx + 1 <= self.log_idx:
				idx = idx + 1
				self.log[idx]['commit_done'] = True
			self.last_commit_idx = idx
			self.logger.info("End last commit idx: " + str(self.last_commit_idx))
		self.config_change['last_commit_idx'] = True

		self.logger.info("Commit upto index done")

	'''
	This will be called by thread periodically to apply log entries to the database
	'''
	def apply(self):

		while True:
			with self.lock:
				# self.logger.info("Apply started")
				c_idx = self.last_commit_idx
				idx = self.last_applied_idx + 1
				while idx <= c_idx:
					flush_res = self.flush(idx)
					if flush_res:
						entry = self.get(idx)
						self.logger.info('Applying value: ' + str(entry['value']) + ' to key: ' + str(entry['key']))
						self.database.put(entry['key'], entry['value'])
						self.last_applied_idx = self.last_applied_idx + 1
						self.last_applied_command_per_client.update({entry['clientid']: entry['sequence_number']})
						self.config_change['last_applied_idx'] = True
						self.config_change['last_applied_command_per_client'] = True
					else:
						break
					idx = idx + 1
			time.sleep(SERVER_SLEEP_TIME)

	def get(self, index):
		self.logger.info("Get at index: " + str(index))
		return self.log[index]

	def convert_optionals_to_list(self, entry):
		result = dict()
		result['term'] = entry['term']
		result['clientid'] = entry['clientid']
		result['sequence_number'] = entry['sequence_number']
		result['key'] = list()
		result['value'] = list()
		for k in entry['key']:
			result['key'].append(k)
		for v in entry['value']:
			result['value'].append(v)
		return result

	def append(self, entry):
		self.logger.info("Append entry- key: " + str(entry['key']) + ' value: ' + str(entry['value']))

		entry = self.convert_optionals_to_list(entry)

		with self.lock:
			self.logger.info("Log size before: " + str(len(self.log)))

			self.log_idx += 1
			self.log[self.log_idx] = entry
			self.log[self.log_idx]['commit_done'] = False
			self.config_change['log_idx'] = True

			self.logger.info("Log size after: " + str(len(self.log)))
			self.logger.info("Append entry done")
			return self.log_idx

	def insert_at(self, index, entry):
		self.logger.info("Insert at index: " + str(index))

		entry = self.convert_optionals_to_list(entry)

		with self.lock:
			if index == self.log_idx + 1:
				self.log_idx += 1
			elif index > self.log_idx + 1:
				self.logger.error("index > log_idx + 1 -- must not be possible")
				self.logger.info("Insert at index done")
				return -1
			self.log[index] = entry
			self.log[index]['commit_done'] = False

			self.config_change['log_idx'] = True

			self.logger.info("Insert at index done")
			return index

	def is_applied(self, index):
		self.logger.info("Is applied")

		return index <= self.last_applied_idx

	def get_leader(self):
		self.logger.info("Get leader")

		with self.lock:
			return self.leader_id

	def update_leader(self, leader):
		self.logger.info("Update leader to: " + leader)

		with self.lock:
			self.leader_id = leader
		self.config_change['leader_id'] = True
		
		self.logger.info("Update leader done")		

	def update_status(self, status):
		self.logger.info("Update status to: " + status)

		with self.lock:
			self.status = status
		self.config_change['status'] = True

		self.logger.info("Update status done")

	def get_status(self):
		# self.logger.info("Get status")

		return self.status
	
	def set_self_candidate(self):
		self.logger.info("Set self candidate")

		with self.lock:
			self.term += 1
			self.status = STATE['CANDIDATE']
			self.voted_for['term'] = self.term
			self.voted_for['server_id'] = self.server_id
			self.logger.info(f"my term {self.term}, my id {self.server_id}")
			self.logger.info(f"Updating status, voted for term {self.voted_for['term']}, voted for id {self.voted_for['server_id']}")

		self.config_change['voted_for'] = True
		self.config_change['status'] = True
		self.config_change['term'] = True	

		self.logger.info("Set self candidate done")

	def set_self_leader(self):
		self.logger.info("Set self leader")

		with self.lock:
			self.status = STATE['LEADER']
			self.leader_id = self.server_id
			self.logger.info(f"leader for term {self.term} is meeeee, self serverid {self.server_id}, leader id {self.leader_id}, ")
		self.config_change['status'] = True
		self.config_change['leader_id'] = True

		self.logger.info("Set self leader done")

	def revert_to_follower(self, new_term, new_leader_id):
		## If we are reverting to follower because we have cast a vote, we will set our term to new term
		## but we will set leader ID to None because we don't know if they actually won the election yet

		self.logger.info("Checking if I need to revert to follower")

		with self.lock:
			if self.status == STATE['CANDIDATE'] or self.status == STATE['LEADER']:
				self.logger.info(f'Reverting to follower from {self.status}')
				self.status = STATE['FOLLOWER']
				self.config_change['status'] = True
			
			if self.term != new_term:
				self.logger.info(f'Updating term from {self.term} to {new_term}')
				self.term = new_term
				self.config_change['term'] = True

			if self.leader_id != new_leader_id:
				self.logger.info(f'Updating leader id from {self.leader_id} to {new_leader_id}')
				self.leader_id = new_leader_id
				self.config_change['leader_id'] = True

		self.logger.info("Revert to follower done")

	def get_voted_for(self):
		self.logger.info("Get vorted for")

		return self.voted_for['term'], self.voted_for['server_id']
	
	def cast_vote(self, candidate_term, candidate_id):
		self.logger.info("Cast vote")

		with self.lock:
			self.term = candidate_term
			self.voted_for['term'] = candidate_term
			self.voted_for['server_id'] = candidate_id
		self.config_change['term'] = True
		self.config_change['voted_for'] = True

		self.logger.info("Case vote done")
			
	def get_last_committed_sequence_for(self, client_id):
		self.logger.info("Get last committed sequence for: " + str(client_id))

		with self.lock:
			if client_id in self.last_applied_command_per_client:
				return self.last_applied_command_per_client[client_id]
			else:
				return -1

	def clear(self):
		self.logger.info("clear")

		with self.lock:
			self.log.clear()
			self.last_commit_idx = -1
			self.log_idx = -1
			self.last_applied_idx = -1
			self.clear_log_backup()

		self.logger.info("clear done")
	
	def debug_print_log(self):
		self.logger.info("Debug print log")
		for key in self.log:
			self.logger.info("Index: " + str(key) + "- " +str(self.log[key]['key']) + " : " + str(self.log[key]['value']))
		self.logger.info("Debug print log done")

	def debug_get_last_commit_idx(self):
		return self.last_commit_idx

	def debug_print_config(self):
		self.logger.info("last_commit_idx: " + str(self.last_commit_idx))
		self.logger.info("last_applied_idx: " + str(self.last_applied_idx))
		self.logger.info("log_idx: " + str(self.log_idx))
		self.logger.info("term: " + str(self.term))
