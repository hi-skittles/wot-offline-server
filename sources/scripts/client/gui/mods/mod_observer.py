import BigWorld
import ResMgr
import ArenaType
import Event
import GUI
import BattleReplay
import weakref
import physics_shared
import constants
import time
import game
import Keys

from frameworks.wulf import WindowLayer
from debug_utils import *
from helpers import i18n, dependency
from constants import ARENA_BONUS_TYPE, ARENA_GUI_TYPE, ARENA_BONUS_MASK
from arena_bonus_type_caps import ARENA_BONUS_TYPE_CAPS
from items.vehicles import g_list, VehicleDescr, getVehicleTypeCompactDescr

from constants import AIMING_MODE
from aih_constants import CTRL_MODE_NAME
from AvatarInputHandler import cameras
from ProjectileMover import collideDynamicAndStatic
from Vehicle import Vehicle

from skeletons.connection_mgr import IConnectionManager
from skeletons.gui.lobby_context import ILobbyContext

from gui import ClientHangarSpace
from gui.shared import events, EVENT_BUS_SCOPE
from gui.battle_control.arena_visitor import _ClientArenaVisitor

from gui.Scaleform.framework import g_entitiesFactories, ViewSettings, ScopeTemplates
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView

from gui.Scaleform.daapi.view.lobby.trainings import formatters
from gui.Scaleform.daapi.view.lobby.MinimapLobby import MinimapLobby
from gui.Scaleform.daapi.view.lobby.trainings.TrainingSettingsWindow import TrainingSettingsWindow
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.Scaleform.genConsts.PREBATTLE_ALIASES import PREBATTLE_ALIASES

from gui.prb_control.entities.training.legacy.ctx import TrainingSettingsCtx

from gui.shared.personality import ServicesLocator

try:
	from gui.modsListApi import g_modsListApi
except:
	LOG_CURRENT_EXCEPTION()
	g_modsListApi = None

from gui.mods.observer import LOG_NOTE, LOG_DEBUG, IS_AUTOSTART, override
from gui.mods.observer.ReplayController import ReplayController

ArenaType.init()

OBSERVER_ALIAS = 'mod_observer'
DEFAULT_SPACE_NAME = sorted(ArenaType.g_geometryNamesToIDs.keys())[0]
# DEFAULT_SPACE_NAME = '208_bf_epic_normandy'
# DEFAULT_SPACE_NAME = '00_tank_tutorial'
# DEFAULT_SPACE_NAME = '04_himmelsdorf'
# DEFAULT_SPACE_NAME = '06_ensk'
# DEFAULT_SPACE_NAME = '02_malinovka'
# DEFAULT_SPACE_NAME = '112_eiffel_tower_ctf'


class ObserverWindow(AbstractWindowView):
	def _populate(self):
		g_instance.onUpdate += self.onUpdate
		super(ObserverWindow, self)._populate()

	def _dispose(self):
		g_instance.onUpdate -= self.onUpdate
		super(ObserverWindow, self)._dispose()

	def onWindowClose(self):
		self.destroy()

	def showSelectMap(self):
		ServicesLocator.appLoader.getApp().loadView(SFViewLoadParams(PREBATTLE_ALIASES.TRAINING_SETTINGS_WINDOW_PY, PREBATTLE_ALIASES.TRAINING_SETTINGS_WINDOW_PY), {
			'isCreateRequest': True,
			'isObserverMod': True,
			'settings': TrainingSettingsCtx(),
		})

	def startLoading(self):
		g_instance.observerStart()

	def onUpdate(self):
		arenaTypeID = g_instance.arenaTypeID
		spaceName = g_instance.spaceName
		arenaName = g_instance.arenaName
		self.as_setArenaS(arenaName, spaceName)
		self.as_setLoadingEnabledS(True)

	def as_setArenaS(self, arenaName, spaceName):
		if self._isDAAPIInited():
			return self.flashObject.as_setArena(arenaName, '../maps/icons/map/stats/%s.png' % spaceName)

	def as_setLoadingEnabledS(self, isEnabled):
		if self._isDAAPIInited():
			return self.flashObject.as_setLoadingEnabled(isEnabled)


