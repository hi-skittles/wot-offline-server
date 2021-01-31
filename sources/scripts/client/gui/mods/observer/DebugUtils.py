import BigWorld
import Math

from AvatarInputHandler import mathUtils


class DebugPoint(object):
	def __init__(self):
		self.model = BigWorld.Model('helpers/models/point.model')
		BigWorld.addModel(self.model)

	def set(self, position):
		self.model.position = position

class DebugLine(object):
	def _setThickness(self, value):
		self.__thickness = value
		
	def _setVisibility(self, value):
		self.__model.visible = value

	thickness = property(lambda self: self.__thickness, _setThickness)
	visibility = property(lambda self: self.__model.visible, _setVisibility)
   
	def __init__(self):
		self.__model = BigWorld.Model('helpers/models/unit_cube.model')
		self.__motor = BigWorld.Servo(Math.Matrix())
		self.__model.addMotor(self.__motor)
		self.__model.castsShadow = False
		self.__thickness = 0.1
		BigWorld.addModel(self.__model, BigWorld.player().spaceID)

	def set(self, start, end):
		direction = end - start
		m = mathUtils.createSRTMatrix((self.__thickness, self.__thickness, direction.length), (direction.yaw, direction.pitch, 0), start + direction / 2)
		m.preMultiply(mathUtils.createTranslationMatrix((-0.5, -0.5, -0.5)))
		self.__motor.signal = m

	def destroy(self):
		if self.__model and self.__motor:
			self.__model.delMotor(self.__motor)
		self.__motor = None
		if self.__model and self.__model in BigWorld.models():
			BigWorld.delModel(self.__model)
		self.__model = None
 
class DebugLines(object):
   
	def __init__(self):
		self.__lines = []
 
	def set(self, points):
		idx = 0
		for curP, nextP in zip(points, points[1:]):
			if idx == len(self.__lines):
				self.__lines.append(Line(curP, nextP))
			else:
				self.__lines[idx].set(curP, nextP)
				self.__lines[idx].model.visible = True
			idx += 1
 
		while idx < len(self.__lines):
			self.__lines[idx].model.visible = False
			idx += 1
   
	def clear(self):
		while len(self.__lines):
			line = self.__lines.pop()
			line.destroy()
   
	def visible(self, value):
		for line in self.__lines:
			line.visibility = value