import BigWorld
import ResMgr
import ArenaType
import Event
import GUI
import BattleReplay 

import weakref
import physics_shared
import constants
import debug_utils
import AvatarObserver

from debug_utils import *
from helpers import i18n
from constants import ARENA_BONUS_TYPE, ARENA_GUI_TYPE, ARENA_BONUS_MASK
from arena_bonus_type_caps import ARENA_BONUS_TYPE_CAPS
from items.vehicles import g_list, VehicleDescr, getVehicleTypeCompactDescr

from AvatarInputHandler import cameras
from ProjectileMover import collideDynamicAndStatic

from gui.shared import events, EVENT_BUS_SCOPE

from gui.Scaleform.framework import g_entitiesFactories, ViewSettings, ViewTypes, ScopeTemplates
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView

from gui.Scaleform.daapi.view.lobby.trainings import formatters
from gui.Scaleform.daapi.view.lobby.MinimapLobby import MinimapLobby
from gui.Scaleform.daapi.view.lobby.trainings.TrainingSettingsWindow import TrainingSettingsWindow

from gui.Scaleform.genConsts.PREBATTLE_ALIASES import PREBATTLE_ALIASES

from gui.app_loader import states
from gui.app_loader.loader import g_appLoader
from gui.Scaleform.framework.managers.loaders import ViewLoadParams


from gui.modsListApi import g_modsListApi
from gui.mods.observer import LOG_NOTE, LOG_DEBUG, WOT_UTILS, IS_AUTOSTART

