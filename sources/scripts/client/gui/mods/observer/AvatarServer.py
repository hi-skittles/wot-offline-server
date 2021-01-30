import BigWorld
import AccountCommands
import cPickle
import zlib
import functools
import Math
import BattleReplay

from BotPoint import BotPoint

from items.vehicles import VehicleDescr, makeIntCompactDescrByID
from gun_rotation_shared import encodeGunAngles
from constants import ARENA_UPDATE, ARENA_PERIOD, VEHICLE_SIEGE_STATE, VEHICLE_SETTING
from helpers.CallbackDelayer import CallbackDelayer

from . import LOG_DEBUG, IS_PHYSICS, override
from .VehicleMover import VehicleMover


def packVehicleArenaInfo(vehicleID, 
			vDesc,
			name='', 
			team=1, 
			isAlive=True, 
			isAvatarReady=False, 
			isTeamKiller=False, 
			accountDBID=1, 
			clanAbbrev='', 
			clanDBID=0, 
			prebattleID=0, 
			isPrebattleCreator=False, 
			forbidInBattleInvitations=False, 
			events={}, 
			igrType=0, 
    		personalMissionIDs=[],
			personalMissionInfo={},
		 	ranked=None, 
			outfitCD='',
			avatarSessionID='',
			wtr=0,
			fakeName='Игорь',
			badges=((), ()),
			overriddenBadge='',
			maxHealth=None):

	compactDescr = vDesc.makeCompactDescr()
	return zlib.compress(cPickle.dumps(([
		vehicleID, # 0
		compactDescr, # 1
		name, # 2
		team, # 3
		isAlive, # 4
		isAvatarReady, # 5 
		isTeamKiller, # 6
		accountDBID, # 7
		clanAbbrev, # 8
		clanDBID, # 9
		prebattleID, # 10
		isPrebattleCreator, # 11 
		forbidInBattleInvitations, # 12 
		events, # 13
		igrType, # 14
		personalMissionIDs, # 15
		personalMissionInfo, # 16
		ranked, # 17
		outfitCD, # 18
		avatarSessionID, # 19
		wtr, # 20
		fakeName, # 21
		badges, # 22
		overriddenBadge, # 23
		vDesc.maxHealth if maxHealth is None else maxHealth, # 24
	])))

def getVehicleDesc(compactDescr, isTop):
	vDesc = VehicleDescr(compactDescr=compactDescr)
	if isTop:
		vType = vDesc.type
		turrent = vType.turrets[-1][-1]
		gun = turrent['guns'][-1]

		gunID = makeIntCompactDescrByID('vehicleGun',gun.id[0],gun.id[1])
		turretID = makeIntCompactDescrByID('vehicleTurret',turrent.id[0],turrent.id[1])
		engineID = makeIntCompactDescrByID('vehicleEngine',vType.engines[-1].id[0],vType.engines[-1].id[1])
		radioID = makeIntCompactDescrByID('vehicleRadio',vType.radios[-1].id[0],vType.radios[-1].id[1])
		chassisID = makeIntCompactDescrByID('vehicleChassis',vType.chassis[-1].id[0],vType.chassis[-1].id[1])

		vDesc.installComponent(chassisID)
		vDesc.installComponent(engineID)
		vDesc.installTurret(turretID,gunID)
		vDesc.installComponent(radioID)
	return vDesc

def getEntityDesc(vDesc, team, name):
	return {
		'publicInfo': {
			'compDescr': vDesc.makeCompactDescr(),
			'name': name,
			'team': team,
			'prebattleID': 0,
			'marksOnGun': 0,
			'index': 0,
			'outfit': '',
			'crewGroup': 0,
			'commanderSkinID': 0,
			'maxHealth': vDesc.maxHealth,
		},
		'gunAnglesPacked': encodeGunAngles(0, 0, vDesc.gun.pitchLimits['absolute']),
		'health': vDesc.maxHealth,
		'isCrewActive': True,
		'isAlive': True,
		'isPlayer': False,
		'steeringAngle': 0,
		'isStrafing': False,
		'siegeState': VEHICLE_SIEGE_STATE.DISABLED,
		'engineMode': (0, 0),
		'damageStickers': [],
		'publicStateModifiers': ()
	}


