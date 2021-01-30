import math
import Math
import BigWorld
import math_utils

from debug_utils import LOG_CURRENT_EXCEPTION

from . import *
from BasePhysics import BasePhysics

from physics_shared import *

from vehicle_systems.tankStructure import TankPartNames

def sum(array):
	value = array[0]
	for i in array[1:]:
		value = value + i
	return value

def avg(array):
	return sum(array)/len(array)

MODELS_OFFSET = Math.Vector3(0.0, 0.0, 0.0)

WHEEL_RADIUS = 0.4

class DumbPhysics(BasePhysics):
	def __init__(self, mover, physics):
		super(DumbPhysics, self).__init__(mover, physics)
		self.fallingSpeed = 0.0
		self.speed = 0.0
		self.rspeed = 0.0
		self.timeout = 0.0
		self.body = None

	def start(self):
		self.body = PhysicalBody(self)
		super(DumbPhysics, self).start()

	def updateMovement(self):
		#if self.body.isOnGround:
		friction = self.physics.brakeFriction if self.command.isStop else 1 # self.physics.forwardFriction
		force = friction / (WHEEL_RADIUS * 100) * self.physics.gravity * self.physics.mass

		limits = [-self.physics.bkwdSpeedLimit, self.physics.fwdSpeedLimit]
		if self.command.isCruiseControl25:
			limits[0] *= 0.25
			limits[1] *= 0.25
		elif self.command.isCruiseControl50:
			limits[0] *= 0.25
			limits[1] *= 0.25

		if self.command.isBackward or self.command.isStop and self.speed > 0:
			force = -force

		self.speed += force / self.physics.mass
		self.speed = max(min(self.speed, limits[1]), limits[0])

		if self.command.isStop and abs(self.speed) < 1:
			# Fix low-speed moving when vehicle must be stopped
			self.speed = 0

		if abs(self.speed) > 0:
			velocity = Math.Vector3(math.sin(self.body.rotation[0]), 0, math.cos(self.body.rotation[0])) * self.speed * self.timeout
			self.body.apply(velocity)

	def updateFalling(self):
		if self.fallingSpeed > 0:
			self.fallingSpeed = 0.0

		if self.body.isOnGround:
			self.fallingSpeed = 0.0
		elif self.body.isAboveGround:
			self.fallingSpeed -= self.physics.gravity * self.timeout
			self.fallingSpeed = min(self.fallingSpeed, self.body.position[1] - self.body.positionOnGround[1])
		elif self.body.isUnderGround:
			self.fallingSpeed = self.body.positionOnGround[1] - self.body.position[1]

		if abs(self.fallingSpeed) > 0:
			self.body.apply(Math.Vector3(0, self.fallingSpeed, 0))
			
	def updateRotation(self):
		if self.command.isLeft:
			self.rspeed = math.radians(-self.physics.rotationSpeedLimit)
		elif self.command.isRight:
			self.rspeed = math.radians(self.physics.rotationSpeedLimit)
		else:
			self.rspeed = 0

		if abs(self.rspeed) > 0:
			self.body.rotate(self.rspeed)

	def update(self, command, timeout, isPickup):
		'''
		Called by VehicleMover
		Returns position, rotation, movement speed, rotation speed

		Movement speed = base speed (forward/backward) + falling speed
		'''

		self.timeout = timeout
		self.command = command

		if isPickup:
			self.rspeed = 0
			self.speed = 0
			self.fallingSpeed = 0
			self.body.apply(Math.Vector3(0, 10, 0))
			self.body.applyRotation(Math.Vector3(0, -self.body.rotation[1], -self.body.rotation[2]))
		else:
			self.updateRotation()
			self.updateMovement()

		self.updateFalling()
		self.body.update(isPickup)
		return self.body.position, self.body.rotation, self.speed + self.fallingSpeed, self.rspeed