class ArenasCache:
	def __init__(self):
		self.cache = []
		self.spaces = {}

		for arenaTypeID, arenaType in ArenaType.g_cache.iteritems():
			try:
				if arenaType.gameplayName == 'ctf':
					nameSuffix = ''
				else:
					nameSuffix = i18n.makeString('#arenas:type/%s/name' % arenaType.gameplayName)
				self.cache.append({
					'label': '%s - %s' % (arenaType.name, nameSuffix) if len(nameSuffix) else arenaType.name,
					'name': arenaType.name,
					'arenaType': nameSuffix,
					'key': arenaTypeID,
					'size': arenaType.maxPlayersInTeam,
					'time': arenaType.roundLength / 60,
					'description': '',
					'icon': formatters.getMapIconPath(arenaType)
				})
			except Exception:
				LOG_ERROR('There is error while reading arenas cache',
						  arenaTypeID, arenaType)
				LOG_CURRENT_EXCEPTION()
				continue

		for space, cfg in ClientHangarSpace._readHangarSettings().items():
			space = space.replace('spaces/', '')
			id = len(self.spaces) | (1 << 32)
			self.spaces[id] = space
			self.cache.append({
				'label': space,
				'name': space,
				'arenaType': '',
				'key': id,
				'size': 1,
				'time': 1,
				'description': '',
				'icon': ''
			})

		self.cache = sorted(self.cache, key=lambda x: x['label'].lower() + x['name'].lower() )


