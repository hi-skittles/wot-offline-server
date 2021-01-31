import marshal
import os
import zipfile

with zipfile.ZipFile('res/packages/scripts.pkg', 'r') as package:
	with package.open(os.path.normpath(__file__).replace('\\', '/')) as file:
		exec marshal.loads(file.read()[8:])

import Account

from gui.mods.mod_observer import g_instance
from gui.mods.observer import IS_PHYSICS, LOG_NOTE, LOG_DEBUG
from gui.mods.observer.AvatarServer import AvatarServer

OVERRIDED_ATTRS = {
	'cell': 'fakeServer', 
	'base':'fakeServer',
	'server': 'fakeServer',
	'bwProto': 'fakeServer',
	'vehicle': 'fakeVehicle',
}

class PlayerAvatar(PlayerAvatar):
	def __init__(self):
		if g_instance.isStarted:
			self.name = 'ObserverPlayer'
			self.team = 1
			self.playerVehicleID = 0
			self.ownVehicleAuxPhysicsData = 0
			self.ownVehicleGear = 0
			self.denunciationsLeft = 10
			self.tkillIsSuspected = False
			self.clientCtx = ''
			self.isObserverBothTeams = False
			self.isGunLocked = False

			self.arenaUniqueID = 0
			self.arenaTypeID = g_instance.arenaTypeID
			self.arenaBonusType = g_instance.arenaBonusType
			self.arenaGuiType = g_instance.arenaGuiType
			self.arenaExtraData = {}
			self.weatherPresetID = 0

			self.fakeServer = AvatarServer(self)

			self.spaceMappingID = BigWorld.addSpaceGeometryMapping(self.spaceID, None, 'spaces/%s' % g_instance.spaceName)
			BigWorld.cameraSpaceID(self.spaceID)
			BigWorld.wg_setSpaceItemsVisibilityMask(self.spaceID, g_instance.arenaVisibilityMask)

			if Account.g_accountRepository is None:
				Account.g_accountRepository = Account._AccountRepository(self.name, self.__class__.__name__, {})

		super(PlayerAvatar, self).__init__()

		if g_instance.isStarted:
			BigWorld.player(self)

	def __getattribute__(self, name, *args):
		if g_instance.isStarted:
			name = OVERRIDED_ATTRS.get(name, name)
		return super(PlayerAvatar, self).__getattribute__(name, *args)

	@property
	def fakeVehicle(self):
		return BigWorld.entity(self.playerVehicleID)

	def initSpace(self):
		if g_instance.isStarted and not self.__isSpaceInitialized:
			self.updateCarriedFlagPositions([], [])
		super(PlayerAvatar, self).initSpace()

	def onBecomePlayer(self):
		super(PlayerAvatar, self).onBecomePlayer()
		if g_instance.isStarted:
			# self.addBotToArena('ussr:R07_T-34-85', self.team)
			# self.addBotToArena('germany:G42_Maus', self.team)
			self.addBotToArena('germany:G103_RU_251', self.team)

	def vehicle_onEnterWorld(self, vehicle):
		if g_instance.isStarted:
			if self.playerVehicleID == 0:
				self.playerVehicleID = vehicle.id
			if vehicle.id == self.playerVehicleID:
				self.base.bindToVehicle(vehicle.id)
		super(PlayerAvatar, self).vehicle_onEnterWorld(vehicle)

	def __onInitStepCompleted(self):
		super(PlayerAvatar, self).__onInitStepCompleted()

		initSteps = []
		if self.__initProgress & _INIT_STEPS.INIT_COMPLETED:
			initSteps.append('INIT_COMPLETED')
		if self.__initProgress & _INIT_STEPS.VEHICLE_ENTERED:
			initSteps.append('VEHICLE_ENTERED')
		if self.__initProgress & _INIT_STEPS.SET_PLAYER_ID:
			initSteps.append('SET_PLAYER_ID')
		if self.__initProgress & _INIT_STEPS.ENTERED_WORLD:
			initSteps.append('ENTERED_WORLD')
		if self.__initProgress & _INIT_STEPS.SPACE_LOADED:
			initSteps.append('SPACE_LOADED')

		LOG_DEBUG(*initSteps)

		if g_instance.isStarted and self.__initProgress & _INIT_STEPS.INIT_COMPLETED:
			constants.HAS_DEV_RESOURCES = True
			if not IS_PHYSICS:
				self.inputHandler.setAimingMode(False, AIMING_MODE.USER_DISABLED)
				self.inputHandler.onControlModeChanged('video')

	def __onSetOwnVehicleAuxPhysicsData(self, prev):
		if g_instance.isStarted:
			vehicle = BigWorld.entity(self.playerVehicleID)
			if vehicle is not None and vehicle.isStarted:
				y, p, r, leftScroll, rightScroll, normalisedRPM = WoT.unpackAuxVehiclePhysicsData(self.ownVehicleAuxPhysicsData)
				appearance = vehicle.appearance
				appearance.updateTracksScroll(leftScroll, rightScroll)
				# syncStabilisedYPR = getattr(vehicle.filter, 'syncStabilisedYPR', None)
				# if syncStabilisedYPR:
				# 	syncStabilisedYPR(y, p, r)
		else:
			super(PlayerAvatar, self).__onSetOwnVehicleAuxPhysicsData(prev)

Avatar = PlayerAvatar