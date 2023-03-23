GET_QUERY = 'select key, value from KeyValueStore where key = ?;'
PUT_QUERY = 'insert into KeyValueStore (key, value) values (?, ?);'
UPDATE_QUERY = 'update KeyValueStore value = ? where key = ?;'

def connect():
	pass

def get(key):
	pass

def put(key, value):
	pass

def update(key, value);
	pass