class Wheel(object):
	def __init__(self, track, isContact, isLeading, localPosition):
		self.localPosition = localPosition
		self.track = track
		self.physics = track.physics
		self.body = track.body
		self.height = 0 if isLeading else track.height
		self.isContact = isContact
		self.isLeading = isLeading and not isContact

		self.position = None
		self.isOnGround = False
		self.wheel = Math.Vector3()
		self.wheelUp = Math.Vector3()
		self.wheelDown = Math.Vector3()
		self.positionOnGround = Math.Vector3()

	def update(self):
		matrix = self.body.getRotationMatrix()

		self.wheel = self.body.position + matrix.applyPoint(self.track.localPosition + self.localPosition)
		self.wheelUp = self.wheel + matrix.applyPoint(Math.Vector3(0, self.height, 0))
		self.wheelDown = self.wheel - matrix.applyPoint(Math.Vector3(0, self.height, 0))

		self.positionOnGround = self.physics.collide(self.wheelUp, self.wheelDown, True)
		self.position = self.positionOnGround or self.wheel
		self.isOnGround = self.positionOnGround is not None

		if self.positionOnGround is None:
			self.positionOnGround = self.physics.collide(
				self.wheelUp + matrix.applyPoint(Math.Vector3(0, self.physics.getHeight(), 0)), 
				self.wheelDown - matrix.applyPoint(Math.Vector3(0, 1000, 0))
			)

class VehicleTrack(object):
	def __init__(self, body, isRight):
		self.body = body
		self.physics = body.physics
		self.isRight = isRight

		chassisBbox = self.physics.vehicle.typeDescriptor.chassis['hitTester'].bbox

		self.localPosition = Math.Vector3(chassisBbox[0][0], 0, 0)
		if isRight:
			self.localPosition = -self.localPosition

		self.halfLength = max(abs(chassisBbox[0][2]), abs(chassisBbox[1][2]))
		self.height = max(abs(chassisBbox[0][1]), abs(chassisBbox[1][1]))
		self.wheels = [
			Wheel(self, False, True,  Math.Vector3(0, self.height / 2.0, -self.halfLength)), 
			Wheel(self, True, False,  Math.Vector3(0, 0, -self.halfLength * 0.75)), 
			Wheel(self, True, False,  Math.Vector3(0, 0, -self.halfLength * 0.5)), 
			Wheel(self, False, False, Math.Vector3(0, 0, -self.halfLength * 0.25)), 
			Wheel(self, False, False, Math.Vector3(0, 0, 0)), 
			Wheel(self, False, False, Math.Vector3(0, 0, self.halfLength * 0.25)), 
			Wheel(self, True, False,  Math.Vector3(0, 0, self.halfLength * 0.5)), 
			Wheel(self, True, False,  Math.Vector3(0, 0, self.halfLength * 0.75)), 
			Wheel(self, False, True,  Math.Vector3(0, self.height / 2.0, self.halfLength)), 
		]

		self.position = Math.Vector3()
		self.pitch = 0
		self.isOnGround = False
		self.positionOnGround = Math.Vector3()

	def update(self):
		map(lambda wheel: wheel.update(), self.wheels)
		self.isOnGround = False not in [wheel.isOnGround for wheel in self.wheels if wheel.isContact]

		avgWheel = avg([wheel.position for wheel in self.wheels])
		localPosition = self.body.getRotationMatrix().applyPoint(self.localPosition)
		localPosition = Math.Vector3(localPosition[0], avgWheel[1] - self.body.position[1], localPosition[2])
		self.position = self.body.position + localPosition

		angles = []
		lastWheel = None
		for wheel in self.wheels:
			if wheel.isContact:
				if lastWheel:
					angles.append((wheel.position - lastWheel.position).pitch)
				lastWheel = wheel
		self.pitch = avg(angles)
		self.positionOnGround = avg([wheel.positionOnGround for wheel in self.wheels if wheel.isContact])

	def debugUpdate(self):
		try:
			if IS_DEBUG:
				lines = []
				points = []
				lastWheel = None
				for wheel in self.wheels:
					points.append(wheel.position)
					lines.append((wheel.wheelUp, wheel.wheelDown))
					if lastWheel:
						lines.append((wheel.position, lastWheel.position))

				if not hasattr(self, 'debugModels'):
					self.debugModels = [[], []]

				for i in xrange(0, len(lines) - len(self.debugModels[0])):
					self.debugModels[0].append(DebugLine())

				for i in xrange(0, len(points) - len(self.debugModels[1])):
					self.debugModels[1].append(DebugPoint())

				for i, (start, end) in enumerate(lines):
					self.debugModels[0][i].set(start + MODELS_OFFSET, end + MODELS_OFFSET)

				for i, position in enumerate(points):
					self.debugModels[1][i].set(position + MODELS_OFFSET)
		except:
			LOG_CURRENT_EXCEPTION()

