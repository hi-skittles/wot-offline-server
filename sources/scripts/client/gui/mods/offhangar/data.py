import nations
import items

from helpers import dependency
from constants import ACCOUNT_ATTR

from items import utils, vehicles, tankmen, getTypeOfCompactDescr, makeIntCompactDescrByID
from items.vehicles import g_list, g_cache
from items.vehicles import VehicleDescr

from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.Vehicle import Vehicle

from skeletons.gui.shared import IItemsCache

from gui.mods.offhangar.logging import *
from gui.mods.offhangar.utils import *
from gui.mods.offhangar._constants import *

@dependency.replace_none_kwargs(itemsCache=IItemsCache)
def getOfflineInventory(itemsCache=None):
	data = {i: {} for i in GUI_ITEM_TYPE.ALL()}

	compDescr = {}
	for value in g_list._VehicleList__ids.values():
		vehicle = vehicles.VehicleDescr(typeID=value)
		intCompDescr = vehicles.makeIntCompactDescrByID('vehicle', *value)
		item = Vehicle(typeCompDescr=intCompDescr, proxy=itemsCache.items)

		vDesc = vehicle
		vType = vDesc.type
		turretv = vType.turrets[-1][-1]
		gunv = turretv.guns[-1]

		gunIDv = makeIntCompactDescrByID('vehicleGun',gunv.id[0],gunv.id[1])
		turretIDv = makeIntCompactDescrByID('vehicleTurret',turretv.id[0],turretv.id[1])
		engineIDv = makeIntCompactDescrByID('vehicleEngine',vType.engines[-1].id[0],vType.engines[-1].id[1])
		radioIDv = makeIntCompactDescrByID('vehicleRadio',vType.radios[-1].id[0],vType.radios[-1].id[1])
		chassisIDv = makeIntCompactDescrByID('vehicleChassis',vType.chassis[-1].id[0],vType.chassis[-1].id[1])

		vDesc.installComponent(chassisIDv)
		vDesc.installComponent(engineIDv)
		vDesc.installTurret(turretIDv,gunIDv)
		vDesc.installComponent(radioIDv)

		if not item.isOnlyForEventBattles and not item.isPremiumIGR:
			compDescr[len(compDescr)] = vDesc.makeCompactDescr()


	data[GUI_ITEM_TYPE.VEHICLE] = {
		'repair': {},
		'lastCrew': {},
		'settings': {},
		'compDescr': compDescr,
		'eqs': {},
		'shells': {},
		'customizationExpiryTime': {},
		'lock': {},
		'shellsLayout': {},
		'vehicle': {}
	}
	data['customizations'] = {
		False: {},
		True: {}
	}
			
	return {
		'inventory': data,
	}

def getOfflineStats():
	unlocksSet = set()
	vehiclesSet = set()
	
	for nationID in nations.INDICES.values():
		unlocksSet |= {vehicles.makeIntCompactDescrByID('vehicleChassis', nationID, i) for i in g_cache.chassis(nationID).keys()}
		unlocksSet |= {vehicles.makeIntCompactDescrByID('vehicleEngine', nationID, i) for i in g_cache.engines(nationID).keys()}
		unlocksSet |= {vehicles.makeIntCompactDescrByID('vehicleFuelTank', nationID, i) for i in g_cache.fuelTanks(nationID).keys()}
		unlocksSet |= {vehicles.makeIntCompactDescrByID('vehicleRadio', nationID, i) for i in g_cache.radios(nationID).keys()}
		unlocksSet |= {vehicles.makeIntCompactDescrByID('vehicleTurret', nationID, i) for i in g_cache.turrets(nationID).keys()}
		unlocksSet |= {vehicles.makeIntCompactDescrByID('vehicleGun', nationID, i) for i in g_cache.guns(nationID).keys()}
		unlocksSet |= {vehicles.makeIntCompactDescrByID('shell', nationID, i) for i in g_cache.shells(nationID).keys()}

		vData = {vehicles.makeIntCompactDescrByID('vehicle', nationID, i) for i in g_list.getList(nationID).keys()}
		unlocksSet |= vData
		vehiclesSet |= vData

	attrs = 0
	for field in dir(ACCOUNT_ATTR):
		value = getattr(ACCOUNT_ATTR, field, None)
		if isinstance(value, (int, long)):
			attrs |= value
	
	vehTypeXP = {i: 0 for i in vehiclesSet}

	return { 
		'stats': {
			'crystalExchangeRate': 200,
			'berths': 40000,
			'accOnline': 0,
			'autoBanTime': 0,
			'gold': 10000000,
			'crystal': 10000000,
			'isFinPswdVerified': True,
			'finPswdAttemptsLeft': 0,
			'denunciationsLeft': 0,
			'freeVehiclesLeft': 0,
			'refSystem': {'referrals': {}},
			'slots': 1000,
			'battlesTillCaptcha': 0,
			'hasFinPassword': True,
			'clanInfo': (None, None, 0, 0, 0),
			'unlocks': unlocksSet,
			'mayConsumeWalletResources': True,
			'freeTMenLeft': 10,
			'vehicleSellsLeft': 10,
			'SPA': {'/common/goldfish_bonus_applied/': u'1'},
			'vehTypeXP': vehTypeXP,
			'unitAcceptDeadline': 0,
			'globalVehicleLocks': {},
			'freeXP': 10000000,
			'captchaTriesLeft': 0,
			'fortResource': 0,
			'premiumExpiryTime': 8000,
			'tkillIsSuspected': False,
			'credits': 100000000,
			'vehTypeLocks': {},
			'dailyPlayHours': [0],
			'globalRating': 0,
			'restrictions': {},
			'oldVehInvID': 0,
			'accOffline': 1,
			'dossier': '',
			'multipliedXPVehs': {},
			'tutorialsCompleted': 33553532,
			'eliteVehicles': vehiclesSet,
			'playLimits': ((0, ''), (0, '')),
			'clanDBID': 0,
			'attrs': attrs,
		}
	}

def getOfflineShop():
	shopItems = {}
	items.init(True, shopItems)
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
		'freeXPConversion': (100000,0.1),
		'dropSkillsCost': {
			0: { 'xpReuseFraction': 0.5, 'gold': 0, 'credits': 0 },
			1: { 'xpReuseFraction': 0.75, 'gold': 0, 'credits': 20000 },
			2: { 'xpReuseFraction': 1.0, 'gold': 10, 'credits': 1000 }
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
			1: 1, #250
			3: 1, #650
			7: 1, #1250
			360: 1, #24000
			180: 1, #13500
			30: 1 #2500
		},
		'winXPFactorMode': 0,
		'sellPriceModif': 0.75,
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
		'paidRemovalCost': 0,
		'dailyXPFactor': 100,
		'changeRoleCost': 500,
		'isEnabledBuyingGoldShellsForCredits': False,
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
				'tiles': set([]),
				'rewards': {},
				'compDescr': '',
				'selected': set([1, 17, 31, 46, 61]),
				'lastIDs': {},
				'slots': 2
			},
			'fallout': {
				'tiles': set([]),
				'rewards': {},
				'compDescr': '',
				'selected': set([301, 401]),
				'lastIDs': {},
				'slots': 2
			},
		},
		'quests': {}
	}