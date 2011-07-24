import json
import math
import re
import scipy.integrate
import time
import urllib2

_difficulty = (0, 0)
_pool_blocks = ({}, 0)

#-------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------

def get_difficulty():
	global _difficulty

	if time.time() - _difficulty[1] > 3600:
		difficulty = float(urllib2.urlopen('http://blockexplorer.com/q/getdifficulty').read())
		_difficulty = (difficulty, time.time())

	return _difficulty[0]

def get_pool_blocks(pool):
	global _pool_blocks

	if time.time() - _pool_blocks[1] > 120:
		try:
			pool_blocks = json.loads(urllib2.urlopen('http://bitcoin.calindora.com/pool_recent_blocks.json').read())
			_pool_blocks = (pool_blocks, time.time())
		except:
			pass

	return _pool_blocks[0][pool] if pool in _pool_blocks[0] else {}

def get_servers(pools):
	servers = []

	for pool in pools:
		for server in pool.servers:
			servers.append(('', pool.username, pool.password, server, pool.name))

	return servers

def load_pool_config(filename):
	pools = {}
	priority = 1000

	with open(filename, 'r') as f:
		for line in f:
			fields = re.split('\s+', line)

			pools[fields[0]] = (fields[1], fields[2], priority)

			priority -= 1

	return pools

#-------------------------------------------------------------------------------
# PoolManager Class
#-------------------------------------------------------------------------------

class PoolManager(object):
	def __init__(self, config_filename='pools.conf'):
		self.load_pools(config_filename)

	def load_pools(self, config_filename):
		self.pools = {}

		for pool, pool_data in load_pool_config(config_filename).items():
			if pool in _pool_class_map:
				self.pools[pool] = _pool_class_map[pool](pool_data[0], pool_data[1], pool_data[2])

	def get_best_pools(self):
		return sorted(self.pools.values(), key=lambda pool: (pool.utility, pool.priority), reverse=True)

#-------------------------------------------------------------------------------
# Pool Base Class
#-------------------------------------------------------------------------------

class Pool(object):
	def __init__(self, username, password, priority):
		self.username = username
		self.password = password
		self.priority = priority
		self.last_update = 0
		self.rate = 1.0

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
		try:
			self.update_data()
		except (ValueError, urllib2.HTTPError):
			pass

		blocks = get_pool_blocks(self.pident_name)

		utility = 0.0

		for block_time, probability in sorted(blocks.items()):
			shares = (self.rate * (time.time() - float(block_time))) / 2 ** 32
			progress = max(shares, 1.0) / get_difficulty()
			utility += probability * scipy.integrate.quad((lambda x: (math.exp(progress - x) / x)), progress, 100.0)[0]

		return utility * 1 - self.fee

#-------------------------------------------------------------------------------
# Unsupported Pools
#-------------------------------------------------------------------------------

# Bitcoinpool
# Uses a strange anti-hopping measure that needs to be evaluated.

# Slush and BTCMine
# Use a score-based systems that I have no fully evaluated for hopping
# potential, but should be nearly hop-proof.

# x8s
# Uses PPLNS payout, so is not hoppable. Charges a 1% fee, so there's no value
# beyond the other backups already implemented.

#-------------------------------------------------------------------------------
# Geometric/PPLNS/SMPPS Pools
#-------------------------------------------------------------------------------
# TODO: Figure out which pools give transaction fees back.

class ArsBitcoinPool(Pool):
	name = 'arsbitcoin'
	pident_name = 'ArsBitcoin'
	servers = ['arsbitcoin.com:8344']
	fee = 0.0

class BitPitPool(Pool):
	name = 'bitpit'
	pident_name = 'BitPit'
	servers = ['pool.bitp.it:8334']
	fee = 0.0

class EclipseMCPool(Pool):
	name = 'eclipsemc'
	pident_name = 'EclipseMC'
	servers = ['us.eclipsemc.com:8337', 'eu.eclipsemc.com:8337']
	fee = 0.0

class EligiusPool(Pool):
	name = 'eligius'
	pident_name = 'Eligius'
	servers = ['mining.eligius.st:8337']
	fee = 0.000001

class MineCoinPool(Pool):
	name = 'mineco.in'
	pident_name = 'Mineco.in'
	servers = ['mineco.in:3000']
	fee = 0.0

#-------------------------------------------------------------------------------
# Proportional Pools
#-------------------------------------------------------------------------------
# POOLS TO ADD/UPDATE:
# Bitcoinpool
# Ozco.in

class BitCoinsLCPool(ProportionalPool):
	name = 'bitcoins.lc'
	pident_name = 'Bitcoins.lc'
	servers = ['bitcoins.lc:8080']
	fee = 0.0

	def get_data(self):
		data = json.loads(urllib2.urlopen('http://www.bitcoins.lc/stats.json').read())
		self.rate = float(data['hash_rate'])

class BTCGuildPool(ProportionalPool):
	name = 'btcguild'
	pident_name = 'BTCGuild'
	servers = ['uswest.btcguild.com:8332', 'uscentral.btcguild.com:8332',]
	fee = 0.0

	def get_data(self):
		data = json.loads(urllib2.urlopen('http://www.btcguild.com/pool_stats.php').read())
		self.rate = float(data['hash_rate']) * 1000000000.0

class MtRedPool(ProportionalPool):
	name = 'mtred'
	pident_name = 'MtRed'
	servers = ['mtred.com:8337']
	fee = 0.0

	def get_data(self):
		data = json.loads(urllib2.urlopen('https://mtred.com/api/stats').read())
		self.rate = float(data['hashrate']) * 1000000000.0

class OzCoinPool(ProportionalPool):
	name = 'ozco.in'
	pident_name = 'Ozco.in'
	servers = ['ozco.in:8332']
	fee = 0.0

	def get_data(self):
		data = json.loads(urllib2.urlopen('https://ozco.in/api.php').read())
		self.rate = float(data['hashrate']) * 1000000.0

class RFCPool(ProportionalPool):
	name = 'rfcpool'
	pident_name = 'RFCPool'
	servers = ['pool.rfcpool.com:8332']
	fee = 0.0

	def get_data(self):
		data = json.loads(urllib2.urlopen('https://rfcpool.com/api/pool/stats').read())['poolstats']

		multipliers = {
			'H/s':  1.0,
			'KH/s': 1000.0,
			'MH/s': 1000000.0,
			'GH/s': 1000000000.0,
			'TH/s': 1000000000000.0,
		}

		self.rate = float(data['hashrate']) * multipliers[data['hashrate_unit']]

class TripleMiningPool(ProportionalPool):
	name = 'triplemining'
	pident_name = 'TripleMining'
	servers = ['eu.triplemining.com:8344']
	fee = 0.01

	def get_data(self):
		data = urllib2.urlopen('https://www.triplemining.com').read()
		matches = re.search('([0-9.]+) GHash', data)
		self.rate = float(matches.group(1)) * 1000000000.0

#-------------------------------------------------------------------------------
# Module Setup
#-------------------------------------------------------------------------------

_pool_class_map = {
	'arsbitcoin': ArsBitcoinPool,
	'bitcoins.lc': BitCoinsLCPool,
	'bitpit': BitPitPool,
	'btcguild': BTCGuildPool,
	'eclipsemc': EclipseMCPool,
	'eligius': EligiusPool,
	'mineco.in': MineCoinPool,
	'mtred': MtRedPool,
	'ozco.in': OzCoinPool,
	'rfcpool': RFCPool,
	'triplemining': TripleMiningPool,
}
