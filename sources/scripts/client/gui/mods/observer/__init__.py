from .utils import *

IS_PHYSICS = False
IS_AUTOSTART = False

def LOG_NOTE(*args, **kwargs):
	kwargs = repr(kwargs) if kwargs else ''
	args = ' '.join([unicode(s) for s in args])
	print '[OBSERVER] %s %s' % (args, kwargs)

def LOG_DEBUG(*args, **kwargs):
	LOG_NOTE('[DEBUG]', *args, **kwargs)


def LOG_DEBUG_DEV(*args, **kwargs):
	LOG_NOTE('[DEBUG_DEV]', *args, **kwargs)
