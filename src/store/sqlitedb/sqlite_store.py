import sqlite3

from os import path, getenv, makedirs

class SqliteStore:

	def __init__(self, server_id, logger):

		self.logger = logger

		# Set the store path
		store_dir = './store'
		self.db_backup_file_name = server_id + '_sql'
		self.store_path = path.join(store_dir, self.db_backup_file_name)

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
		for (k, v) in zip(key, value):
			cursor = self.conn.cursor()
			cursor.execute("INSERT OR REPLACE INTO key_value_store (key, value) VALUES (?, ?)", (k, v))
			self.conn.commit()

	def clear_backup(self):
		self.logger.info("Clear backup for Sqlite db called")
		cursor = self.conn.cursor()
		cursor.execute("""
			DELETE FROM key_value_store;
		""")
		self.conn.commit()
		self.logger.info("Clear backup done")