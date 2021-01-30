import BigWorld
import ArenaType
import weakref
import physics_shared

from Vehicle import Vehicle

from gui.mods.mod_observer import g_instance
from gui.mods.observer import override


@override(Vehicle, '__startWGPhysics')
def __startWGPhysics(baseFunc, baseSelf):
	if g_instance.isStarted:
		if hasattr(baseSelf.filter, 'setVehiclePhysics'):
			typeDescr = baseSelf.typeDescriptor
			isWheeled = 'wheeledVehicle' in baseSelf.typeDescriptor.type.tags
			physics = BigWorld.WGWheeledPhysics() if isWheeled else BigWorld.WGTankPhysics()
			physics_shared.initVehiclePhysicsClient(physics, typeDescr)
			arenaMinBound, arenaMaxBound = (-10000, -10000), (10000, 10000)
			physics.setArenaBounds(arenaMinBound, arenaMaxBound)
			physics.owner = weakref.ref(baseSelf)
			physics.staticMode = False
			physics.movementSignals = 0
			baseSelf.filter.setVehiclePhysics(physics)
			physics.visibilityMask = ArenaType.getVisibilityMask(BigWorld.player().arenaTypeID >> 16)
			# yaw, pitch = decodeGunAngles(baseSelf.gunAnglesPacked, typeDescr.gun.pitchLimits['absolute'])
			# baseSelf.filter.syncGunAngles(yaw, pitch)
			baseSelf._Vehicle__speedInfo.set(baseSelf.filter.speedInfo)
			
		BigWorld.player().base.startVehicle(baseSelf.id, physics)
	else:
		baseFunc(baseSelf)
