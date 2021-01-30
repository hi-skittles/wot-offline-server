import nations
import items

from helpers import dependency
from constants import ACCOUNT_ATTR, SkinInvData

from items import utils, vehicles, tankmen, getTypeOfCompactDescr, makeIntCompactDescrByID
from items.vehicles import isItemWithCompactDescrExist

from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.Vehicle import Vehicle
from gui.shared.utils.requesters.vehicle_items_getter import _MODULES_GETTERS

from skeletons.gui.shared.gui_items import IGuiItemsFactory

from .logging import *
from .utils import *
from ._constants import *

shopItems = {}
items.init(True, shopItems)

if vehicles._g_prices and 'notInShopItems' in vehicles._g_prices:
	vehicles._g_prices['notInShopItems'].clear()
if 'notInShopItems' in shopItems:
	shopItems['notInShopItems'].clear()

def iterItems():
	for itemType, getter in _MODULES_GETTERS.items():
		for nationID in nations.INDICES.itervalues():
			for item in getter(nationID):
				if isItemWithCompactDescrExist(item.compactDescr):
					yield item.compactDescr

@dependency.replace_none_kwargs(itemsFactory=IGuiItemsFactory)
def getOfflineInventory(itemsFactory=None):
	data = {i: {} for i in GUI_ITEM_TYPE.ALL()}
	data[GUI_ITEM_TYPE.VEHICLE] = {
		'compDescr': {},
		'crew': {},
	}
	data[GUI_ITEM_TYPE.TANKMAN] = {
		'compDescr': {},
		'vehicle': {},
	}
	data[GUI_ITEM_TYPE.CREW_SKINS] = {
		SkinInvData.ITEMS: {},
		SkinInvData.OUTFITS: {},
	}

	for typeCompDescr in iterItems():
		itemType = getTypeOfCompactDescr(typeCompDescr)
		if itemType == GUI_ITEM_TYPE.VEHICLE:
			item = itemsFactory.createGuiItem(itemType, typeCompDescr=typeCompDescr)
			nationID, vehicleTypeID = item.descriptor.type.id

			data[GUI_ITEM_TYPE.VEHICLE]['compDescr'][typeCompDescr] = item.descriptor.makeCompactDescr()
			data[GUI_ITEM_TYPE.VEHICLE]['crew'][typeCompDescr] = []

			for idx, roles in enumerate(item.descriptor.type.crewRoles):
				tmanID = typeCompDescr << 4 + idx
				data[GUI_ITEM_TYPE.TANKMAN]['compDescr'][tmanID] = tankmen.generateCompactDescr(
					tankmen.generatePassport(nationID, True), 
					vehicleTypeID, 
					roles[0], 
					100
				)
				data[GUI_ITEM_TYPE.TANKMAN]['vehicle'][tmanID] = typeCompDescr
				data[GUI_ITEM_TYPE.VEHICLE]['crew'][typeCompDescr].append(tmanID)
		else:
			item = itemsFactory.createGuiItem(itemType, typeCompDescr)
			if itemType == GUI_ITEM_TYPE.CREW_SKINS:
				data[itemType][SkinInvData.ITEMS][item.getID()] = item.getMaxCount()
				data[itemType][SkinInvData.OUTFITS][item.getID()] = item.getMaxCount()
			else:
				data[itemType][typeCompDescr] = 1

	return {
		'inventory': data,
	}

