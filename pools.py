import re

#-------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------

def load_pool_config(filename):
	pools = {}

	with open(filename, 'r') as f:
		for line in f:
			fields = re.split('\s+', line)

			pools[fields[0]] = (fields[1], fields[2])

	return pools

#-------------------------------------------------------------------------------
# PoolManager Class
#-------------------------------------------------------------------------------

class PoolManager(object):
	def __init__(self, config_filename='pools.conf'):
		self.load_pools(config_filename)

	def load_pools(self, config_filename):
		self.pools = {}

		for pool, pool_data in sorted(load_pool_config(config_filename).items()):
			if pool in _pool_class_map:
				self.pools[pool] = _pool_class_map[pool](pool_data[0], pool_data[1])

	def get_servers(self):
		servers = []

		for pool_name, pool in self.pools.items():
			for server in pool.servers:
				servers.append(('', pool.username, pool.password, server))

		return servers

#-------------------------------------------------------------------------------
# Pool Base Class
#-------------------------------------------------------------------------------

class Pool(object):
	def __init__(self, username, password):
		self.username = username
		self.password = password

#-------------------------------------------------------------------------------
# Pools
#-------------------------------------------------------------------------------

class ArsBitcoinPool(Pool):
	servers = ['arsbitcoin.com:8344']

class EligiusPool(Pool):
	servers = ['srv3.mining.eligius.st:8337']

#-------------------------------------------------------------------------------
# Module Setup
#-------------------------------------------------------------------------------

_pool_class_map = {
	'arsbitcoin': ArsBitcoinPool,
	'eligius': EligiusPool,
}
