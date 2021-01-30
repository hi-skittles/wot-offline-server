import BigWorld
import functools
import AccountCommands
import zlib
import cPickle
import game
import ResMgr

from collections import namedtuple

from .logging import *
from .server import *
from ._constants import *
from .data import *
from .utils import *

RequestResult = namedtuple('RequestResult', ['resultID', 'errorStr', 'data'])

def baseRequest(cmdID):
	def wrapper(func):
		def requester(requestID, *args):
			result = func(requestID, *args)
			return requestID, result.resultID, result.errorStr, result.data
		BASE_REQUESTS[cmdID] = requester
		return func
	return wrapper

def packStream(requestID, data):
	data = zlib.compress(cPickle.dumps(data))
	desc = cPickle.dumps((len(data), zlib.crc32(data)))
	return functools.partial(game.onStreamComplete, requestID, desc, data)

@baseRequest(AccountCommands.CMD_COMPLETE_TUTORIAL)
def completeTutorial(requestID, revision, dataLen, dataCrc):
	return RequestResult(AccountCommands.RES_SUCCESS, '', {})

@baseRequest(AccountCommands.CMD_SYNC_DATA)
def syncData(requestID, revision, crc, _):
	data = {'rev':revision + 1, 'prevRev': revision}

	# data.update(cPickle.loads(ResMgr.openSection('helpers/offhangar/persistentCache.pickle').asBinary))
	
	data.update(getOfflineInventory())
	data.update(getOfflineStats())
	data.update(getOfflineQuestsProgress())
	return RequestResult(AccountCommands.RES_SUCCESS, '', data)

@baseRequest(AccountCommands.CMD_SYNC_SHOP)
def syncShop(requestID, revision, dataLen, dataCrc):
	data = {'rev':revision + 1, 'prevRev': revision}
	data.update(getOfflineShop())
	BigWorld.callback(REQUEST_CALLBACK_TIME, packStream(requestID, data))
	return RequestResult(AccountCommands.RES_STREAM, '', None)

@baseRequest(AccountCommands.CMD_SYNC_DOSSIERS)
def syncDossiers(requestID, revision, maxChangeTime, _):
	BigWorld.callback(REQUEST_CALLBACK_TIME, packStream(requestID, (revision + 1, [])))
	return RequestResult(AccountCommands.RES_STREAM, '', None)
