import sys
import time

sys.path.append('../')
sys.path.append('../../')

from log import Log
from store.memorydatabase.mem_store import MemoryStore
from logger import Logging

# To test
# commit, get_log_idx, get_term, update_term, commit_upto, apply, get, insert_at, is_applied, get_leader, update_leader, update_status, append
# get_status, set_self_candidate, set_self_leader, revert_to_follower, get_voted_for, cast_vote, get_last_committed_sequence_for, clear

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
	idx = log.append(create_entry(100, 1000, term, clientid, sequence_number))

	assert idx == 0

	log.commit(idx)

	time.sleep(5000/1000)

	assert log.is_applied(idx)

	# fetch first entry
	assert db.get(100) == 1000

	# append second entry
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(100, 2000, term, clientid, sequence_number))

	assert idx == 1

	log.commit(idx)

	time.sleep(5000/1000)

	assert log.is_applied(idx)
	# fetch updated value
	assert db.get(100) == 2000

	# append third entry
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(100, 3000, term, clientid, sequence_number))

	assert idx == 2

	log.commit(idx)

	time.sleep(5000/1000)

	assert log.is_applied(idx)
	# fetch updated value
	assert db.get(100) == 3000

	# append fourth entry on different key
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(100, 2000, term, clientid, sequence_number))

	assert idx == 1

	log.commit(idx)

	time.sleep(5000/1000)

	assert log.is_applied(idx)
	# fetch updated value
	assert db.get(100) == 2000

	# append third entry
	sequence_number = sequence_number + 1

	idx = log.append(create_entry(100, 3000, term, clientid, sequence_number))

	assert idx == 2

	log.commit(idx)

	time.sleep(5000/1000)

	assert log.is_applied(idx)
	
	return True


if __name__ == '__main__':
	logger = Logging('server_1').get_logger()
	db = MemoryStore()
	log = Log('server_1', db, logger)

	if test_normal_functionality(log, db):
		print('normal insert test passed')
	