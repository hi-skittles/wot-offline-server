import BigWorld
import Math
import time
import sys

from constants import ARENA_PERIOD
from helpers.CallbackDelayer import CallbackDelayer, TimeDeltaMeter


REPLAY_TIME_MARK_CLIENT_READY = 2147483648L
REPLAY_TIME_MARK_REPLAY_FINISHED = 2147483649L
REPLAY_TIME_MARK_CURRENT_TIME = 2147483650L


class ReplayController(TimeDeltaMeter, CallbackDelayer):
	def __init__(self, replayController):
		CallbackDelayer.__init__(self)
		TimeDeltaMeter.__init__(self, time.clock)

		self._isStarted = False
		self._isRecording = False
		self._wg_replayController = replayController

	def __getattribute__(self, name):
		try:
			return super(ReplayController, self).__getattribute__(name)
		except AttributeError:
			return getattr(self._wg_replayController, name)

	def startPlayback(self, fileName):
		self._isStarted = True
		self._isSimulation = True
		self._battleStartTime = 0.0
		self._battleFinishTime = 60.0 * 60.0
		self.currentTime = 0.0

		self.isControllingCamera = False
		self.hasMods = False
		self.fileName = fileName
		self.controlMode = 'video'
		self.fps = 0.0
		self.ping = 0.0
		self.isLaggingNow = False
		self._isRecording = True
		self.playbackSpeed = 1.0
		self.clientVersion = BigWorld.wg_getProductVersion()

		self.gunMarkerDiameter = 0.0
		self.gunMarkerPosition = Math.Vector3()
		self.gunMarkerDirection = Math.Vector3()
		self.gunRotatorTargetPoint = Math.Vector3()

		self.delayCallback(0.0, self._update)

		return True

	def __set_isControllingCamera(self, value):
		# Throwing an exception to prevent losing the camera control
		# assert not value, 'Replay simulator has not saved camera!'
		pass

	isControllingCamera = property(lambda self: False, __set_isControllingCamera)

	@property
	def isTimeWarpInProgress(self):
		return False

	@property
	def isClientReady(self):
		return True

	@property
	def isRecording(self):
		return self._isRecording

	@property
	def isServerAim(self):
		return False

	@property
	def isOfflinePlaybackMode(self):
		return True

	def __set_playerVehicleID(self, value):
		if not self._isStarted:
			self._wg_replayController.playerVehicleID = value

	def __get_playerVehicleID(self):
		if self._isStarted:
			return BigWorld.player().playerVehicleID
		return self._wg_replayController.playerVehicleID

	playerVehicleID = property(__get_playerVehicleID, __set_playerVehicleID)

	def stop(self, delete):
		self._isStarted = False

	def _update(self):
		if self._isStarted:
			self.currentTime += self.measureDeltaTime() * self.playbackSpeed
			if self.currentTime > self._battleFinishTime:
				self._battleFinishTime = self.currentTime + 10.0
			return 0.0

	def beginTimeWarp(self, time):
		self.currentTime = time
		BigWorld.callback(0.0, self.warpFinishedCallback)
		return False

	def isPlaying(self): 
		return self._isStarted

	def getTimeMark(self, mark): 
		if mark == REPLAY_TIME_MARK_CURRENT_TIME:
			return self.currentTime
		if mark == REPLAY_TIME_MARK_REPLAY_FINISHED:
			return self._battleFinishTime
		if mark == REPLAY_TIME_MARK_CLIENT_READY:
			return self._battleStartTime

	def confirmDlgAccepted(self, *args, **kwargs): pass
	def getAimClipPosition(self, *args, **kwargs): pass
	def getArcadeGunMarkerSize(self, *args, **kwargs): pass
	def getArenaInfoStr(self, *args, **kwargs): pass
	def getAutoStartFileName(self, *args, **kwargs): pass
	def getCallbackHandler(self, *args, **kwargs): pass
	def getConsumableSlotCooldownAmount(self, *args, **kwargs): pass
	def getGunReloadAmountLeft(self, *args, **kwargs): pass
	def getSPGGunMarkerParams(self, *args, **kwargs): pass
	def isEffectNeedToPlay(self, *args, **kwargs): pass
	def isFileCompressed(self, *args, **kwargs): pass
	def onAmmoButtonPressed(self, *args, **kwargs): pass
	def onBattleChatMessage(self, *args, **kwargs): pass
	def onClientReady(self, *args, **kwargs): pass
	def onCommonSfwUnloaded(self, *args, **kwargs): pass
	def onLockTarget(self, *args, **kwargs): pass
	def onServerAim(self, *args, **kwargs): pass
	def onSetCruiseMode(self, *args, **kwargs): pass
	def onSetEquipmentID(self, *args, **kwargs): pass
	def onSniperMode(self, *args, **kwargs): pass
	def registerWotReplayFileExtension(self, *args, **kwargs): pass
	def resetArenaPeriod(self, *args, **kwargs): pass
	def serializeCallbackData(self, *args, **kwargs): pass
	def setActiveConsumableSlot(self, *args, **kwargs): pass
	def setAimClipPosition(self, *args, **kwargs): pass
	def setArcadeGunMarkerSize(self, *args, **kwargs): pass
	def setArenaInfoStr(self, *args, **kwargs): pass
	def setArenaStatisticsStr(self, *args, **kwargs): pass
	def setDataCallback(self, *args, **kwargs): pass
	def setGunReloadTime(self, *args, **kwargs): pass
	def setResultingFileName(self, *args, **kwargs): pass
	def setSPGGunMarkerParams(self, *args, **kwargs): pass
	def setupAvatarMethodExcludeFilter(self, *args, **kwargs): pass
	def setupStreamExcludeFilter(self, *args, **kwargs): pass
	def startRecording(self, *args, **kwargs): pass

