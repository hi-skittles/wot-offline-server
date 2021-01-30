import BigWorld
import functools
import AccountCommands
import cPickle

from ._constants import CHAT_ACTION_DATA
from .logging import *

BASE_REQUESTS = {}

class FakeServer(object):
	def __call__(self, *args, **kwargs):
		if not self.__isMuted:
			LOG_DEBUG('%s ( %s, %s )' % (self.__name, args, kwargs))
			
	def __init__(self, name='Server', isMuted=False):
		super(FakeServer, self).__init__()
		self.__isMuted = isMuted
		self.__name = name
			
	def __getattr__(self, name):
		try:
			return super(FakeServer, self).__getattribute__(name)
		except AttributeError:
			return FakeServer(name='%s.%s' % (self.__name, name), isMuted=self.__isMuted)

	def chatCommandFromClient(self, requestID, action, channelID, int64Arg, int16Arg, stringArg1, stringArg2):
		# chatActionData = CHAT_ACTION_DATA.copy()
		# chatActionData['requestID'] = requestID
		# chatActionData['action'] = action
		# BigWorld.player().onChatAction(chatActionData)
		pass

	def doCmdStr(self, requestID, cmd, str):
		LOG_DEBUG('Server.doCmdStr', requestID, str)
		self.__doCmd(requestID, cmd, str)

	def doCmdIntStr(self, requestID, cmd, int, str):
		LOG_DEBUG('Server.doCmdIntStr', requestID, cmd, int, str)
		self.__doCmd(requestID, cmd, int, str)

	def doCmdInt3(self, requestID, cmd, int1, int2, int3):
		LOG_DEBUG('Server.doCmdInt3', requestID, cmd, int1, int2, int3)
		self.__doCmd(requestID, cmd, int1, int2, int3)

	def doCmdInt4(self, requestID, cmd, int1, int2, int3, int4):
		LOG_DEBUG('Server.doCmdInt4', requestID, cmd, int1, int2, int3, int4)
		self.__doCmd(requestID, cmd, int1, int2, int3, int4)

	def doCmdInt2Str(self, requestID, cmd, int1, int2, str):
		LOG_DEBUG('Server.doCmdInt2Str', requestID, cmd, int1, int2, str)
		self.__doCmd(requestID, cmd, int1, int2, str)

	def doCmdIntArr(self, requestID, cmd, arr):
		LOG_DEBUG('Server.doCmdIntArr', requestID, cmd, arr)
		self.__doCmd(requestID, cmd, arr)

	def doCmdIntArrStrArr(self, requestID, cmd, intArr, strArr):
		LOG_DEBUG('Server.doCmdIntArrStrArr', requestID, cmd, intArr, strArr)
		self.__doCmd(requestID, cmd, intArr, strArr)

	def __doCmd(self, requestID, cmd, *args):
		cmdCall = BASE_REQUESTS.get(cmd)
		if cmdCall:
			requestID, resultID, errorStr, ext = cmdCall(requestID, *args)
		else:
			LOG_DEBUG('Server.requestFail', requestID, cmd, args)
			requestID, resultID, errorStr, ext = requestID, AccountCommands.RES_FAILURE, '', None
			
		if ext is not None:
			callback = functools.partial(BigWorld.player().onCmdResponseExt, requestID, resultID, errorStr, cPickle.dumps(ext))
		else:
			callback = functools.partial(BigWorld.player().onCmdResponse, requestID, resultID, errorStr)
		
		BigWorld.callback(0.0, callback)