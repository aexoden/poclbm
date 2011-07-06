import math
import re
import scipy.integrate
import time
import urllib2

_difficulty = (0, 0)

#-------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------

def get_difficulty():
	global _difficulty

	if time.time() - _difficulty[1] > 3600:
		difficulty = float(urllib2.urlopen('http://blockexplorer.com/q/getdifficulty').read())
		_difficulty = (difficulty, time.time())

	return _difficulty[0]

def get_servers(pools):
	servers = []

	for pool in pools:
		for server in pool.servers:
			servers.append(('', pool.username, pool.password, server))

	return servers

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

	def get_best_pools(self):
		return sorted(self.pools.values(), key=lambda pool: pool.utility, reverse=True)

#-------------------------------------------------------------------------------
# Pool Base Class
#-------------------------------------------------------------------------------

class Pool(object):
	def __init__(self, username, password):
		self.username = username
		self.password = password
		self.last_update = 0

	@property
	def utility(self):
		return 1.0

#-------------------------------------------------------------------------------
# Pools
#-------------------------------------------------------------------------------

class ArsBitcoinPool(Pool):
	name = 'arsbitcoin'
	servers = ['arsbitcoin.com:8344']

	def update_data(self):
		if time.time() - self.last_update > 120:
			data = urllib2.urlopen('http://www.arsbitcoin.com/stats.php').read()
			matches = re.search('Shares this round</td><td>([0-9]*)</td', data)

			if matches:
				self.shares = int(matches.group(1))

	@property
	def utility(self):
		self.update_data()
		progress = self.shares / get_difficulty()
		return scipy.integrate.quad((lambda x: (math.exp(progress - x) / x)), progress, 100.0)[0]

class EligiusPool(Pool):
	name = 'eligius'
	servers = ['srv3.mining.eligius.st:8337']

#-------------------------------------------------------------------------------
# Module Setup
#-------------------------------------------------------------------------------

_pool_class_map = {
	'arsbitcoin': ArsBitcoinPool,
	'eligius': EligiusPool,
}