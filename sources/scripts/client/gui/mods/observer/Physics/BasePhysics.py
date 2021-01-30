import Math
import BigWorld
import Vehicle

from . import IS_DEBUG

class BasePhysics(object):
	vehicle = property(lambda self: self.mover.vehicle)
	vehicleID = property(lambda self: self.mover.vehicleID)

	def __init__(self, mover, physics):
		self.mover = mover
		self.physics = physics
		self.collidesPerTick = 0

	def setPhysics(self, physics):
		self.physics = physics

	def start(self):
		pass

	def stop(self):
		pass

	def update(self, command, timeout, isPickup):
		'''
		Called by VehicleMover
		Returns position, rotation, movement speed, rotation speed
		'''
		return self.vehicle.position, Math.Vector3(self.vehicle.yaw, self.vehicle.roll, self.vehicle.pitch), 0.0, 0.0

	def getHeight(self):
		hullPosition = self.vehicle.typeDescriptor.chassis.hullPosition
		_, hullBboxMax, _ = self.vehicle.typeDescriptor.hull.hitTester.bbox
		turretPosition = self.vehicle.typeDescriptor.hull.turretPositions[0]
		turretTopY = max(hullBboxMax.y, turretPosition.y + self.vehicle.typeDescriptor.turret.hitTester.bbox[1].y)
		return hullPosition.y + turretTopY

	def getTopPoint(self, point, height):
		return Math.Vector3(point[0], point[1] + (height or self.getHeight()), point[2])

	def collidePoint(self, point, height=None):
		startPoint = self.getTopPoint(point, height)
		endPoint = Math.Vector3(point[0], -10000.0, point[2])
		return self.collide(startPoint, endPoint)

	def collide(self, startPoint, endPoint, noneOnEmpty=False):
		self.collidesPerTick += 1
		
		direction = endPoint - startPoint
		direction.normalise()
		
		testResStatic = BigWorld.wg_collideSegment(self.vehicle.spaceID, startPoint, endPoint, 128)

		distDynamic = None

		if testResStatic:
			endPoint = testResStatic[0]

		for entityID, entity in BigWorld.entities.items():
			if entityID != self.vehicleID:
				if isinstance(entity, Vehicle.Vehicle) and entity.isStarted or entity.model:
					if ProjectileMover.segmentMayHitEntity(entity, startPoint, endPoint):
						collisionResult = entity.collideSegment(startPoint, endPoint, skipGun)
						if collisionResult and (distDynamic is None or distDynamic < collisionResult[0]):
							distDynamic = collisionResult[0]

		if testResStatic or distDynamic:
			if not testResStatic or distDynamic and distDynamic <= (endPoint - startPoint).length:
				return startPoint + distDynamic * direction
			return endPoint
		if not noneOnEmpty:
			return startPoint
		return None