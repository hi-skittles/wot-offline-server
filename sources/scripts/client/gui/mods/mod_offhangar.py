import os
import signal
import Keys

import BigWorld
import constants
import Account

from debug_utils import LOG_CURRENT_EXCEPTION
from helpers import dependency
from predefined_hosts import g_preDefinedHosts
from connection_mgr import LOGIN_STATUS

from gui.Scaleform.Waiting import Waiting
from gui.shared.gui_items.Vehicle import Vehicle
from gui.Scaleform.daapi.view.login.LoginView import LoginView

from skeletons.gui.login_manager import ILoginManager

from gui.mods.offhangar.logging import *
from gui.mods.offhangar.utils import *
from gui.mods.offhangar._constants import *
from gui.mods.offhangar.server import *
from gui.mods.offhangar.requests import *

Account.LOG_DEBUG = LOG_DEBUG
Account.LOG_NOTE = LOG_NOTE

def fini():
	# Force killing game process
	os.kill(os.getpid(), signal.SIGTERM)

g_preDefinedHosts._hosts.append(g_preDefinedHosts._makeHostItem(OFFLINE_SERVER_ADDRES, OFFLINE_SERVER_ADDRES, OFFLINE_SERVER_ADDRES))

@override(Vehicle, 'canSell')
def Vehicle_canSell(baseFunc, baseSelf):
	return BigWorld.player().isOffline or baseFunc(baseSelf)

@override(LoginView, '_populate')
def LoginView_populate(baseFunc, baseSelf, *args, **kwargs):
	baseFunc(baseSelf, *args, **kwargs)
	# baseSelf.loginManager.initiateLogin(OFFLINE_LOGIN, OFFLINE_PWD, OFFLINE_SERVER_ADDRES, False, False) // dont auto login for nostalgia.

@override(Account.PlayerAccount, '__init__')
def Account_init(baseFunc, baseSelf):
	baseSelf.isOffline = not hasattr(baseSelf, 'name')
	if baseSelf.isOffline:
		# set constants
		constants.IS_SHOW_SERVER_STATS = True
		constants.DEVELOPMENT_INFO.ENABLE_SENDING_VEH_ATTRS_TO_CLIENT = True
		constants.CURRENT_REALM = 'ZZ'
		constants.ENABLE_DEBUG_DYNAMICS_INFO = True
		constants.IS_DEVELOPMENT = True # <-- important
		constants.IS_RENTALS_ENABLED = True
		constants.IS_SHOW_INGAME_HELP_FIRST_TIME = False
		constants.IS_TUTORIAL_ENABLED = False # enable if you want
		
		constants.ACCOUNT_ATTR.ADMIN = 256

		#

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
		progressFn(1, LOGIN_STATUS.LOGGED_ON, '{}')
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