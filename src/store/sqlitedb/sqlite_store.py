import sqlite3

from os import path, getenv, makedirs

'''
TODO:
1. Implement persistence of SqliteStore
2. Implement recovery of SqliteStore
'''
class SqliteStore:

	def __init__(self, store_name, logger):

		self.logger = logger

		# Set the store path
		store_dir = './store'
		self.store_path = path.join(store_dir, store_name)

		if not path.exists(store_dir):
			makedirs(store_dir)

		# Initialize DB
		self.conn = sqlite3.connect(self.store_path, check_same_thread=False)

		# Create table
		self.create_key_value_table()

	def create_key_value_table(self):
		cursor = self.conn.cursor()
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS key_value_store (
				key TEXT PRIMARY KEY,
				value TEXT
			)
		""")
		self.conn.commit()

	def get(self, key):
		self.logger.info("Sqlite get called for key: " + str(key))
		cursor = self.conn.cursor()
		cursor.execute("SELECT value from key_value_store WHERE key = ?", (key,))
		result = cursor.fetchone()
		self.logger.info("Returning value: " + str(result))
		if result is not None:
			return int(result[0])
		else:
			return None

	def put(self, key, value):
		self.logger.info("Sqlite put called for key: " + str(key) + ", value: " + str(value))
		cursor = self.conn.cursor()
		cursor.execute("INSERT OR REPLACE INTO key_value_store (key, value) VALUES (?, ?)", (key, value))
		self.conn.commit()