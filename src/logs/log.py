from os import path, getenv, makedirs
from threading import Lock, Thread

import time
import shelve

from raft.config import STATE

class Log:

	def __init__(self, server_id, database):
		backup_name = server_id + '.log'
		self.server_id = server_id
		self.backup_path = path.join('backup', backup_name)
		self.database = database

		# persistent configs
		self.log = list()
		self.last_commit_idx = 0
		self.log_idx = 0
		self.last_applied_idx = 0
		self.term = 0
		self.status = STATE['FOLLOWER']
		self.voted_for = {
			'term': 0,
			'server_id': None
		}
		self.leader_id = None
		self.last_applied_command_per_client = dict()
		
		self.lock = Lock()
		
		self.recover()

		Thread(target=self.apply).start()

	def delete_log_backup(self):
		pass

	def recover(self):
		pass

	def flush(self, index):
		pass

	def get_log_idx(self):
		with self.lock:
			return self.log_idx

	def get_term(self):
		with self.lock:
			return self.term

	def update_term(self, term):
		with self.lock:
			self.term = term

	def commit_upto(self, index):
		with self.lock:
			if self.last_commit_idx < index:
				self.last_commit_idx = index

	def apply(self):
		while True:
			c_idx = self.last_commit_idx
			idx = self.last_applied_idx + 1
			while idx < c_idx: 
				flush_res = self.flush(idx)
				if flush_res:
					entry = self.get(idx)
					self.database.put(entry.key, entry.value)
					idx = idx + 1
					self.last_applied_idx = self.last_applied_idx + 1
					self.last_applied_command_per_client.update({entry.client_id, idx})
				else:
					break
			time.sleep(100)

	def get(self, index):
		return self.log[index]

	def insert_at(self, index, entry):
		with self.lock:
			if index <= self.log_idx:
				self.log[index] = entry
				return index
			else:
				self.list.append(entry)
				self.log_idx += 1
				return self.log_idx

	def is_applied(self, index):
		return index <= self.last_applied_idx

	def get_leader(self):
		with self.lock:
			return self.leader_id

	def update_leader(self, leader):
		with self.lock:
			self.leader_id = leader

	def update_status(self, status):
		with self.lock:
			self.status = status

	def get_status(self):
		return self.status
	
	def set_self_candidate(self):
		with self.lock:
			self.term += 1
			self.status = STATE['CANDIDATE']

	def set_self_leader(self):
		with self.lock:
			self.status = STATE['LEADER']
			self.leader_id = self.server_id

	def revert_to_follower(self, new_term, new_leader_id):
		with self.lock:
			if self.status == STATE['CANDIDATE'] or self.status == STATE['LEADER']:
				self.status = STATE['FOLLOWER']

			self.term = new_term
			self.leader_id = new_leader_id

	def get_voted_for(self):
		return self.voted_for['term'], self.voted_for['server_id']
	
	def cast_vote(self, candidate_term, candidate_id):
		with self.lock:
			self.term = candidate_term
			self.voted_for['term'] = candidate_id
			self.voted_for['server_id'] = candidate_id
			
	def get_last_committed_sequence_for(self, client_id):
		with self.lock:
			return self.last_applied_command_per_client[client_id]

	def clear(self):
		with self.lock:
			self.log.clear()
			self.last_commit_idx = 0
			self.log_idx = 0
			self.last_applied_idx = 0
			self.delete_log_backup()
			
