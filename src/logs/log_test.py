import sys
import time

sys.path.append('../')
sys.path.append('../../')

from log import Log
from store.database import Database
from logger import Logging

# Test recovery of db state and in-mem state. Implement clear on db. Implement shelve on im-mem db. Implement clear on in-mem db

# Tested: clear, is_applied, append, commit, commit_upto, apply, get_last_committed_sequence_for, insert_at

def create_entry(key, value, term, clientid, sequence_number):
	entry = {
		'key': key,
		'value': value,
		'term': term,
		'clientid': clientid,
		'sequence_number': sequence_number
	}
	return entry

def test_normal_functionality(log, db):
	clientid = 1
	sequence_number = 1
	term = 1

	# clear log
	log.clear()
	idx = log.get_log_idx()

	assert idx == -1

	# append first entry
	idx = log.append(create_entry(100, 1001, term, clientid, sequence_number))

	assert idx == 0

	log.commit(idx)

	time.sleep(1000/1000)

	assert log.is_applied(idx)

	# fetch first entry
	assert db.get(100) == 1001

	# append second entry
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(100, 2001, term, clientid, sequence_number))

	assert idx == 1

	log.commit(idx)

	time.sleep(1000/1000)

	assert log.is_applied(idx)
	# fetch updated value
	assert db.get(100) == 2001

	# append third entry
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(100, 3001, term, clientid, sequence_number))

	assert idx == 2

	log.commit(idx)

	time.sleep(1000/1000)

	assert log.is_applied(idx)
	# fetch updated value
	assert db.get(100) == 3001

	# append fourth entry on different key
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(200, 1002, term, clientid, sequence_number))

	assert idx == 3

	log.commit(idx)

	time.sleep(1000/1000)

	assert log.is_applied(idx)
	# fetch updated value
	assert db.get(200) == 1002
	return True

def test_last_commit_idx(log):
	clientid = 2
	sequence_number = 1
	term = 1

	# clear log
	log.clear()
	idx = log.get_log_idx()

	assert idx == -1
	assert log.debug_get_last_commit_idx() == -1

	# append first entry
	idx = log.append(create_entry(100, 2001, term, clientid, sequence_number))

	assert idx == 0

	log.commit(idx)

	assert log.debug_get_last_commit_idx() == 0

	# append second entry
	sequence_number = sequence_number + 1

	log.append(create_entry(100, 1001, term, clientid, sequence_number))

	# append third entry
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(100, 3001, term, 1, sequence_number))

	assert idx == 2

	log.commit(idx)

	assert log.debug_get_last_commit_idx() == 0

	# append fourth entry
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(300, 1003, term, 3, sequence_number))

	assert idx == 3

	log.commit_upto(idx)

	assert log.debug_get_last_commit_idx() == 3

	time.sleep(1000/1000)

	return True

# to be called only after test_last_commit_idx()
def test_recovery(log):
	time.sleep(1000/1000)
	assert log.get_log_idx() == 3
	assert log.debug_get_last_commit_idx() == 3
	assert log.is_applied(3)
	assert log.get_last_committed_sequence_for(2) == 2
	assert log.get_last_committed_sequence_for(1) == 3
	assert log.get_last_committed_sequence_for(3) == 4

	# append entry

	idx = log.append(create_entry(400, 1004, 2, 3, 5))

	assert idx == 4

	log.commit_upto(idx)

	assert log.debug_get_last_commit_idx() == 4

	time.sleep(1000/1000)

	assert log.is_applied(idx)

	assert db.get(400) == 1004

	return True

def test_insert_at(log):

	clientid = 1
	sequence_number = 1
	term = 1

	# clear log
	log.clear()
	idx = log.get_log_idx()

	assert idx == -1

	# append first entry
	idx = log.append(create_entry(100, 1001, term, clientid, sequence_number))

	assert idx == 0

	# append second entry
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(200, 2001, term, clientid, sequence_number))

	assert idx == 1

	# fetch first entry
	assert log.get(0)['key'] == 100
	assert log.get(0)['value'] == 1001

	# update fisrt entry
	sequence_number = sequence_number + 1

	idx = log.insert_at(0, create_entry(100, 1002, term, clientid, sequence_number))

	assert idx == 0

	log.commit_upto(1)

	time.sleep(1000/1000)

	assert log.is_applied(idx)

	# fetch updated value
	assert db.get(100) == 1002
	assert db.get(200) == 2001
	return True

if __name__ == '__main__':
	logger = Logging('server_1').get_logger()

	db = Database(server_id = 'server_1', logger = logger, type = 'sqlite3')
	log = Log('server_1', db, logger)

	if test_normal_functionality(log, db):
		print('normal functionality test passed')

	if test_last_commit_idx(log):
		print('last commit idx test passed')

	log = Log('server_1', db, logger)

	if test_recovery(log):
		print('test recovery passed')

	if test_insert_at(log):
		print('insert at test passed')
	
	db = Database(server_id = 'server_1', type = 'memory', logger = logger)
	log = Log('server_1', db, logger)

	if test_normal_functionality(log, db):
		print('normal functionality test passed')

	if test_last_commit_idx(log):
		print('last commit idx test passed')

	log = Log('server_1', db, logger)

	if test_recovery(log):
		print('test recovery passed')

	if test_insert_at(log):
		print('insert at test passed')
