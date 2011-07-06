import json
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
		return 1.0 * (1 - self.fee)

	def update_data(self):
		if time.time() - self.last_update > 120:
			self.get_data()
			self.last_update = time.time()

class ProportionalPool(Pool):
	@property
	def utility(self):
		self.update_data()
		progress = max(self.shares, 1.0) / get_difficulty()
		return scipy.integrate.quad((lambda x: (math.exp(progress - x) / x)), progress, 100.0)[0] * (1 - self.fee)

#-------------------------------------------------------------------------------
# Pools
#-------------------------------------------------------------------------------

class ArsBitcoinPool(ProportionalPool):
	name = 'arsbitcoin'
	servers = ['arsbitcoin.com:8344']
	fee = 0.0

	def get_data(self):
		data = urllib2.urlopen('http://www.arsbitcoin.com/stats.php').read()
		matches = re.search('Shares this round</td><td>([0-9]*)</td', data)

		if matches:
			self.shares = int(matches.group(1))

class BitClockersPool(ProportionalPool):
	name = 'bitclockers'
	servers = ['pool.bitclockers.com:8332']
	fee = 0.02

	def get_data(self):
		data = json.loads(urllib2.urlopen('http://bitclockers.com/api').read())
		self.shares = int(data['roundshares'])

class BitCoinsLCPool(ProportionalPool):
	name = 'bitcoins.lc'
	servers = ['bitcoins.lc:8080']
	fee = 0.0

	def get_data(self):
		data = json.loads(urllib2.urlopen('http://www.bitcoins.lc/stats.json').read())
		self.shares = int(data['valid_round_shares'])

class BTCGuildPool(ProportionalPool):
	name = 'btcguild'
	servers = ['uscentral.btcguild.com:8332', 'useast.btcguild.com:8332', 'de1.btcguild.com:8332', 'de2.btcguild.com:8332']
	fee = 0.0

	def get_data(self):
		data = json.loads(urllib2.urlopen('http://www.btcguild.com/pool_stats.php').read())
		self.shares = int(data['round_shares'])

class EligiusPool(Pool):
	name = 'eligius'
	servers = ['srv3.mining.eligius.st:8337']
	fee = 0.0000004096
				
class MineCoinPool(ProportionalPool):
	name = 'mineco.in'
	servers = ['mineco.in:3000']
	fee = 0.0

	def get_data(self):
		data = json.loads(urllib2.urlopen('http://mineco.in/stats.json').read())
		self.shares = int(data['shares_this_round'])

class MtRedPool(ProportionalPool):
	name = 'mtred'
	servers = ['173.193.21.69:8337']
	fee = 0.0

	def get_data(self):
		data = json.loads(urllib2.urlopen('https://mtred.com/api/stats').read())
		self.shares = int(data['roundshares'])

#-------------------------------------------------------------------------------
# Module Setup
#-------------------------------------------------------------------------------

_pool_class_map = {
	'arsbitcoin': ArsBitcoinPool,
	'bitclockers': BitClockersPool,
	'bitcoins.lc': BitCoinsLCPool,
#	'btcguild': BTCGuildPool,
	'eligius': EligiusPool,
	'mineco.in': MineCoinPool,
	'mtred': MtRedPool,
}
