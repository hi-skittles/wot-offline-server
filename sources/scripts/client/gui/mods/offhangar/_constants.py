import cPickle
import Keys
import ResMgr
import time

from chat_shared import CHAT_RESPONSES, CHAT_ACTIONS, CHAT_COMMANDS
from gui.mods.offhangar.utils import jsonParse

# Request catching feature
# Disables 'offline' mode
# Dumps any request from client and any result from server
IS_REQUEST_CATCHING = False

OFFLINE_SERVER_ADDRES = 'ensure.wargaming.local'
OFFLINE_NICKNAME = 'ensure'
OFFLINE_LOGIN = OFFLINE_NICKNAME + '@' + OFFLINE_SERVER_ADDRES
OFFLINE_PWD = ''
OFFLINE_DBID = 1

OFFLINE_GUI_CTX = cPickle.dumps({
    'databaseID': OFFLINE_DBID,
   	'bootcampRunCount': 1,
   	'bootcampCompletedCount': 0,
   	'logUXEvents': False,
   	'serverUTC': time.time(),
   	'currentVehInvID': 0,
    'bootcampNeedAwarding': 0,
    'aogasStartedAt': time.time(),
    'sessionStartedAt': time.time(),
    'isAogasEnabled': False,
    'collectUiStats': True,
    'isLongDisconnectedFromCenter': False,
})

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
