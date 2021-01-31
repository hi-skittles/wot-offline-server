import functools
from gui.mods.offhangar.utils import *

doLog = functools.partial(doLog, 'OFFHANGAR')
LOG_NOTE = functools.partial(doLog, '[NOTE]')
LOG_DEBUG = functools.partial(doLog, '[DEBUG]')