class Observer:
	connectionManager = dependency.descriptor(IConnectionManager)
	lobbyContext = dependency.descriptor(ILobbyContext)

	def __init__(self):
		self.onUpdate = Event.Event()
		self.arenasCache = ArenasCache()

		self.spaceName = DEFAULT_SPACE_NAME
		self.arenaType = None
		self.arenaGuiType = ARENA_GUI_TYPE.RANDOM
		self.isStarted = False

		BattleReplay.g_replayCtrl._BattleReplay__replayCtrl = ReplayController(BattleReplay.g_replayCtrl._BattleReplay__replayCtrl)

		override(BigWorld, 'serverTime', self._BigWorld_serverTime)
		override(_ClientArenaVisitor, 'getTeamSpawnPoints', self._ClientArenaVisitor_getTeamSpawnPoints)
		override(MinimapLobby, 'setArena', self._MinimapLobby_setArena)
		override(TrainingSettingsWindow, '__init__', self._TrainingSettingsWindow_init)
		override(TrainingSettingsWindow, 'updateTrainingRoom', self._TrainingSettingsWindow_updateTrainingRoom)

		g_entitiesFactories.addSettings(ViewSettings(
			OBSERVER_ALIAS, ObserverWindow, 'ObserverWindow.swf', WindowLayer.WINDOW, None, ScopeTemplates.DEFAULT_SCOPE))

		if g_modsListApi:
			g_modsListApi.addModification(
				id='mod_observer',
				name='Offline map viewer',
				description='',
				icon='',
				enabled=True,
				login=True,
				lobby=False,
				callback=self.openWindow
			)

	def openWindow(self):
		ServicesLocator.appLoader.getApp().loadView(SFViewLoadParams(OBSERVER_ALIAS, OBSERVER_ALIAS), {})

	@property
	def arenaTypeID(self):
		if self.arenaType:
			return self.arenaType.id
		elif self.spaceName in ArenaType.g_geometryNamesToIDs:
			return ArenaType.g_geometryNamesToIDs[self.spaceName]
		try:
			return ArenaType.g_geometryNamesToIDs[DEFAULT_SPACE_NAME]
		except KeyError:
			return ArenaType.g_geometryNamesToIDs.values()[0]

	@property
	def arenaName(self):
		return ArenaType.g_cache[self.arenaTypeID].name

	@property
	def arenaVisibilityMask(self):
		return ArenaType.getVisibilityMask(self.arenaTypeID >> 16)

	@property
	def arenaBonusType(self):
		bonusType = max(ARENA_BONUS_TYPE.RANGE)+1

		ARENA_BONUS_TYPE.RANGE = list(ARENA_BONUS_TYPE.RANGE)
		ARENA_BONUS_TYPE.RANGE.append(bonusType)
		ARENA_BONUS_TYPE.RANGE = tuple(ARENA_BONUS_TYPE.RANGE)

		ARENA_BONUS_MASK.TYPE_BITS = dict(
			((name, 2 ** id) for id, name in enumerate(ARENA_BONUS_TYPE.RANGE[1:])))

		if bonusType not in ARENA_BONUS_TYPE_CAPS._typeToCaps:
			caps = set()
			for _bonusType, typeCaps in ARENA_BONUS_TYPE_CAPS._typeToCaps.items():
				if _bonusType not in constants.ARENA_BONUS_TYPE.RANDOM_RANGE:
					continue
				if _bonusType not in constants.ARENA_BONUS_TYPE.EXTERNAL_RANGE:
					continue
				caps = caps | typeCaps
			ARENA_BONUS_TYPE_CAPS._typeToCaps[bonusType] = caps
			LOG_DEBUG('ARENA_BONUS_TYPE registred: %s' % bonusType)
		return bonusType

	def getCursorWorldPos(self):
		x, y = GUI.mcursor().position
		dir, start = cameras.getWorldRayAndPoint(x, y)
		end = start + dir.scale(100000.0)
		return collideDynamicAndStatic(start, end, (), 0)

	def observerStart(self):
		LOG_DEBUG('Observer Start')
		self.isStarted = True
		# constants.IS_DEVELOPMENT = True

		self.lobbyContext.setServerSettings(
			{'roamingSettings': [0, 0, [], []]})

		BigWorld.clearEntitiesAndSpaces()
		self.connectionManager.onConnected()

		BattleReplay.g_replayCtrl.play('offline_%s' % self.spaceName)

		BigWorld.worldDrawEnabled(False)
		LOG_DEBUG('Avatar', BigWorld.createEntity('Avatar', BigWorld.createSpace(), 0, (0, 0, 0), (0, 0, 0), {}))

	def observerStop(self):
		LOG_DEBUG('Observer Stop')
		BigWorld.replaySimulator.stop()
		self.connectionManager.onDisconnected()
		# constants.IS_DEVELOPMENT = False
		# constants.HAS_DEV_RESOURCES = False
		self.isStarted = False
		ServicesLocator.appLoader.goToLoginByEvent()

	def _BigWorld_serverTime(self, baseFunc, *args, **kwargs):
		if self.isStarted:
			return BigWorld.time(*args, **kwargs)
		return baseFunc(*args, **kwargs)

	def _MinimapLobby_setArena(self, baseFunc, baseSelf, arenaTypeID):
		if arenaTypeID < 0:
			arenaTypeID = ArenaType.g_geometryNamesToIDs[DEFAULT_SPACE_NAME]
		return baseFunc(baseSelf, arenaTypeID)

	def _TrainingSettingsWindow_init(self, baseFunc, baseSelf, ctx=None):
		baseFunc(baseSelf, ctx)
		baseSelf.isObserverMod = ctx.get('isObserverMod', False)
		if baseSelf.isObserverMod:
			baseSelf._TrainingSettingsWindow__arenasCache = self.arenasCache

	def _TrainingSettingsWindow_updateTrainingRoom(self, baseFunc, baseSelf, arenaTypeID, roundLength, isPrivate, comment):
		if baseSelf.isObserverMod:
			if arenaTypeID in self.arenasCache.spaces:
				self.arenaType = ArenaType.g_cache[ArenaType.g_geometryNamesToIDs[DEFAULT_SPACE_NAME]]
				self.spaceName = self.arenasCache.spaces[arenaTypeID]
			else:
				self.arenaType = ArenaType.g_cache[arenaTypeID]
				self.spaceName = self.arenaType.geometryName
			baseSelf.onWindowClose()
			self.onUpdate()
		else:
			baseFunc(baseSelf, arenaTypeID, roundLength, isPrivate, comment)

	def _ClientArenaVisitor_getTeamSpawnPoints(self, baseFunc, baseSelf, team):
		if team is None:
			team = 0 if BigWorld.player().team == 1 else 1
		return baseFunc(baseSelf, team)

g_instance = Observer()


@override(game, 'handleKeyEvent')
def game_handleKeyEvent(baseFunc, event):
	if event.isKeyDown() and not event.isRepeatedEvent(): 
		if g_instance.isStarted:
			if event.isCtrlDown() and event.key == Keys.KEY_F10:
				player = BigWorld.player()
				player.inputHandler.setAimingMode(False, AIMING_MODE.USER_DISABLED)
				player.inputHandler.onControlModeChanged(CTRL_MODE_NAME.VIDEO)
		else:
			if event.isCtrlDown() and event.key == Keys.KEY_F10:
				g_instance.openWindow()
			if event.isCtrlDown() and event.key == Keys.KEY_F11:
				g_instance.observerStart()
	return baseFunc(event)

from gui.mods.observer import avatar_overrides, vehicle_overrides