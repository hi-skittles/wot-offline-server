"""This module contains common functions that used in game modifications"""

__author__ = "Iliev Renat"
__email__ = "me@izeberg.ru"

import collections
import functools
import inspect
import json
import os
import re
import shutil
import tempfile
import time

import BigWorld
import ResMgr

from constants import ARENA_GUI_TYPE


DEFAULT_EXCLUDED_GUI_TYPES = {
    ARENA_GUI_TYPE.TUTORIAL, ARENA_GUI_TYPE.EPIC_RANDOM, ARENA_GUI_TYPE.EPIC_BATTLE,
    ARENA_GUI_TYPE.EPIC_RANDOM_TRAINING, ARENA_GUI_TYPE.EPIC_TRAINING, ARENA_GUI_TYPE.EVENT_BATTLES,
    ARENA_GUI_TYPE.UNKNOWN,
}


def isDisabledByBattleType(exclude=None, include=tuple()):
	if not exclude:
		exclude = DEFAULT_EXCLUDED_GUI_TYPES
	player = BigWorld.player()
	if not hasattr(player, 'arena') or player.arena is None:
		return False
	if player.arena.guiType in exclude and player.arena.guiType not in include:
		return True
	return False


def byteify(data):
	"""Encodes data with UTF-8
	:param data: Data to encode"""
	if isinstance(data, dict):
		return {byteify(key): byteify(data) for key, data in data.iteritems()}
	elif isinstance(data, list):
		return [byteify(element) for element in data]
	elif isinstance(data, unicode):
		return data.encode('utf-8')
	else:
		return data


def jsonify(obj):
	""" Returns JSON-serializable object from given object
	:param obj: Object
	:param needFmt: JSON-serializable object (dict or list)
	"""
	if isinstance(obj, collections.Mapping):
		return {str(k): jsonify(v) for k, v in obj.iteritems()}
	if isinstance(obj, collections.Iterable) and not isinstance(obj, (str, unicode)):
		return list(map(jsonify, obj))
	return obj


def jsonDump(obj, needFmt=False):
	""" Serializes an object into a string
	:param obj: Object
	:param needFmt: Indicates that the result should be formatted for human reading"""
	kwargs = {
		'encoding': 'utf-8'
	}
	if needFmt:
		kwargs.update({
			'ensure_ascii': False,
			'indent': 4,
			'separators': (',', ': '),
			'sort_keys': True
		})
	return json.dumps(jsonify(obj), **kwargs)


def jsonLoad(src, skipcomments=False):
	""" Returns json data from source
	It supports comments in json (see jsonRemoveComments)
	:param skipcomments: Skip comments removing
	:param src: Data source (file or string)"""

	if not isinstance(src, (str, unicode)):
		src = src.read()

	if not skipcomments:
		src = jsonRemoveComments(src)

	return byteify(json.loads(src))


def jsonRemoveComments(data, strip_space=True):
	""" Removes json comments in data
	"""

	tokenizer = re.compile('"|(/\*)|(\*/)|(//)|\n|\r')
	endSlashes = re.compile(r'(\\)*$')

	inString = False
	inMultiString = False
	inSingle = False

	result = []
	index = 0

	for match in re.finditer(tokenizer, data):
		if not (inMultiString or inSingle):
			tmp = data[index:match.start()]
			if not inString and strip_space:
				# replace white space as defined in standard
				tmp = re.sub('[ \t\n\r]+', '', tmp)
			result.append(tmp)

		index = match.end()
		group = match.group()

		if group == '"' and not (inMultiString or inSingle):
			escaped = endSlashes.search(data, 0, match.start())

			# start or unescaped quote character to end
			if not inString or (escaped is None or len(escaped.group()) % 2 == 0):
				inString = not inString
			index -= 1  # include quote character in next catch
		elif not (inString or inMultiString or inSingle):
			if group == '/*':
				inMultiString = True
			elif group == '//':
				inSingle = True
		elif group == '*/' and inMultiString and not (inString or inSingle):
			inMultiString = False
		elif group in '\r\n' and not (inMultiString or inString) and inSingle:
			inSingle = False
		elif not ((inMultiString or inSingle) or (group in ' \r\n\t' and strip_space)):
			result.append(group)

	result.append(data[index:])
	return ''.join(result)


