import os
import signal
import json
import BigWorld
import constants
import Account
import game

import resource_helper

from soft_exception import SoftException
from gui.doc_loaders import badges_loader

from gui.Scaleform.Waiting import Waiting
from vehicle_systems import model_assembler
from debug_utils import LOG_CURRENT_EXCEPTION
from helpers import dependency
from predefined_hosts import g_preDefinedHosts
from connection_mgr import LOGIN_STATUS

from gui.shared.personality import ServicesLocator
from gui.Scaleform.locale.MENU import MENU
from gui.Scaleform.daapi.view.lobby.header.battle_selector_items import _BattleSelectorItems

from gui.shared.gui_items.Vehicle import Vehicle
from gui.shared.gui_items.fitting_item import FittingItem
from gui.shared.gui_items.customization.c11n_items import Customization, Style

from gui.shared.gui_items.badge import Badge, BadgeLayouts

from skeletons.gui.login_manager import ILoginManager

from items.components.c11n_components import BaseCustomizationItem

from .offhangar.logging import *
from .offhangar.utils import *
from .offhangar._constants import *
from .offhangar.server import *
from .offhangar.requests import *
from .offhangar.catcher import *

Account.LOG_DEBUG = LOG_DEBUG
Account.LOG_NOTE = LOG_NOTE

def fini():
	# Force killing game process
	os.kill(os.getpid(), signal.SIGTERM)


if not IS_REQUEST_CATCHING:
	LOG_DEBUG('Register host', OFFLINE_SERVER_ADDRES)
	g_preDefinedHosts._hosts.append(g_preDefinedHosts._makeHostItem(OFFLINE_SERVER_ADDRES, OFFLINE_SERVER_ADDRES, OFFLINE_SERVER_ADDRES))


@override(_BattleSelectorItems, 'update')
@override(_BattleSelectorItems, 'validateAccountAttrs')
@override(_BattleSelectorItems, 'select')
def _BattleSelectorItems_update(baseFunc, baseSelf, *args, **kwargs):
	selected = baseFunc(baseSelf, *args, **kwargs)
	if BigWorld.player().isOffline:
		for item in baseSelf._BaseSelectorItems__items.itervalues():
			item._isVisible = True
			item._isDisabled = False
	return selected


@override(model_assembler, 'assembleCollisionObstaclesCollector')
def model_assembler_assembleCollisionObstaclesCollector(baseFunc, appearance, lodStateLink, desc, spaceID):
	baseFunc(appearance, lodStateLink, desc, spaceID)
	if BigWorld.player().isOffline:
		appearance.collisionObstaclesCollector.disable()


# Enable all badges
@override(badges_loader, '_readBadges')
def badges_loader_readBadges(baseFunc):
	if not BigWorld.player().isOffline:
		return baseFunc()

	result = {}
	ctx, section = resource_helper.getRoot(badges_loader._BADGES_XML_PATH)
	for ctx, subSection in resource_helper.getIterator(ctx, section['badges']):
		try:
			item = resource_helper.readItem(ctx, subSection, name='badge')
			if not item.name:
				raise SoftException('No name for badge is provided', item.name)
			if 'id' not in item.value:
				raise SoftException('No ID for badge is provided', item.value)
			value = dict(item.value)
			realms = value.pop('realm', None)
			# if realms is not None:
			# 	if CURRENT_REALM in realms.get('exclude', []) or 'include' in realms and CURRENT_REALM not in realms.get('include', []):
			# 		continue
			if 'weight' not in value:
				value['weight'] = -1.0
			if 'type' not in value:
				value['type'] = 0
			if 'layout' not in value:
				value['layout'] = BadgeLayouts.PREFIX
			else:
				layout = value['layout']
				if layout not in BadgeLayouts.ALL():
					raise SoftException('Invalid badge layout type "{}" is provided'.format(layout))
			value['name'] = item.name
			result[value['id']] = value
		except:
			LOG_CURRENT_EXCEPTION()

	resource_helper.purgeResource(badges_loader._BADGES_XML_PATH)
	return result