from helpers import dependency
from skeletons.connection_mgr import IConnectionManager
from skeletons.gui.lobby_context import ILobbyContext


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
		g_appLoader.getApp().loadView(ViewLoadParams(PREBATTLE_ALIASES.TRAINING_SETTINGS_WINDOW_PY, PREBATTLE_ALIASES.TRAINING_SETTINGS_WINDOW_PY), {
			'isCreateRequest': True,
			'isObserverMod': True
		})

	def startLoading(self):
		g_instance.observerStart()

	def onUpdate(self):
		arenas = g_instance.arenasCache
		arenaTypeID = g_instance.arenaTypeID
		spaceName = g_instance.spaceName		
		arenaName = ArenaType.g_cache[arenaTypeID].name
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
		for arenaTypeID, arenaType in ArenaType.g_cache.iteritems():
			try:
				nameSuffix = '' if arenaType.gameplayName == 'ctf' else i18n.makeString('#arenas:type/%s/name' % arenaType.gameplayName)
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
				LOG_ERROR('There is error while reading arenas cache', arenaTypeID, arenaType)
				LOG_CURRENT_EXCEPTION()
				continue
		self.cache = sorted(self.cache, key=lambda x: (x['label'].lower(), x['name'].lower()))

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

		AvatarObserver.LOG_ERROR = debug_utils.LOG_ERROR

		WOT_UTILS.OVERRIDE(BigWorld, 'serverTime', self._BigWorld_serverTime)
		WOT_UTILS.OVERRIDE(states, '_isBattleReplayPlaying', self._states_isBattleReplayPlaying)
		WOT_UTILS.OVERRIDE(MinimapLobby, 'setArena', self._MinimapLobby_setArena)
		WOT_UTILS.OVERRIDE(TrainingSettingsWindow, '__init__', self._TrainingSettingsWindow_init)
		WOT_UTILS.OVERRIDE(TrainingSettingsWindow, 'updateTrainingRoom', self._TrainingSettingsWindow_updateTrainingRoom)

		g_entitiesFactories.addSettings(ViewSettings(OBSERVER_ALIAS, ObserverWindow, 'ObserverWindow.swf', ViewTypes.WINDOW, None, ScopeTemplates.DEFAULT_SCOPE))

		g_modsListApi.addModification(
			id='mod_observer', 
			name='Offline map viewer', 
			description='', 
			icon='', 
			enabled=True, 
			login=True, 
			lobby=False, 
			callback=self.onModsListCallback
		)

	def onModsListCallback(self):
		g_appLoader.getApp().loadView(ViewLoadParams(OBSERVER_ALIAS, OBSERVER_ALIAS), {})

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
	def arenaVisibilityMask(self):
		return ArenaType.getVisibilityMask(self.arenaTypeID >> 16)

	@property
	def arenaBonusType(self):
		bonusType = max(ARENA_BONUS_TYPE.RANGE)+1

		ARENA_BONUS_TYPE.RANGE = list(ARENA_BONUS_TYPE.RANGE)
		ARENA_BONUS_TYPE.RANGE.append(bonusType)
		ARENA_BONUS_TYPE.RANGE = tuple(ARENA_BONUS_TYPE.RANGE)

		ARENA_BONUS_MASK.TYPE_BITS = dict(((name, 2 ** id) for id, name in enumerate(ARENA_BONUS_TYPE.RANGE[1:])))

		if bonusType not in ARENA_BONUS_TYPE_CAPS._typeToCaps:
			caps = set()
			for typeCaps in ARENA_BONUS_TYPE_CAPS._typeToCaps.itervalues():
				caps = caps | typeCaps
			ARENA_BONUS_TYPE_CAPS._typeToCaps[bonusType] = caps
			LOG_DEBUG('ARENA_BONUS_TYPE registred: %s' % bonusType)
		return bonusType

	def getCursorWorldPos(self):
		x, y = GUI.mcursor().position
		dir, start = cameras.getWorldRayAndPoint(x, y)
		end = start + dir.scale(100000.0)
		return collideDynamicAndStatic(start, end, (), 0)

	def observerStart(self, connectionManager=None, lobbyContext=None):
		LOG_DEBUG('Observer Start')
		self.isStarted = True
		# constants.IS_DEVELOPMENT = True

		self.lobbyContext.setServerSettings({'roamingSettings': [0,0,[],[]]})

		BigWorld.clearEntitiesAndSpaces()
		self.connectionManager.onConnected()
		
		LOG_DEBUG('createEntity')
		BigWorld.worldDrawEnabled(False)
		LOG_DEBUG(BigWorld.createEntity('Avatar', BigWorld.createSpace(), 0, (0, 0, 0), (0, 0, 0), {}))

	def observerStop(self, connectionManager=None):
		LOG_DEBUG('Observer Stop')
		self.connectionManager.onDisconnected()
		# constants.IS_DEVELOPMENT = False
		# constants.HAS_DEV_RESOURCES = False
		self.isStarted = False
		g_appLoader.goToLoginByEvent()

	def _BigWorld_serverTime(self, baseFunc, *args, **kwargs):
		if self.isStarted:
			return BigWorld.time()
		return baseFunc(*args, **kwargs)

	def _states_isBattleReplayPlaying(self, baseFunc, *args, **kwargs):
		return self.isStarted or baseFunc(*args, **kwargs)

	def _MinimapLobby_setArena(self, baseFunc, baseSelf, arenaTypeID):
		if arenaTypeID < 0:
			arenaTypeID = ArenaType.g_geometryNamesToIDs[DEFAULT_SPACE_NAME]
		return baseFunc(baseSelf, arenaTypeID)

	def _TrainingSettingsWindow_init(self, baseFunc, baseSelf, ctx = None):
		baseFunc(baseSelf, ctx)
		baseSelf.isObserverMod = ctx.get('isObserverMod', False)
		if baseSelf.isObserverMod:
			baseSelf._TrainingSettingsWindow__arenasCache = self.arenasCache

	def _TrainingSettingsWindow_updateTrainingRoom(self, baseFunc, baseSelf, arenaTypeID, roundLength, isPrivate, comment):
		if baseSelf.isObserverMod:
			self.arenaType = ArenaType.g_cache[arenaTypeID]
			self.spaceName = self.arenaType.geometryName
			baseSelf.onWindowClose()
			self.onUpdate()
		else:
			baseFunc(baseSelf, arenaTypeID, roundLength, isPrivate, comment)

g_instance = Observer()

# AUTOSTART
def init():
	if IS_AUTOSTART:
		if not BattleReplay.isPlaying() and not BattleReplay.isLoading():
			BigWorld.callback(1, g_instance.observerStart)