def jsonParse(data, skipcomments=False):
	""" Pareses json string into dict
	It supports comments in json
	:param data: JSON string"""

	if not skipcomments:
		data = jsonRemoveComments(data)

	return byteify(json.loads(data))


def deepUpdate(obj, new):
	""" Recursive updating of the dictionary (including dictionaries in it)
	:param obj: Dictionary to be updated
	:param new: Diff dictionary"""
	for key, value in new.iteritems():
		if isinstance(value, dict):
			obj[key] = deepUpdate(obj.get(key, {}), value)
		else:
			obj[key] = value
	return obj


def isAlly(vehicle):
	""" Checks is vehicle in player's team
	:param vehicle: Entity ID or object
	:return: Is given entity in player team"""
	player = BigWorld.player()
	vehicles = player.arena.vehicles
	vehicleID = vehicle.id if isinstance(vehicle, BigWorld.Entity) else vehicle
	return vehicleID in vehicles and vehicles[player.playerVehicleID]['team'] == vehicles[vehicleID]['team']


def doLog(project, *args, **kwargs):
	""" Prints arguments to stdout with tag
	:param project: Tag for log string
	:param args: Arguments, it reduces to string by join with space
	:param kwargs: Key-value arguments, it reduces to string by repr"""

	kwargs = repr(kwargs) if kwargs else ''
	args = ' '.join([unicode(s) for s in args])
	print '[%s] %s %s' % (project, args, kwargs)


def unpackVFS(prefix, *paths):
	""" Unpacks files from VFS with ResMgr into temporary folder
	:param postfix: Postfix for temporary folder name
	:param prefix: Prefix for temporary folder name
	:param paths: Path to files in VFS
	:return: List of absolute paths to unpacked files"""

	folder = os.path.join(tempfile.gettempdir(), '_'.join(
		[str(prefix), str(int(time.time()))]))

	if os.path.exists(folder):
		shutil.rmtree(folder, ignore_errors=True)
	os.makedirs(folder)

	result = []
	for path in paths:
		filepath = os.path.join(folder, os.path.basename(path))
		result.append(filepath)
		with open(filepath, 'wb') as f:
			f.write(str(ResMgr.openSection(path).asBinary))
	return result


def override(obj, prop, getter=None, setter=None, deleter=None):
	""" Overrides attribute in object.
	Attribute should be property or callable.
	Getter, setter and deleter should be callable or None.
	:param obj: Object
	:param prop: Name of any attribute in object (can be not mangled)
	:param getter: Getter function
	:param setter: Setter function
	:param deleter: Deleter function"""

	if inspect.isclass(obj) and prop.startswith('__') and prop not in dir(obj) + dir(type(obj)):
		prop = obj.__name__ + prop
		if not prop.startswith('_'):
			prop = '_' + prop

	src = getattr(obj, prop)
	if type(src) is property and (getter or setter or deleter):
		assert getter is None or callable(getter), 'Getter is not callable!'
		assert setter is None or callable(setter), 'Setter is not callable!'
		assert deleter is None or callable(deleter), 'Deleter is not callable!'

		getter = functools.partial(getter, src.fget) if getter else src.fget
		setter = functools.partial(setter, src.fset) if setter else src.fset
		deleter = functools.partial(deleter, src.fdel) if deleter else src.fdel

		setattr(obj, prop, property(getter, setter, deleter))
		return getter
	elif getter:
		assert callable(src), 'Source property is not callable!'
		assert callable(getter), 'Handler is not callable!'

		if inspect.isclass(obj) and inspect.ismethod(src) \
			or isinstance(src, type(BigWorld.Entity.__getattribute__)):
			
			getter_new = lambda *args, **kwargs: getter(src, *args, **kwargs)
		else:
			getter_new = functools.partial(getter, src)

		setattr(obj, prop, getter_new)
		return getter
	else:
		return functools.partial(override, obj, prop)
