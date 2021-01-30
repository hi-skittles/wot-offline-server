import os
import time
import json
import cPickle

from Account import _AccountRepository
from account_helpers.AccountSyncData import AccountSyncData
from account_helpers.SyncController import SyncController

from .utils import override, jsonDump
from .logging import LOG_DEBUG
from ._constants import IS_REQUEST_CATCHING

SYNC_DUMPS_RESPONCE = os.path.abspath('syncDumps/onSyncResponse')
SYNC_DUMPS_STREAM = os.path.abspath('syncDumps/onSyncStreamComplete')
PERSISTENT_CACHE = os.path.abspath('syncDumps/persistentCache')
INIT_SERVER_SETTINGS = os.path.abspath('syncDumps/initialServerSettings')


def dumpData(folder, data):
	if not os.path.exists(folder):
		os.makedirs(folder)

	name = time.time()

	with open(os.path.join(folder, '%s.json' % name), 'wb') as file:
		file.write(jsonDump(data, True))
	
	with open(os.path.join(folder, '%s.pickle' % name), 'wb') as file:
		file.write(cPickle.dumps(data))


if IS_REQUEST_CATCHING:
	@override(_AccountRepository, '__init__')
	def _AccountRepository_init(baseFunc, self, name, className, initialServerSettings):
		LOG_DEBUG(initialServerSettings)
		dumpData(INIT_SERVER_SETTINGS, initialServerSettings)
		return baseFunc(self, name, className, initialServerSettings)


	@override(SyncController, '__onSyncResponse')
	def SyncController_onSyncResponse(baseFunc, baseSelf, syncID, requestID, resultID, errorStr, ext={}):
		dumpData(SYNC_DUMPS_RESPONCE, {
			'syncID': syncID,
			'requestID': requestID,
			'resultID': resultID,
			'errorStr': errorStr,
			'ext': ext,
		})
		return baseFunc(baseSelf, syncID, requestID, resultID, errorStr, ext=ext)


	@override(SyncController, '__onSyncStreamComplete')
	def SyncController_onSyncStreamComplete(baseFunc, baseSelf, syncID, isSuccess, data):
		if isSuccess:
			try:
				dataUnpacked = cPickle.loads(data)
			except:
				try:
					dataUnpacked = cPickle.loads(zlib.decompress(data))
				except:
					dataUnpacked = None

			dumpData(SYNC_DUMPS_STREAM, {
				'syncID': syncID,
				'isSuccess': isSuccess,
				'data': data,
				'dataUnpacked': dataUnpacked,
			})
		return baseFunc(baseSelf, syncID, isSuccess, data)


	@override(AccountSyncData, 'updatePersistentCache')
	def AccountSyncData_updatePersistentCache(baseFunc, baseSelf, ext, isFullSync):
		result = baseFunc(baseSelf, ext, isFullSync)
		dumpData(PERSISTENT_CACHE, baseSelf._AccountSyncData__persistentCache.data)
		return result