class PhysicalBody(object):
	def __init__(self, physics):
		self.physics = physics

		self.skeleton = SkeletonCollider(physics)
		self.skeleton.attach()

		self.tracks = [
			VehicleTrack(self, False),
			VehicleTrack(self, True)
		]

		self.position = physics.vehicle.position
		self.rotation = Math.Vector3(physics.vehicle.yaw, physics.vehicle.pitch, physics.vehicle.roll)
		self.positionOnGround = self.physics.collidePoint(self.position)
		self.isOnGround = False
		self.isAboveGround = True
		self.isUnderGround = False

		self.debugVelocity = DebugLine()

	def apply(self, velocity):
		self.position = self.position + velocity

	def applyRotation(self, velocity):
		self.rotation = self.rotation + velocity
		self.rotation = Math.Vector3(
				math_utils.reduceToPI(self.rotation[0]),
				math_utils.reduceToPI(self.rotation[1]),
				math_utils.reduceToPI(self.rotation[2]),
			)

	def rotate(self, rspeed):
		self.applyRotation(Math.Vector3(rspeed, 0, 0))

	def update(self, isPickup):
		map(lambda track: track.update(), self.tracks)

		self.position = avg([track.position for track in self.tracks])
		self.positionOnGround = avg([track.positionOnGround for track in self.tracks])

		self.isOnGround = self.position[1] == self.positionOnGround[1] or sum([track.isOnGround for track in self.tracks]) == len(self.tracks)
		self.isAboveGround = self.position[1] > self.positionOnGround[1]
		self.isUnderGround = self.position[1] < self.positionOnGround[1]

		pitch = avg([track.pitch for track in self.tracks])
		roll = (self.tracks[0].position - self.tracks[1].position).pitch
		self.rotation = Math.Vector3(self.rotation[0], pitch, roll)

		# if not isPickup:
		# 	hasCollide = self.skeleton.doCollide(self.physics.vehicle.position, self.position - self.physics.vehicle.position)
		# 	if hasCollide:
		# 		print 'Collision detected!', self.skeleton.impactCollider, self.skeleton.impactPoint, self.skeleton.impactReflection
		# 		self.position = self.physics.vehicle.position
		# 		self.rotation = Math.Vector3(self.physics.vehicle.yaw, self.physics.vehicle.pitch, self.physics.vehicle.roll)

		self.debugUpdate()
		
	def debugUpdate(self):
		try:
			if IS_DEBUG:
				map(lambda track: track.debugUpdate(), self.tracks)

				if not hasattr(self, 'debugVelocity'):
					self.debugVelocity = DebugLine()

				offset = Math.Vector3(0.0, 3.0, 0.0)
				self.debugVelocity.set(self.physics.vehicle.position + offset, self.position + offset)
		except:
			LOG_CURRENT_EXCEPTION()

	def getRotationMatrix(self):
		matrix = Math.Matrix()
		matrix.setRotateYPR(self.rotation)
		return matrix

class SkeletonCollider(object):
	impactCollider = property(lambda self: self.skeletonCollider.impactCollider)
	impactPoint = property(lambda self: self.skeletonCollider.impactPoint)
	impactReflection = property(lambda self: self.skeletonCollider.impactReflection)

	def __init__(self, physics):
		self.physics = physics
		self.vehicle = self.physics.vehicle
		self.skeletonCollider = BigWorld.SkeletonCollider()

		descr = self.vehicle.typeDescriptor
		descList = [
			#(TankPartNames.CHASSIS, descr.chassis['hitTester'].bbox),
			(TankPartNames.HULL, descr.hull['hitTester'].bbox),
			(TankPartNames.TURRET, descr.turret['hitTester'].bbox),
			#(TankPartNames.GUN, descr.gun['hitTester'].bbox)
		]

		for desc in descList:
			boxAttach = BigWorld.BoxAttachment()
			boxAttach.name = desc[0]
			boxAttach.minBounds = desc[1][0]
			boxAttach.maxBounds = desc[1][1]
			self.skeletonCollider.addCollider(boxAttach)

	def attach(self):
		for idx in xrange(self.skeletonCollider.nColliders()):
			collider = self.skeletonCollider.getCollider(idx)
			self.vehicle.model.node(collider.name).attach(collider)

	def detach(self):
		for idx in xrange(self.skeletonCollider.nColliders()):
			collider = self.skeletonCollider.getCollider(idx)
			self.vehicle.model.node(collider.name).detach(collider)

	def doCollide(self, start, direction):
		return self.skeletonCollider.doCollide(start, direction)