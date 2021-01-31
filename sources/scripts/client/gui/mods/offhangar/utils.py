'''This module contains common functions that used in game modifications'''

__author__ = "Iliev Renat"
__email__ = "iliahonz@gmail.com"

import BigWorld
import ResMgr
import functools
import inspect
import os
import shutil
import tempfile
import time
import json
import re

def byteify(data):
	'''Encodes data with UTF-8
	:param data: Data to encode'''
	if isinstance(data, dict): 
		return {byteify(key): byteify(data) for key, data in data.iteritems()}
	elif isinstance(data, list): 
		return [byteify(element) for element in data]
	elif isinstance(data, unicode): 
		return data.encode('utf-8')
	else: 
		return data

def jsonDump(obj, needFmt=False):
	'''Serializes an object into a string
	:param obj: Object
	:param needFmt: Indicates that the result should be formatted for human reading'''
	if needFmt:
		return json.dumps(obj, ensure_ascii=False, indent=4, separators=(',', ': '), sort_keys=True, encoding='utf-8')
	return json.dumps(obj)

def jsonLoad(src):
	'''Returns json data from source
	It supports comments in json
	:param src: Data source (file handler or string)'''
	if not isinstance(src, (str, unicode)):
		src = src.read()
	return jsonParse(src)

def jsonParse(data):
	'''Pareses json string into dict
	It supports comments in json
	:param data: JSON string'''
	def comments(text):
		regex = r'\s*(#|\/{2}).*$'
		regex_inline = r'(:?(?:\s)*([A-Za-z\d\.{}]*)|((?<=\").*\"),?)(?:\s)*(((#|(\/{2})).*)|)$'
		lines = text.split('\n')
		excluded = []
		for index, line in enumerate(lines):
			if re.search(regex, line):
				if re.search(r'^' + regex, line, re.IGNORECASE):
					excluded.append(lines[index])
				elif re.search(regex_inline, line):
					lines[index] = re.sub(regex_inline, r'\1', line)
		for line in excluded:
			lines.remove(line)
		return '\n'.join(lines)
	return byteify(json.loads(comments(data), encoding='utf-8'))

def deepUpdate(obj, new):
	'''Recursive updating of the dictionary (including dictionaries in it)
	:param obj: Dictionary to be updated
	:param new: Diff dictionary'''
	for key, value in new.iteritems():
		if isinstance(value, dict):
			obj[key] = deepUpdate(obj.get(key, {}), value)
		else:
			obj[key] = value
	return obj

def isAlly(vehicle):
	'''Checks is vehicle in player's team
	:param vehicle: Entity ID or object
	:return: Is given entity in player team'''
	player = BigWorld.player()
	vehicles = player.arena.vehicles
	vehicleID = vehicle.id if isinstance(vehicle, BigWorld.Entity) else vehicle
	return vehicleID in vehicles and vehicles[player.playerVehicleID]['team'] == vehicles[vehicleID]['team']

def doLog(project, *args, **kwargs):
	'''Prints arguments to stdout with tag
	:param project: Tag for log string
	:param args: Arguments, it reduces to string by join with space
	:param kwargs: Key-value arguments, it reduces to string by repr'''

	kwargs = repr(kwargs) if kwargs else ''
	args = ' '.join([unicode(s) for s in args])
	print '[%s] %s %s' % (project, args, kwargs)

def unpackVFS(prefix, *paths):
	'''Unpacks files from VFS with ResMgr into temporary folder
	:param postfix: Postfix for temporary folder name
	:param prefix: Prefix for temporary folder name
	:param paths: Path to files in VFS
	:return: List of absolute paths to unpacked files'''

	folder = os.path.join(tempfile.gettempdir(), '_'.join([str(prefix), str(int(time.time()))]))

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
	'''Overrides attribute in object.
	Attribute should be property or callable.
	Getter, setter and deleter should be callable or None.
	:param obj: Object
	:param prop: Name of any attribute in object (can be not mangled)
	:param getter: Getter function
	:param setter: Setter function
	:param deleter: Deleter function'''
	
	if inspect.isclass(obj) and prop.startswith('__') and prop not in dir(obj) + dir(type(obj)):
		prop = obj.__name__ + prop
		if not prop.startswith('_'):
			prop = '_' + prop

	src = getattr(obj, prop)
	if type(src) is property and (getter or setter or deleter):
		assert getter is None or callable(getter) , 'Getter is not callable!'
		assert setter is None or callable(setter) , 'Setter is not callable!'
		assert deleter is None or callable(deleter), 'Deleter is not callable!'

		getter = functools.partial(getter, src.fget) if getter else src.fget
		setter = functools.partial(setter, src.fset) if setter else src.fset
		deleter = functools.partial(deleter, src.fdel) if deleter else src.fdel

		setattr(obj, prop, property(getter, setter, deleter))
		return getter
	elif getter:
		assert callable(src), 'Source property is not callable!'
		assert callable(getter), 'Handler is not callable!'

		getter_new = lambda *args, **kwargs: getter(src, *args, **kwargs)
		if not isinstance(src, type(BigWorld.Entity.__getattribute__)) and not inspect.ismethod(src) and inspect.isclass(obj):
			getter_new = staticmethod(getter_new)

		setattr(obj, prop, getter_new)
		return getter
	else:
		return functools.partial(override, obj, prop)