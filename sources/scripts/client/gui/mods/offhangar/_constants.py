import cPickle
import ResMgr

from chat_shared import CHAT_RESPONSES, CHAT_ACTIONS, CHAT_COMMANDS
from gui.mods.offhangar.utils import jsonParse

IS_REQUEST_CATCHING = False

OFFLINE_SERVER_ADDRES = 'wargaming.local'
OFFLINE_NICKNAME = 'Ensure'
OFFLINE_LOGIN = OFFLINE_NICKNAME + '@' + OFFLINE_SERVER_ADDRES
OFFLINE_PWD = '1234'
OFFLINE_DBID = 3

OFFLINE_GUI_CTX = cPickle.dumps({
    'databaseID': OFFLINE_DBID, 
    'logUXEvents': True, 
    'aogasStartedAt': 0, 
    'sessionStartedAt': 0, 
    'isAogasEnabled': False, 
    'collectUiStats': False, 
	'isLongDisconnectedFromCenter': False,
})

'''
OFFLINE_SERVER_SETTINGS = {
    'isGoldFishEnabled': False,
    'isVehicleRestoreEnabled': False,
    'isFalloutQuestEnabled': False,
    'isClubsEnabled': False,
    'isSandboxEnabled': True,
    'isFortBattleDivisionsEnabled': False,
    'isFortsEnabled': False,
    'isEncyclopediaEnabled': 'token',
    'isStrongholdsEnabled': False,
    'isRegularQuestEnabled': False,
    'isSpecBattleMgrEnabled': True,
    'isTankmanRestoreEnabled': False,

    'wallet': (False, False),
    'file_server': {},
    'forbiddenSortiePeripheryIDs': (),
    'newbieBattlesCount': 100,
    'roaming': (1, 1, [(1, 1, 2499999999L, 'OFFLINE')], ()),
    'randomMapsForDemonstrator': {},
    'spgRedesignFeatures': {'stunEnabled': False, 'markTargetAreaEnabled': False},
    'regional_settings': {'starting_day_of_a_new_week': 0, 'starting_time_of_a_new_game_day': 0, 'starting_time_of_a_new_day': 0},

    'forbidSPGinSquads': False,
    'forbiddenRatedBattles': {},
    'forbiddenSortieHours': (14, ),
    'forbiddenSortiePeripheryIDs': (),
    'forbiddenFortDefenseHours': (0, 1, 2, 3, 4),

    'eSportSeasonID': 4,
    'eSportSeasonStart': 1442318400,
    'eSportSeasonFinish': 1472688000,

    'xmpp_enabled': False,
    'xmpp_port': 0,
    'xmpp_host': '',
    'xmpp_muc_enabled': False,
    'xmpp_muc_services': [],
    'xmpp_resource': '',
    'xmpp_bosh_connections': [],
    'xmpp_connections': [],
    'xmpp_alt_connections': [],
}
'''

OFFLINE_SERVER_SETTINGS = jsonParse(ResMgr.openSection('helpers/offhangar/initialServerSettings.json').asBinary)

CHAT_ACTION_DATA = {
	'requestID': None,
	'action': None,
	'actionResponse': CHAT_RESPONSES.internalError.index(),
	'time': 0,
	'sentTime': 0,
	'channel': 0,
	'originator': 0,
	'originatorNickName': '',
	'group': 0,
	'data': {},
	'flags': 0,
}
REQUEST_CALLBACK_TIME = 0.5