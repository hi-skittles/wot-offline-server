from gui.mods.mod_observer import *

import Vehicle
import time

from Avatar import _CRUISE_CONTROL_MODE, _MOVEMENT_FLAGS
from helpers.CallbackDelayer import CallbackDelayer

from Physics import DumbPhysics

MOVEMENT_TICK = 0.01

class MovementCommand:
	isStop            = property(lambda self: not self.isForward and not self.isBackward or self.isBlockTracks)
	isForward         = property(lambda self: self.hasFlag(_MOVEMENT_FLAGS.FORWARD) or self._isCruiseControlForward())
	isBackward        = property(lambda self: self.hasFlag(_MOVEMENT_FLAGS.BACKWARD) or self._isCruiseControlBackward())
	isLeft            = property(lambda self: self.hasFlag(_MOVEMENT_FLAGS.ROTATE_LEFT))
	isRight           = property(lambda self: self.hasFlag(_MOVEMENT_FLAGS.ROTATE_RIGHT))
	isCruiseControl50 = property(lambda self: self.hasFlag(_MOVEMENT_FLAGS.CRUISE_CONTROL50) or self._isCruiseControl50())
	isCruiseControl25 = property(lambda self: self.hasFlag(_MOVEMENT_FLAGS.CRUISE_CONTROL25) or self._isCruiseControl25())
	isBlockTracks     = property(lambda self: self.hasFlag(_MOVEMENT_FLAGS.BLOCK_TRACKS))

	def __init__(self):
		self.flags = 0
		self.cruiseControlMode = _CRUISE_CONTROL_MODE.NONE

	def hasFlag(self, flag):
		return self.flags & flag > 0

	def _isCruiseControl25(self):
		return self.cruiseControlMode == _CRUISE_CONTROL_MODE.FWD25

	def _isCruiseControl50(self):
		return self.cruiseControlMode in (_CRUISE_CONTROL_MODE.FWD50, _CRUISE_CONTROL_MODE.BCKW50)

	def _isCruiseControlForward(self):
		return self.cruiseControlMode in (_CRUISE_CONTROL_MODE.FWD25, _CRUISE_CONTROL_MODE.FWD50, _CRUISE_CONTROL_MODE.FWD100)

	def _isCruiseControlBackward(self):
		return self.cruiseControlMode in (_CRUISE_CONTROL_MODE.BCKW50, _CRUISE_CONTROL_MODE.BCKW100)

class VehicleMover(CallbackDelayer):
	vehicle = property(lambda self: BigWorld.entity(self.vehicleID))

	def __init__(self, vehicleID, server):
		CallbackDelayer.__init__(self)
		self.server = server
		self.vehicleID = vehicleID
		self.isStarted = False
		self.physics = None
		self.command = MovementCommand()
		self.lastTick = None
		self.isPickup = False

		self._wgPhysics = None

	def moveWith(self, flags):
		self.command.flags = flags

	def setCruiseControlMode(self, mode):
		self.command.cruiseControlMode = mode

	def setPhysics(self, physics):
		self._wgPhysics = physics
		self.physics = DumbPhysics(self, physics)

	def start(self):
		self.isStarted = True
		self.physics.start()
		self.delayCallback(MOVEMENT_TICK, self.__movementTick)
		
	def stop(self):
		self.physics.stop()
		self.isStarted = False

	def pickup(self):
		self.isPickup = True

	def __movementTick(self):
		if self.isStarted:
			try:
				if self.vehicle is not None and self.vehicle.isStarted:

					if self.lastTick is None:
						self.lastTick = time.time()
					position, rotation, speed, rspeed = self.physics.update(self.command, time.time() - self.lastTick, self.isPickup)
					self.vehicle.teleport(position, rotation)
					self.lastTick = time.time()

					if self.physics.collidesPerTick > 150:
						print "WARN: Too many collides per tick:", self.physics.collidesPerTick
					self.physics.collidesPerTick = 0

					self.server.updateVehiclePosition(self.vehicleID, position, rotation, speed, rspeed)
					self.isPickup = False
			except:
				LOG_CURRENT_EXCEPTION()
			return MOVEMENT_TICK