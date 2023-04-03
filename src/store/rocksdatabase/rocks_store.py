import rocksdb

from os import path, makedirs

# Make this guy implement an interface
class RocksStore:

	def __init__(self, store_name):

		# Set the store path
		self.store_path = path.join('./store/', store_name)
		if not path.exists(self.store_path):
			makedirs(self.store_path)

		# Set rocks db options
		self.rocks_opts = rocksdb.Options()
		self.rocks_opts.create_if_missing = True
		self.rocks_opts.max_open_files = 300000
		self.rocks_opts.write_buffer_size = 67108864
		self.rocks_opts.max_write_buffer_number = 3
		self.rocks_opts.target_file_size_base = 67108864
		self.rocks_opts.table_factory = rocksdb.BlockBasedTableFactory(
			filter_policy=rocksdb.BloomFilterPolicy(10),
			block_cache=rocksdb.LRUCache(2 * (1024 ** 3)),
			block_cache_compressed=rocksdb.LRUCache(500 * (1024 ** 2)))

		# Initialize DB
		self.db = rocksdb.DB(self.store_path, self.rocks_opts)

	def get(self, key):
		key = bytes(key, encoding='UTF-8')
		value = self.db.get(key)
		return value.decode('UTF-8')

	def put(self, key, value):
		key = bytes(key, encoding='UTF-8')
		value = bytes(value, encoding='UTF-8')
		self.db.put(key, value)