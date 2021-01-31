import functools
import inspect
import BigWorld

from os.path import isdir
from ResMgr import openSection
from BigWorld import wg_getProductVersion
from Event import Event

class WOT_UTILS:
	# Provides easy way for overriding and stores some info about client

	PATH = [openSection.asString for openSection in openSection('../paths.xml')['Paths'].values() if isdir(openSection.asString)][0]
	MODS = '/'.join([PATH, 'scripts', 'client', 'mods'])
	VERSION = tuple(map(int, wg_getProductVersion().split('.')))
	GUI_MODS = '/'.join([PATH, 'scripts', 'client', 'gui', 'mods'])

	@classmethod
	def OVERRIDE(cls, obj, prop, getter=None, setter=None, deleter=None):
		# Overrides property in object
		# source - object
		# prop - any property in object (can be not mangled)
		# getter, setter, deleter - functions for override 'property' wrapper (not tested)
		if inspect.isclass(obj) and prop.startswith('__') and prop not in dir(obj) + dir(type(obj)):
			prop = obj.__name__ + prop
			if not prop.startswith('_'):
				prop = '_' + prop

		src = getattr(obj, prop)
		if type(src) is property and (getter or setter or deleter):
			assert callable(getter) and (not setter or callable(setter)) and (not deleter or callable(deleter)), 'Args is not callable!'

			getter = functools.partial(getter, src.fget) if getter else src.fget
			setter = functools.partial(setter, src.fset) if setter else src.fset
			deleter = functools.partial(deleter, src.fdel) if deleter else src.fdel

			setattr(obj, prop, property(getter, setter, deleter))
			return getter
		elif getter:
			assert callable(src), 'Source property is not callable!'
			assert callable(getter), 'Handler is not callable!'

			getter_new = lambda *args, **kwargs: getter(src, *args, **kwargs)
			if not inspect.ismethod(src) and inspect.isclass(obj):
				getter_new = staticmethod(getter_new)

			setattr(obj, prop, getter_new)
			return getter
		else:
			return lambda getter=None, setter=None, deleter=None: cls.OVERRIDE(obj, prop, getter)

	class EVENT(Event):
		def __init__(self, source, prop, isAfter=True, isEnabled=lambda: True, isCallback=False, isDispose=False, delegates=None):
			# Allows delegates to subscribe for the event and to be called when source's property is called.
			# source - object
			# prop - property in object (can be not mangled)
			# isAfter - call delegates after basic function
			# isEnabled - function, if result is True - delegates can be called
			# isCallback - call delegates in BigWorld.callback
			# isDispose - clear delegates list after every call
			# delegates - base delegates (can't be deleted)

			super(self.__class__, self).__init__()
			self.isEnabled = isEnabled
			self.isAfter = isAfter
			self.isCallback = isCallback
			self.isDispose = isDispose
			self._delegates = delegates
			if delegates:
				map(self.__iadd__, delegates)
			WOT_UTILS.OVERRIDE(source, prop, self.call)

		def __call__(self, *args, **kwargs):
			if self.isEnabled():
				call = functools.partial(super(self.__class__, self).__call__, *args, **kwargs)
				if self.isCallback:
					BigWorld.callback(0, call)
				else:
					call()

				if self.isDispose:
					self.clear()

		def clear(self):
			super(self.__class__, self).clear()
			if self._delegates:
				map(self.__iadd__, self._delegates)

		def call(self, baseFunc, *args, **kwargs):
			if not self.isAfter: 
				self.__call__(*args, **kwargs)
			retval = baseFunc(*args, **kwargs)
			if self.isAfter:
				self.__call__(*args, **kwargs)
			return retval