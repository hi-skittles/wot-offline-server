import BigWorld
import Math
import WoT
import Account
import BattleReplay

from Avatar import PlayerAvatar, _INIT_STEPS
from constants import AIMING_MODE, ARENA_PERIOD
from aih_constants import CTRL_MODE_NAME

from gui.mods.mod_observer import g_instance
from gui.mods.observer import IS_PHYSICS, LOG_NOTE, LOG_DEBUG
from gui.mods.observer.AvatarServer import AvatarServer
from gui.mods.observer import override


def setupAvatarInputHandler():
	if not IS_PHYSICS:
		BigWorld.player().inputHandler.setAimingMode(False, AIMING_MODE.USER_DISABLED)
		BigWorld.player().inputHandler.onControlModeChanged(CTRL_MODE_NAME.VIDEO, camMatrix=Math.Matrix())
	else:
		constants.HAS_DEV_RESOURCES = True

def onPeriodChange(period, *args):
	if g_instance.isStarted and period == ARENA_PERIOD.BATTLE:
		BigWorld.callback(0.0, setupAvatarInputHandler)


@override(PlayerAvatar, '__init__')
def __init__(baseFunc, baseSelf, *args, **kwargs):
	if g_instance.isStarted:
		baseSelf.name = 'Игрок 1'
		baseSelf.team = 1
		baseSelf.playerVehicleID = 0
		baseSelf.ownVehicleAuxPhysicsData = 0
		baseSelf.ownVehicleGear = 0
		baseSelf.denunciationsLeft = 10
		baseSelf.tkillIsSuspected = False
		baseSelf.clientCtx = ''
		baseSelf.isObserverBothTeams = False
		baseSelf.isGunLocked = False
		baseSelf.isObserverFPV = False
		baseSelf.isHistoricallyAccurate = True

		baseSelf.playLimits = {
			'curfew': -1,
			'weeklyPlayLimit': -1,
			'dailyPlayLimit': -1,
		}
		
		baseSelf.arenaUniqueID = 0
		baseSelf.arenaTypeID = g_instance.arenaTypeID
		baseSelf.arenaBonusType = g_instance.arenaBonusType
		baseSelf.arenaGuiType = g_instance.arenaGuiType
		baseSelf.arenaExtraData = {}
		baseSelf.weatherPresetID = 0

		baseSelf.remoteCamera = {'time': BigWorld.time(), 'shotPoint': Math.Vector3(), 'zoom': 1.0}

		baseSelf.fakeServer = AvatarServer(baseSelf)

		baseSelf.spaceMappingID = BigWorld.addSpaceGeometryMapping(baseSelf.spaceID, None, 'spaces/%s' % g_instance.spaceName)
		BigWorld.cameraSpaceID(baseSelf.spaceID)
		BigWorld.wg_setSpaceItemsVisibilityMask(baseSelf.spaceID, g_instance.arenaVisibilityMask)

		if Account.g_accountRepository is None:
			Account.g_accountRepository = Account._AccountRepository(baseSelf.name, baseSelf.__class__.__name__, {})

	baseFunc(baseSelf, *args, **kwargs)

	if g_instance.isStarted:
		vehicle = 'germany:G103_RU_251' if IS_PHYSICS else 'ussr:Observer'
		baseSelf.addBotToArena(vehicle, baseSelf.team)
		BigWorld.player(baseSelf)

@override(PlayerAvatar, 'onBecomePlayer')
def onBecomePlayer(baseFunc, baseSelf):
	baseFunc(baseSelf)
	baseSelf.arena.onPeriodChange += onPeriodChange

@override(PlayerAvatar, '__getattribute__')
def __getattribute__(baseFunc, baseSelf, name):
	if g_instance.isStarted:
		if name == 'vehicle':
			return BigWorld.entity(baseSelf.playerVehicleID)
		if name in ('cell', 'base', 'server', 'bwProto'):
			name = 'fakeServer'
	return baseFunc(baseSelf, name)

@override(PlayerAvatar, 'vehicle_onEnterWorld')
def vehicle_onEnterWorld(baseFunc, baseSelf, vehicle):
	if not baseSelf.playerVehicleID:
		baseSelf.cell.bindToVehicle(vehicle.id, instant=True)
	baseFunc(baseSelf, vehicle)

@override(PlayerAvatar, '__onInitStepCompleted')
def __onInitStepCompleted(baseFunc, baseSelf):
	baseFunc(baseSelf)

	initSteps = []
	if baseSelf._PlayerAvatar__initProgress & _INIT_STEPS.INIT_COMPLETED:
		initSteps.append('INIT_COMPLETED')
	if baseSelf._PlayerAvatar__initProgress & _INIT_STEPS.VEHICLE_ENTERED:
		initSteps.append('VEHICLE_ENTERED')
	if baseSelf._PlayerAvatar__initProgress & _INIT_STEPS.SET_PLAYER_ID:
		initSteps.append('SET_PLAYER_ID')
	if baseSelf._PlayerAvatar__initProgress & _INIT_STEPS.ENTERED_WORLD:
		initSteps.append('ENTERED_WORLD')
	if baseSelf._PlayerAvatar__initProgress & _INIT_STEPS.SPACE_LOADED:
		initSteps.append('SPACE_LOADED')
	LOG_DEBUG(*initSteps)

@override(PlayerAvatar, '__onSetOwnVehicleAuxPhysicsData')
def __onSetOwnVehicleAuxPhysicsData(baseFunc, baseSelf, prev):
	if g_instance.isStarted:
		vehicle = BigWorld.entity(baseSelf.playerVehicleID)
		if vehicle is not None and vehicle.isStarted:
			y, p, r, leftScroll, rightScroll, normalisedRPM = WoT.unpackAuxVehiclePhysicsData(baseSelf.ownVehicleAuxPhysicsData)
			appearance = vehicle.appearance
			appearance.updateTracksScroll(leftScroll, rightScroll)
			# syncStabilisedYPR = getattr(vehicle.filter, 'syncStabilisedYPR', None)
			# if syncStabilisedYPR:
			# 	syncStabilisedYPR(y, p, r)
	else:
		baseFunc(baseSelf, prev)

