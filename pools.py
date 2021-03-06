import json
import math
import re
import scipy.integrate
import time
import urllib2

import httplib2

_difficulty = (0, 0)
_pool_data = ({}, 0)

#-------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------

def get_difficulty():
	global _difficulty

	if time.time() - _difficulty[1] > 3600:
		difficulty = float(urllib2.urlopen('http://blockexplorer.com/q/getdifficulty').read())
		_difficulty = (difficulty, time.time())

	return _difficulty[0]

def get_pool_rate(pool):
	global _pool_data

	update_pool_data(pool)

	return _pool_data[0]['rates'][pool] if pool in _pool_data[0]['rates'] else 0.0

def get_pool_most_recent_block(pool):
	global _pool_data

	update_pool_data(pool)

	return _pool_data[0]['most_recent_block'][pool] if pool in _pool_data[0]['most_recent_block'] else {}

def update_pool_data(pool):
	global _pool_data

	if time.time() - _pool_data[1] > 120:
		try:
			h = httplib2.Http('.cache')
			response, content = h.request('http://bitcoin.calindora.com/api/pools/')

			pool_data = json.loads(content)
			_pool_data = (pool_data, time.time())
		except:
			pass

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

			pools[fields[0]] = (fields[1], fields[2], (float(fields[3]) / 100.0) if len(fields) > 3 else 0.0, priority)

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
				self.pools[pool] = _pool_class_map[pool](pool_data[0], pool_data[1], pool_data[2], pool_data[3])

	def get_best_pools(self):
		return sorted(self.pools.values(), key=lambda pool: (pool.utility, pool.priority), reverse=True)

#-------------------------------------------------------------------------------
# Pool Base Class
#-------------------------------------------------------------------------------

class Pool(object):
	def __init__(self, username, password, donation, priority):
		self.username = username
		self.password = password
		self.priority = priority
		self.rate = 1.0
		self.donation = donation

	@property
	def utility(self):
		return 1.0 * (1 - self.fee - self.donation)

	def update_data(self):
		self.rate = get_pool_rate(self.pident_name)

	def get_shares(self, start):
		return self.rate * (time.time() - start) / 2 ** 32

class ProportionalPool(Pool):
	@property
	def utility(self):
		try:
			self.update_data()
		except (ValueError, urllib2.HTTPError):
			pass

		blocks = get_pool_most_recent_block(self.pident_name)

		utility = 0.0

		for block_time, probability in sorted(blocks.items()):
			shares = self.get_shares(float(block_time))
			progress = max(shares, 1.0) / get_difficulty()
			utility += probability * scipy.integrate.quad((lambda x: (math.exp(progress - x) / x)), progress, 100.0)[0]

		return utility * (1 - self.fee - self.donation)

	def get_shares(self, start):
		hopper_bonus = 100.0 * 1000000000.0
		base_rate = (math.sqrt(2) * math.sqrt(50 * (hopper_bonus ** 2) + 13 * hopper_bonus * self.rate + 50 * (self.rate ** 2)) - 10 * hopper_bonus + 10 * self.rate) / 20
		rate = base_rate + hopper_bonus

		return rate * (time.time() - start) / 2 ** 32

#-------------------------------------------------------------------------------
# Unsupported Pools
#-------------------------------------------------------------------------------

# Bitcoinpool
# Uses a strange anti-hopping measure that needs to be evaluated.

# Slush and BTCMine
# Use a score-based systems that I have no fully evaluated for hopping
# potential, but should be nearly hop-proof.

#-------------------------------------------------------------------------------
# Fair Pools
#-------------------------------------------------------------------------------
# TODO: Figure out which pools give transaction fees back.

class ArsBitcoinPool(Pool):
	name = 'arsbitcoin'
	pident_name = 'ArsBitcoin'
	servers = ['arsbitcoin.com:8344']
	fee = 0.0

class BitMinterPool(Pool):
	name = 'bitminter'
	pident_name = 'BitMinter'
	servers = ['mint.bitminter.com:8332']
	fee = 0.0

class BitPitPool(Pool):
	name = 'bitpit'
	pident_name = 'BitPit'
	servers = ['pool.bitp.it:8334']
	fee = 0.0

class BTCGuildPool(Pool):
	name = 'btcguild'
	pident_name = 'BTCGuild'
	servers = ['btcguild.com:8332']
	fee = 0.05

class EclipseMCPool(Pool):
	name = 'eclipsemc'
	pident_name = 'EclipseMC'
	servers = ['us.eclipsemc.com:8337', 'eu.eclipsemc.com:8337']
	fee = 0.01
	# EclipseMC is currently running with a 1% fee due to its parameters to the geometric scoring method.

class EligiusPool(Pool):
	name = 'eligius'
	pident_name = 'Eligius'
	servers = ['mining.eligius.st:8337']
	fee = 0.0

class MineCoinPool(Pool):
	name = 'mineco.in'
	pident_name = 'Mineco.in'
	servers = ['mineco.in:3000']
	fee = 0.0

class NoFeeMining(Pool):
	name = 'nofeemining'
	pident_name = 'NoFeeMining'
	servers = ['nofeemining.appspot.com:80']
	fee = 0.0

#-------------------------------------------------------------------------------
# Proportional Pools
#-------------------------------------------------------------------------------

class BitCoinsLCPool(ProportionalPool):
	name = 'bitcoins.lc'
	pident_name = 'Bitcoins.lc'
	servers = ['bitcoins.lc:8080']
	fee = 0.0

class MtRedPool(ProportionalPool):
	name = 'mtred'
	pident_name = 'MtRed'
	servers = ['mtred.com:8337']
	fee = 0.0

class OzCoinPool(ProportionalPool):
	name = 'ozco.in'
	pident_name = 'Ozco.in'
	servers = ['ozco.in:8332']
	fee = 0.0

class TripleMiningPool(ProportionalPool):
	name = 'triplemining'
	pident_name = 'TripleMining'
	servers = ['eu.triplemining.com:8344']
	fee = 0.01

#-------------------------------------------------------------------------------
# Module Setup
#-------------------------------------------------------------------------------

_pool_class_map = {
	'arsbitcoin': ArsBitcoinPool,
	'bitcoins.lc': BitCoinsLCPool,
	'bitminter': BitMinterPool,
	'bitpit': BitPitPool,
	'btcguild': BTCGuildPool,
	'eclipsemc': EclipseMCPool,
	'eligius': EligiusPool,
	'mineco.in': MineCoinPool,
#	'mtred': MtRedPool,
	'nofeemining': NoFeeMining,
	'ozco.in': OzCoinPool,
	'triplemining': TripleMiningPool,
}
