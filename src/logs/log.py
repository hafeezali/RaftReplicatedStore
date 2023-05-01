import sys

sys.path.append('../')

from os import path, makedirs
from threading import Lock, Thread

import time
import shelve

from raft.config import STATE
from raft.config import SERVER_SLEEP_TIME, FLUSH_CONFIG_TIME
from store.database import Database

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
	- last_appended_command_per_client
	- last_safe_index
	- last_safe_index_per_follower

TODO:
1. [IN_PROGRESS] All persistent state can be collated into one dict. Easier persistence and recovery (but cant implement finer locks)
2. clear_log_backup() can live inside clear()
3. [DONE] Shelve is having some weird behavior when appending the first element to the list - investigate this later (fixed by using a dict instead of list for log)
4. We probably want the locks to become more finer for some performance gains
5. Can ignore committed logs from disk on recover. Can remove committed logs from log dict
6. [TO_START] last_applied_command_per_client should be updated after every append, but persisted after every apply. We need to store a volatile map called last_appended_command_per_client and recover this from snapshot and replay of logs
'''

class Log:

	'''
	server_id: Used to name the persistent log and config files. Also used whenever setting oneself as leader
	database: instance of mem_store or rocks_store used by this server
	logger: common logger used across node
	'''
	def __init__(self, server_id, database : Database, logger):

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

		self.configs = dict()
		self.configs["last_commit_idx"] = -1
		self.configs["log_idx"] = -1
		self.configs["last_applied_idx"] = -1
		self.configs["term"] = 0
		self.configs["status"] = STATE['FOLLOWER']
		self.configs["voted_for"] = {
			'term': 0,
			'server_id': None
		}
		self.configs["leader_id"] = None
		self.configs["last_appended_command_per_client"] = dict()

		# volatile state
		# For leader, it is the log_index. For follower, it is the last index inserted/appended by the current leader
		# On recovery, it is initialized to last_commit_index for follower and leader. 
		# For leader it should get updated to log_idx and for follower, it should be updated after the 1st RPC
		self.last_safe_index = -1

		# leader stores the last safe index for each client. 
		# This will get populated as leader sends append entries to clients and doesn't need to be persisted
		self.last_safe_index_per_follower = dict()
		self.configs["last_flushed_idx"] = -1

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

		config_file['last_commit_idx'] = self.configs["last_commit_idx"]
		config_file['log_idx'] = self.configs["log_idx"]
		config_file['last_applied_idx'] = self.configs["last_applied_idx"]
		config_file["last_flushed_idx"] = self.configs["last_flushed_idx"]

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
				self.configs["last_commit_idx"] = config_file['last_commit_idx']
				self.last_safe_index = config_file['last_commit_idx']
			if config_file['log_idx']:
				self.configs["log_idx"] = config_file['log_idx']
			if config_file['last_applied_idx']:
				self.configs["last_applied_idx"] = config_file['last_applied_idx']
			if config_file['term']:
				self.configs["term"] = config_file['term']
			if config_file['status']:
				self.configs["status"] = config_file['status']
			if config_file['voted_for']:
				self.configs["voted_for"] = config_file['voted_for']
			if config_file['leader_id']:
				self.configs["leader_id"] = config_file['leader_id']
			if config_file['last_appended_command_per_client']:
				self.configs["last_appended_command_per_client"] = config_file['last_appended_command_per_client']
			if config_file['last_flushed_idx']:
				self.configs['last_flushed_idx'] = config_file['last_flushed_idx']
		except KeyError as e:
			self.logger.info("KeyError")
			config_file['last_commit_idx'] = self.configs["last_commit_idx"]
			config_file['log_idx'] = self.configs["log_idx"] 
			config_file['last_applied_idx'] = self.configs["last_applied_idx"] 
			config_file['term'] = self.configs["term"]
			config_file['status'] = self.configs["status"]
			config_file['voted_for'] = self.configs["voted_for"]
			config_file['leader_id'] = self.configs["leader_id"] 
			config_file['last_appended_command_per_client'] = self.configs["last_appended_command_per_client"] 
			config_file['last_flushed_idx'] = self.configs['last_flushed_idx']

		log_file.close()
		config_file.close()

		# Apply entries from log that were not yet flushed
		self.logger.info(f"Config recovery done, need to replay logs from {self.configs['last_flushed_idx']}")
		self.apply_from_index(self.configs['last_flushed_idx'])

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
			log_file[str(index)] = self.log[index]
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

		while True:
			self.configs["last_flushed_idx"] = self.database.get_last_flushed_index()
			config_file = shelve.open(self.config_path, 'c', writeback=True)
			with self.lock:
				config_file.update(self.configs)

			config_file.close()
			time.sleep(FLUSH_CONFIG_TIME)

	def get_log_idx(self):
		self.logger.info("Get log idx")
		with self.lock:
			return self.configs["log_idx"]
		
		
	def get_last_commit_index(self):
		self.logger.info("Get last commit idx")
		with self.lock:
			return self.configs["last_commit_idx"]

	def get_term(self):
		# self.logger.info("Get term")
		with self.lock:
			return self.configs["term"]

	def update_term(self, term):
		self.logger.info("Update term to: " + str(term))

		with self.lock:
			self.configs["term"] = term

		self.logger.info("Update term done")

	'''
	This marks all logs till index as ready to be committed
	'''
	def commit_upto(self, index):
		self.logger.info("Commit upto index: " + str(index))

		with self.lock:
			self.logger.info("Start last commit idx: " + str(self.configs["last_commit_idx"]))
			idx = self.configs["last_commit_idx"]
			while idx + 1 <= index and idx + 1 <= self.configs["log_idx"]:
				idx = idx + 1
				self.log[idx]['commit_done'] = True
			self.configs["last_commit_idx"] = idx
			self.logger.info("End last commit idx: " + str(self.configs["last_commit_idx"]))

		self.logger.info("Commit upto index done")

	'''
	This will be called by thread periodically to apply log entries to the database
	'''
	def apply(self):

		while True:
			with self.lock:
				c_idx = self.configs["last_commit_idx"]
				idx = self.configs["last_applied_idx"] + 1
				while idx <= c_idx:
					flush_res = self.flush(idx)
					if flush_res:
						entry = self.get(idx)
						self.logger.info('Applying value: ' + str(entry['value']) + ' to key: ' + str(entry['key']))
						self.database.put(entry['key'], entry['value'], idx)
						self.configs["last_applied_idx"] = self.configs["last_applied_idx"] + 1
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
		result['key'] = [k for k in entry['key']]
		result['value'] = [v for v in entry['value']]

		return result

	def append(self, entry):
		self.logger.info("Append entry- key: " + str(entry['key']) + ' value: ' + str(entry['value']))

		entry = self.convert_optionals_to_list(entry)

		with self.lock:
			self.logger.info("Log size before: " + str(len(self.log)))

			self.configs["log_idx"] += 1
			self.log[self.configs["log_idx"]] = entry
			self.log[self.configs["log_idx"]]['commit_done'] = False

			self.configs["last_appended_command_per_client"].update({entry['clientid']: entry['sequence_number']})
			self.last_safe_index = self.log_idx

			self.logger.info("Log size after: " + str(len(self.log)))
			self.logger.info("Append entry done")
			return self.configs["log_idx"]

	def insert_at(self, index, entry):
		self.logger.info("Insert at index: " + str(index))

		entry = self.convert_optionals_to_list(entry)

		with self.lock:
			if index == self.configs["log_idx"] + 1:
				self.configs["log_idx"] += 1
			elif index > self.configs["log_idx"] + 1:
				self.logger.error("index > log_idx + 1 -- must not be possible")
				self.logger.info("Error: Insert at index not done")
				return -1
			
			self.log[index] = entry
			self.log[index]['commit_done'] = False
			self.last_safe_index = min(self.last_safe_index, self.log_idx)
			if entry['sequence_number'] > self.configs['last_appended_command_per_client'][entry['clientid']]:
				self.configs["last_appended_command_per_client"].update({entry['clientid']: entry['sequence_number']})


			self.logger.info("Insert at index done")
			return index

	def is_applied(self, index):
		self.logger.info("Is applied")

		return index <= self.configs["last_applied_idx"]

	def get_leader(self):
		self.logger.info("Get leader")

		with self.lock:
			return self.configs["leader_id"]

	def update_leader(self, leader):
		self.logger.info("Update leader to: " + leader)

		with self.lock:
			self.configs["leader_id"] = leader
		
		self.logger.info("Update leader done")		

	def update_status(self, status):
		self.logger.info("Update status to: " + status)

		with self.lock:
			self.configs["status"] = status

		self.logger.info("Update status done")

	def get_status(self):
		self.logger.info("Get status")
		return self.configs["status"]
	
	def set_self_candidate(self):
		self.logger.info("Set self candidate")

		with self.lock:
			self.configs["term"] += 1
			self.configs["status"] = STATE['CANDIDATE']
			self.configs["voted_for"]['term'] = self.configs["term"]
			self.configs["voted_for"]['server_id'] = self.server_id

			self.logger.info(f'my term {self.configs["term"]}, my id {self.server_id}')
			self.logger.info(f"Updating status, voted for myself")

		self.logger.info("Set self candidate done")

	def set_self_leader(self):
		self.logger.info("Set self leader")

		with self.lock:
			self.configs["status"] = STATE['LEADER']
			self.configs["leader_id"] = self.server_id
			self.logger.info(f'Leader for term {self.configs["term"]} is me, self serverid {self.server_id}')

		self.logger.info("Set self leader done")

	def revert_to_follower(self, new_term, new_leader_id):
		## If we are reverting to follower because we have cast a vote, we will set our term to new term
		## but we will set leader ID to None because we don't know if they actually won the election yet

		self.logger.info("Checking if I need to revert to follower")

		with self.lock:
			if self.configs["status"] == STATE['CANDIDATE'] or self.configs["status"] == STATE['LEADER']:
				self.logger.info(f'Reverting to follower from {self.configs["status"]}')
				self.configs["status"] = STATE['FOLLOWER']
			
			if self.configs["term"] != new_term:
				self.logger.info(f'Updating term from {self.configs["term"]} to {new_term}')
				self.configs["term"] = new_term

			if self.configs["leader_id"] != new_leader_id:
				self.logger.info(f'Updating leader id from {self.configs["leader_id"]} to {new_leader_id}')
				self.configs["leader_id"] = new_leader_id

		self.logger.info("Revert to follower done")

	def get_voted_for(self):
		self.logger.info("Get vorted for")

		return self.configs["voted_for"]['term'], self.configs["voted_for"]['server_id']
	
	def cast_vote(self, candidate_term, candidate_id):
		self.logger.info("Cast vote")

		with self.lock:
			self.configs["term"] = candidate_term
			self.configs["voted_for"]['term'] = candidate_term
			self.configs["voted_for"]['server_id'] = candidate_id

		self.logger.info("Case vote done")
			
	def get_last_appended_sequence_for(self, client_id):
		self.logger.info("Get last appended sequence for: " + str(client_id))

		with self.lock:
			if client_id in self.configs["last_appended_command_per_client"]:
				return self.configs["last_appended_command_per_client"][client_id]
			else:
				return -1

	def clear(self):
		self.logger.info("clear")

		with self.lock:
			self.log.clear()
			self.configs["last_commit_idx"] = -1
			self.configs["log_idx"] = -1
			self.configs["last_applied_idx"] = -1
			self.configs["last_flushed_idx"] = -1
			self.last_safe_index = -1
			self.clear_log_backup()

		self.logger.info("clear done")
	
	def update_last_safe_index_for(self, follower_id, last_safe_index):
		self.logger.info("Update last safe index for :" + str(follower_id))
		with self.lock:
			self.last_safe_index_per_follower[follower_id] = last_safe_index

	def get_last_safe_index_for(self, follower_id):
		self.logger.info("Get last safe index for: " + str(follower_id))

		with self.lock:
			if follower_id in self.last_safe_index_per_follower:
				return self.last_safe_index_per_follower[follower_id]
			else:
				return -1

	def get_last_safe_index(self):
		self.logger.info("Geting last safe index...")
		return self.last_safe_index

	def debug_print_log(self):
		self.logger.info("Debug print log")
		for key in self.log:
			self.logger.info("Index: " + str(key) + "- " +str(self.log[key]['key']) + " : " + str(self.log[key]['value']))
		self.logger.info("Debug print log done")

	def debug_get_last_commit_idx(self):
		return self.configs["last_commit_idx"]

	def debug_print_config(self):
		self.logger.info("last_commit_idx: " + str(self.configs["last_commit_idx"]))
		self.logger.info("last_applied_idx: " + str(self.configs["last_applied_idx"]))
		self.logger.info("log_idx: " + str(self.configs["log_idx"]))
		self.logger.info("term: " + str(self.configs["term"]))


	'''
	Apply entries from log that had not previously been flushed to disk before failure
	
    Only called from recover method to apply entries that were not part of the snapshot.

	'''
	def apply_from_index(self, idx):
		
		start_idx = idx

		# Resetting last_applied_idx to the last index that was applied and flushed to disk
		# Any changes that were applied to in mem but not flused are lost on server crash
		# We will replay logs from the last flushed index, and reapply those changes to in mem state
		self.configs['last_applied_idx'] = idx
		self.logger.info(f"Resetting applied indext to {idx}")
		
		with self.lock:
			self.logger.info(f"Apply_from_index {idx} started")
			c_idx = self.configs["last_commit_idx"]
			idx = self.configs["last_applied_idx"] + 1

			while idx <= c_idx:
				entry = self.get(idx)
				self.logger.info('Applying value: ' + str(entry['value']) + ' to key: ' + str(entry['key']))
				self.database.put(entry['key'], entry['value'], idx)
				self.configs["last_applied_idx"] = self.configs["last_applied_idx"] + 1
				idx = idx + 1

			self.logger.info(f"Apply_from_index finished, from {start_idx} to {c_idx}")
			



	