def callback_wrapper(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		instant = kwargs.pop('instant', False)
		timeout = kwargs.pop('timeout', 0.0)
		call = functools.partial(func, *args, **kwargs)
		if instant:
			return call()
		return BigWorld.callback(timeout, call)
	return wrapper


class VehicleController(object):
	def __init__(self, vehicleID, server):
		self.server = server
		self.vehicleID = vehicleID
		self.mover = VehicleMover(vehicleID, server)

	def start(self, physics):
		if IS_PHYSICS:
			self.mover.setPhysics(physics)
			self.mover.start()

	def stop(self):
		if self.mover.isStarted:
			self.mover.stop()

	def destroy(self):
		self.stop()
		BigWorld.destroyEntity(self.vehicleID)
		self.vehicleID = None

	def moveWith(self, flag):
		if self.mover.isStarted:
			self.mover.moveWith(flag)

	def setCruiseControlMode(self, mode):
		if self.mover.isStarted:
			self.mover.setCruiseControlMode(mode)

	def pickup(self):
		if self.mover.isStarted:
			self.mover.pickup()

class AvatarServer(CallbackDelayer):
	def __init__(self, avatar):
		super(AvatarServer, self).__init__()
		self.avatar = avatar

		# vehicleID: VehicleController
		self.vehicles = {}

		self.currentShell = None

		self.voipController = self

	@property
	def vehicle(self):
		return self.vehicles[self.playerVehicleID]

	@property
	def vehicleEntity(self):
		return BigWorld.entity(self.playerVehicleID)

	@property
	def playerVehicleID(self):
		return self.avatar.playerVehicleID

	def updateVehiclePosition(self, vehicleID, position, rotation, speed, rspeed):
		'''
		Called by VehicleMover
		Notifies Avatar about vehicle movement (when vehicle owned by player)
		'''
		if vehicleID == self.playerVehicleID:
			self.avatar.updateOwnVehiclePosition(position, rotation, speed, rspeed)

	def _setAvatarProperty(self, name, value):
		prev = getattr(self.avatar, name)
		setattr(self.avatar, name, value)
		if hasattr(self.avatar, 'set_' + name):
			func = getattr(self.avatar, 'set_' + name)
			func(prev)

	def _getBotPoint(self):
		for udo in BigWorld.userDataObjects.values():
			if isinstance(udo, BotPoint):
				return udo.position, (udo.roll, udo.pitch, udo.yaw)
		return (0, 100 if IS_PHYSICS else -1000, 0), (0, 0, 0)

	def _onTick(self):
		try:
			vDesc = self.vehicleEntity.typeDescriptor
			turretDescr, gunDescr = vDesc.turrets[0]
			for shot in gunDescr.shots:
				self.avatar.updateVehicleAmmo(
					self.playerVehicleID, 
					shot.shell.compactDescr, 
					int(gunDescr.maxAmmo/len(gunDescr.shots)), 
					gunDescr.clip[0], 
					gunDescr.reloadTime, 
					gunDescr.reloadTime
				)
				if self.currentShell is None:
					self.currentShell = shot.shell.compactDescr
			self.avatar.updateVehicleSetting(self.playerVehicleID, VEHICLE_SETTING.CURRENT_SHELLS, self.currentShell)
			# turretYaw, gunPitch = self.vehicleEntity.getAimParams()
			# self.avatar.updateTargetingInfo(turretYaw, gunPitch, turretDescr.rotationSpeed, gunDescr.rotationSpeed, 1.0, 0.0, 0.0, 0.0, gunDescr.aimingTime)
		finally:
			return 0.1

	@callback_wrapper
	def startVehicle(self, vehicleID, physics):
		self.vehicles[vehicleID].start(physics)

	# BASE
	@callback_wrapper
	def setDevelopmentFeature(self, name, *args):
		if name == 'pickup':
			self.vehicle.pickup()

	@callback_wrapper
	def addBotToArena(self, compactDescr, team, name, pos=(0., 0., 0.), group=0):
		vDesc = getVehicleDesc(compactDescr, False)
		position, rotation = self._getBotPoint()
		vehicleID = BigWorld.createEntity('Vehicle', self.avatar.spaceID, 0, position, rotation, getEntityDesc(vDesc, team, name))
		self.vehicles[vehicleID] = VehicleController(vehicleID, self)
		BigWorld.callback(0.0, lambda: self.avatar.updateArena(ARENA_UPDATE.VEHICLE_ADDED, packVehicleArenaInfo(vehicleID, vDesc, name=name, team=team)))

	@callback_wrapper
	def leaveArena(self, statistics=None):
		LOG_DEBUG('AvatarServer.leaveArena')
		BigWorld.quit()

	@callback_wrapper
	def doCmdStr(self, requestID, cmd, string):
		LOG_DEBUG('doCmdStr', requestID, cmd, string)
		if cmd == AccountCommands.CMD_GET_AVATAR_SYNC:
			self.avatar.onCmdResponse(requestID, 0, '')

	@callback_wrapper
	def doCmdIntArr(self, requestID, cmd, arr):
		LOG_DEBUG('doCmdIntArr', requestID, cmd, arr)
		if cmd in (AccountCommands.CMD_ADD_INT_USER_SETTINGS, AccountCommands.CMD_DEL_INT_USER_SETTINGS):
			self.avatar.onCmdResponse(requestID, 0, '')

	@callback_wrapper
	def setClientReady(self):
		self._setAvatarProperty('isGunLocked', False)
		self._setAvatarProperty('ownVehicleAuxPhysicsData', 0)
		self._setAvatarProperty('ownVehicleGear', 0)
		self.avatar.syncVehicleAttrs({
			'circularVisionRadius': BigWorld.player().vehicleTypeDescriptor.turret.circularVisionRadius
		})

		self.avatar.updateArena(ARENA_UPDATE.AVATAR_READY, cPickle.dumps(self.playerVehicleID))
		self.avatar.updateArena(ARENA_UPDATE.PERIOD, zlib.compress(cPickle.dumps(([ARENA_PERIOD.BATTLE, 0, 0, []]))))
		self.delayCallback(0.1, self._onTick)

	@callback_wrapper
	def vehicle_moveWith(self, flag):
		self.vehicle.moveWith(flag)

	@callback_wrapper
	def vehicle_changeSetting(self, code, value):
		if code == VEHICLE_SETTING.CURRENT_SHELLS:
			self.currentShell = value
		self.avatar.updateVehicleSetting(self.playerVehicleID, code, value)

	@callback_wrapper
	def vehicle_trackWorldPointWithGun(self, shotPoint):
		pass

	@callback_wrapper
	def vehicle_stopTrackingWithGun(self, turretYaw, gunPitch):
		pass

	@callback_wrapper
	def vehicle_shoot(self):
		self.vehicleEntity.showShooting(0)

	# CELL
	@callback_wrapper
	def setRemoteCamera(self, data):
		self._setAvatarProperty('remoteCamera', data)
		
	@callback_wrapper
	def autoAim(self, vehicleID, magnetic):
		pass

	@callback_wrapper
	def switchObserverFPV(self, bool):
		pass

	@callback_wrapper
	def setCruiseControlMode(self, mode):
		self.vehicle.setCruiseControlMode(mode)

	@callback_wrapper
	def bindToVehicle(self, vehicleID):
		if self.avatar.playerVehicleID != vehicleID:
			LOG_DEBUG('AvatarServer.bindToVehicle', vehicleID)
			self._setAvatarProperty('playerVehicleID', vehicleID)
			self.avatar.onVehicleChanged()

	# BWProto
	@callback_wrapper
	def invalidateMicrophoneMute(self):
		pass

	@callback_wrapper
	def moveTo(self, pos):
		pass

	# VOIP
	@callback_wrapper
	def setMicrophoneMute(self, isMuted, force=False):
		pass