def getOfflineStats():
	unlocksSet = set()
	vehiclesSet = set()

	for typeCompDescr in iterItems():
		itemType = getTypeOfCompactDescr(typeCompDescr)
		if itemType == GUI_ITEM_TYPE.VEHICLE:
			vehiclesSet.add(typeCompDescr)
		unlocksSet.add(typeCompDescr)

	attrs = 0
	for field in dir(ACCOUNT_ATTR):
		value = getattr(ACCOUNT_ATTR, field, None)
		if isinstance(value, (int, long)) and value != ACCOUNT_ATTR.SUSPENDED:
			attrs |= value

	return { 
		'stats': {
			'crystalExchangeRate': 200,
			'berths': 40,
			'accOnline': 0,
			'autoBanTime': 0,
			'gold': 1000000,
			'crystal': 100000,
			'isFinPswdVerified': True,
			'finPswdAttemptsLeft': 0,
			'denunciationsLeft': 0,
			'freeVehiclesLeft': 0,
			'refSystem': {'referrals': {}},
			'slots': len(vehiclesSet),
			'battlesTillCaptcha': 0,
			'hasFinPassword': True,
			'clanInfo': (None, None, 0, 0, 0),
			'unlocks': unlocksSet,
			'mayConsumeWalletResources': True, 	
			'freeTMenLeft': 0,
			'vehicleSellsLeft': 0,
        	'SPA': {'/common/goldfish_bonus_applied/': u'1'},
			'vehTypeXP': {i: 0 for i in vehiclesSet},
			'unitAcceptDeadline': 0,
			'globalVehicleLocks': {},
			'freeXP': 100000000,
			'captchaTriesLeft': 0,
			'fortResource': 0,
			'premiumExpiryTime': 86400,
			'tkillIsSuspected': False,
			'credits': 100000000,
			'vehTypeLocks': {},
			'dailyPlayHours': [0],
			'globalRating': 0,
			'restrictions': {},
			'oldVehInvID': 0,
			'accOffline': 0,
			'dossier': '',
			'multipliedXPVehs': unlocksSet,
			'tutorialsCompleted': 33553532,
			'eliteVehicles': vehiclesSet,
			'playLimits': ((0, ''), (0, '')),
			'clanDBID': 0,
			'attrs': attrs,
		}
	}

def getOfflineShop():
	return {
		'crystalExchangeRate': 200,
		'camouflageCost': {
			0: (250, True),
			30: (100000, False),
			7: (25000, False)
		},
		'goodies': {
			'prices': {},
			'notInShop': set([]),
			'goodies': {}
		},
		'berthsPrices': (16,16,[300]),
		'femalePassportChangeCost': 50,
		'freeXPConversion': (25,1),
		'dropSkillsCost': {
			0: { 'xpReuseFraction': 0.5, 'gold': 0, 'credits': 0 },
			1: { 'xpReuseFraction': 0.75, 'gold': 0, 'credits': 20000 },
			2: { 'xpReuseFraction': 1.0, 'gold': 200, 'credits': 0 }
		},
		'refSystem': {
			'maxNumberOfReferrals': 50,
			'posByXPinTeam': 10,
			'maxReferralXPPool': 350000,
			'periods': [(24, 3.0), (168, 2.0), (876000, 1.5)]
		},
		'playerEmblemCost': {
			0: (15, True),
			30: (6000, False),
			7: (1500, False)
		},
		'premiumCost': {
			1: 250,
			3: 650,
			7: 1250,
			360: 24000,
			180: 13500,
			30: 2500
		},
		'winXPFactorMode': 0,
		'sellPriceModif': 0.5,
		'passportChangeCost': 50,
		'exchangeRateForShellsAndEqs': 400,
		'exchangeRate': 400,
		'tankmanCost': ({
				'isPremium': False,
				'baseRoleLoss': 0.20000000298023224,
				'gold': 0,
				'credits': 0,
				'classChangeRoleLoss': 0.20000000298023224,
				'roleLevel': 50
			},
			{
				'isPremium': False,
				'baseRoleLoss': 0.10000000149011612,
				'gold': 0,
				'credits': 20000,
				'classChangeRoleLoss': 0.10000000149011612,
				'roleLevel': 75
			},
			{
				'isPremium': True,
				'baseRoleLoss': 0.0,
				'gold': 200,
				'credits': 0,
				'classChangeRoleLoss': 0.0,
				'roleLevel': 100
			}),
		'dailyXPFactor': 2,
		'changeRoleCost': 500,
		'isEnabledBuyingGoldShellsForCredits': True,
		'items': shopItems,
		'slotsPrices': (9, [300]),
		'freeXPToTManXPRate': 10,
		'defaults': {
			'items': {},
			'freeXPToTManXPRate': 0,
			'goodies': { 'prices': { } }
		},
		'sellPriceFactor': 0.5,
		'isEnabledBuyingGoldEqsForCredits': True,
		'playerInscriptionCost': {
			0: (15, True),
			7: (1500, False),
			30: (6000, False),
			'nations': { }
		}
	}

def getOfflineQuestsProgress():
	return {
		'tokens': {},
		'potapovQuests': {
			'compDescr': '',
			'regular': {
				'lastIDs': {},
				'rewards': [ {}, {} ],
				'selected': [65, 7, 20, 53, 39],
				'slots': 5
			},
			'pm2': {
				'lastIDs': {},
				'rewards': [ {}, {} ],
				'selected': [],
				'slots': 4
			},
		},
		'tiles': []
	}