# Mark all badges as achieved
@override(Badge, '__init__')
def Badge_init(baseFunc, baseSelf, *args, **kwargs):
	baseFunc(baseSelf, *args, **kwargs)
	if BigWorld.player().isOffline:
		baseSelf.isSelected = True
		baseSelf.isAchieved = True
		baseSelf.achievedAt = 0


@override(Vehicle, 'canSell')
def Vehicle_canSell(baseFunc, baseSelf):
	if BigWorld.player().isOffline:
		return False
	return baseFunc(baseSelf)


@override(Customization, 'isHiddenInUI')
@override(BaseCustomizationItem, 'isHiddenInUI')
def hook_offile_show(baseFunc, *args, **kwargs):
	if BigWorld.player().isOffline:
		return False
	return baseFunc(*args, **kwargs)

@override(Account.PlayerAccount, '__init__')
def Account_init(baseFunc, baseSelf):
	baseSelf.isOffline = not hasattr(baseSelf, 'name')
	if baseSelf.isOffline:
		LOG_DEBUG('PlayerAccount.init offline')
		constants.IS_SHOW_SERVER_STATS = False
		baseSelf.fakeServer = FakeServer()
		setattr(baseSelf, *Account._CLIENT_SERVER_VERSION)
		baseSelf.name = OFFLINE_NICKNAME
		baseSelf.initialServerSettings = OFFLINE_SERVER_SETTINGS

	baseFunc(baseSelf)

	if baseSelf.isOffline:
		BigWorld.player(baseSelf)
		

@override(Account.PlayerAccount, '__getattribute__')
def Account_getattribute(baseFunc, baseSelf, name):
	if name in ('cell', 'base', 'server') and baseSelf.isOffline:
		name = 'fakeServer'
	return baseFunc(baseSelf, name)


@override(Account.PlayerAccount, 'onBecomePlayer')
def Account_onBecomePlayer(baseFunc, baseSelf):
	baseFunc(baseSelf)
	if baseSelf.isOffline:
		LOG_DEBUG('PlayerAccount.onBecomePlayer')
		baseSelf.showGUI(OFFLINE_GUI_CTX)


@override(BigWorld, 'clearEntitiesAndSpaces')
def BigWorld_clearEntitiesAndSpaces(baseFunc, *args):
	if getattr(BigWorld.player(), 'isOffline', False):
		return
	baseFunc(*args)


@override(BigWorld, 'connect')
def BigWorld_connect(baseFunc, server, loginParams, progressFn):
	if server == OFFLINE_SERVER_ADDRES:
		LOG_DEBUG('BigWorld.connect')
		BigWorld.callback(0.0, lambda: progressFn(1, LOGIN_STATUS.LOGGED_ON, json.dumps({'token2': ''})))
		BigWorld.createEntity('Account', BigWorld.createSpace(), 0, (0, 0, 0), (0, 0, 0), {})
	else:
		baseFunc(server, loginParams, progressFn)


@override(game, 'handleKeyEvent')
@dependency.replace_none_kwargs(loginManager=ILoginManager)
def game_handleKeyEvent(baseFunc, event, loginManager=None):
	isOffline = getattr(BigWorld.player(), 'isOffline', False)
	if event.isKeyDown() and not event.isRepeatedEvent(): 
		if isOffline:
			if event.isCtrlDown():
				if event.key == Keys.KEY_V:
					app = ServicesLocator.appLoader.getDefLobbyApp()
					if app:
						app.component.visible = not app.component.visible
						app.graphicsOptimizationManager.switchOptimizationEnabled(app.component.visible)
						return True
				if event.key == Keys.KEY_W:
					Waiting.close()
					return True
		elif not IS_REQUEST_CATCHING:
			if event.isCtrlDown() and event.key == Keys.KEY_0:
				LOG_DEBUG('loginManager.initiateLogin', not IS_REQUEST_CATCHING and not BigWorld.player())
				loginManager.initiateLogin(OFFLINE_LOGIN, OFFLINE_PWD, OFFLINE_SERVER_ADDRES, False, False)
				return True
	return baseFunc(event)
