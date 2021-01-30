# coding: utf-8
import types
import json
import os
import subprocess
import sys
import zipfile
import marshal
import imp
import time
import struct
import shutil
import sys
import tempfile

from datetime import datetime
from xml.etree import ElementTree
from xml.dom import minidom


def call(*args):
    try:
        return subprocess.check_output(args, shell=True, stderr=subprocess.STDOUT, universal_newlines=True).strip()
    except subprocess.CalledProcessError as e:
        return e.output


def getVersion(meta):
	if 'version' in meta:
		return meta['version']
	
	if 'not a git repository' not in call('git', 'log'):
		tree = call('git', 'rev-parse', '--abbrev-ref', 'HEAD')
		commit = int(call('git', 'rev-list', 'HEAD', '--count'))
		values = (tree == 'master', commit % 1000 / 100, commit % 100 / 10, commit % 10)
		return '.'.join(map(str, map(int, values)))
	else:
		return '1.0.0'


def readSWF(path):
	path = str(os.path.abspath(path))

	name, _ = os.path.splitext(os.path.basename(path))
	swf = os.path.join(os.path.dirname(path), os.path.basename(name) + '.swf')

	if os.path.isfile(swf):
		with open(swf, 'rb') as f:
			return f.read()
	else:
		print swf, 'not found'


def buildFLA(projects):
	if '-f' in sys.argv and projects:
		with open('build.jsfl', 'wb') as fh:
			for path in projects.keys():
				path = str(os.path.abspath(path))
				fh.write('fl.publishDocument("file:///%s", "Default");' % path.replace('\\', '/').replace(':', '|'))
				fh.write('\r\n')
			fh.write('fl.quit(false);')

		try:
			subprocess.check_output([os.environ.get('ANIMATE'), '-e', 'build.jsfl', '-AlwaysRunJSFL'],
									universal_newlines=True,
									stderr=subprocess.STDOUT)
		except subprocess.CalledProcessError as error:
			print error.output.strip()

		try:
			os.remove('build.jsfl')
		except Exception as ex:
			print ex.message
	return {
		dst: readSWF(src)
		for src, dst in projects.items()
	}


def buildFlashFD(path):
	path = str(os.path.abspath(path))
	if os.path.isfile(path):
		try:
			fdbuild = os.environ.get('FDBUILD')
			flexsdk = os.environ.get('FLEXSDK')
			if fdbuild and os.path.exists(fdbuild) and flexsdk and os.path.exists(flexsdk):
				args = [fdbuild, '-compiler:' + flexsdk, path]
				subprocess.check_output(args,
										shell=True,
										universal_newlines=True,
										stderr=subprocess.STDOUT)
		except subprocess.CalledProcessError as error:
			print path
			print error.output.strip()

		name, _ = os.path.splitext(os.path.basename(path))
		swf = os.path.join(os.path.dirname(path), 'bin', os.path.basename(name) + '.swf')

		return readSWF(path)
	else:
		print path, 'not found'


def buildPython(path, filename):
	def read(self, path, filename):
		with open(path, 'r') as f:
			try:
				timestamp = long(os.fstat(f.fileno()).st_mtime)
			except AttributeError:
				timestamp = long(time.time())
			return f.read(), struct.pack('L', timestamp)

	def repack(code, co_filename, co_name):
		co_consts = []
		for const in code.co_consts:
			if isinstance(const, types.CodeType):
				const = repack(const, co_filename, const.co_name)
			co_consts.append(const)

		code = types.CodeType(
			code.co_argcount,
			code.co_nlocals,
			code.co_stacksize,
			code.co_flags,
			code.co_code,
			tuple(co_consts),
			code.co_names,
			code.co_varnames,
			co_filename,
			co_name,
			code.co_firstlineno,
			code.co_lnotab,
			code.co_freevars,
			code.co_cellvars
		)

		return code

	if filename.startswith('/'):
		filename = filename[1:]

	with open(path, 'rb') as f:
		try:
			timestamp = long(os.fstat(f.fileno()).st_mtime)
		except AttributeError:
			timestamp = long(time.time())

		basename = os.path.basename(path)
		code = compile(f.read(), filename, 'exec')
		code = repack(code, filename, basename)
		return imp.get_magic() + struct.pack('L', timestamp) + marshal.dumps(code)


def buildGO(path):
	"""
		Calls and returns stdout go in project work dir
	"""

	env = dict(os.environ)
	if 'GOBIN' not in env:
		env['GOBIN'] = os.path.join(os.environ.get('GOPATH'), 'bin')

	with tempfile.NamedTemporaryFile(delete=True) as f:
		filename = f.name

	try:
		subprocess.check_output(['go', 'build', '-o', filename], 
								cwd=path, env=env, shell=True, 
								stderr=subprocess.STDOUT, universal_newlines=True)
		with open(filename, 'rb') as f:
			return f.read()
	except subprocess.CalledProcessError as e:
		print path, e.output.strip()


def createMeta(**meta):
	metaET = ElementTree.Element('root')
	for key, value in meta.iteritems():
		ElementTree.SubElement(metaET, key).text = value
	metaStr = ElementTree.tostring(metaET)
	metaDom = minidom.parseString(metaStr)
	metaData = metaDom.toprettyxml(encoding='utf-8').split('\n')[1:]
	return '\n'.join(metaData)


def write(excludes, package, path, data):
	if path in excludes:
		print 'Excluded', path
		return

	if not data:
		data = ''

	print 'Write', path, len(data)
	
	now = tuple(datetime.now().timetuple())[:6]
	path = path.replace('\\', '/')

	dirname = os.path.dirname(path)
	while dirname:
		if dirname + '/' not in package.namelist():
			package.writestr(zipfile.ZipInfo(dirname + '/', now), '')
		dirname = os.path.dirname(dirname)

	if data:
		info = zipfile.ZipInfo(path, now)
		info.external_attr = 33206 << 16 # -rw-rw-rw-
		package.writestr(info, data)


def deploy(pathLine, gamePath):
	# Deploying by adding path into paths.xml
	for dirName, _, files in os.walk(gamePath):
		for filename in files:
			if filename == 'paths.xml':
				print 'Deploy into', dirName
				path = os.path.join(dirName, filename)
				with open(path, 'r') as p:
					paths = p.read().split('\n')
						
				for idx, line in enumerate(paths):
					if line == pathLine:
						break
					if '<Packages>' in line:
						paths.insert(idx, pathLine)
						break

				with open(path, 'w') as p:
					p.write('\n'.join(paths))


def clear(pathLine, gamePath):
	# Remove deployed from paths.xml
	for dirName, _, files in os.walk(gamePath):
		for filename in files:
			if filename == 'paths.xml':
				print 'Clear from', dirName
				path = os.path.join(dirName, filename)
				with open(path, 'r') as p:
					paths = p.read().split('\n')

				paths = filter(lambda x: x.strip() != pathLine, paths)

				with open(path, 'w') as p:
					p.write('\n'.join(paths))


def build(packageFile, config):
	with zipfile.ZipFile(packageFile, 'w') as package:
		write(excludes, package, 'meta.xml', createMeta(**CONFIG['meta']))

		sources = os.path.abspath('./sources')

		for dirName, _, files in os.walk(sources):
			for filename in files:
				path = os.path.join(dirName, filename)
				name = path.replace(sources, '').replace('\\', '/')
				dst = 'res' + name
				
				fname, fext = os.path.splitext(dst)
				if fext == '.py':
					write(excludes, package, fname + '.pyc', buildPython(path, name))
				elif fext == '.po':
					import polib
					write(excludes, package, fname + '.mo', polib.pofile(path).to_binary())
				elif fext != '.pyc' or CONFIG.get('pass_pyc_files', False):
					with open(path, 'rb') as f:
						write(excludes, package, dst, f.read())

		for source, dst in CONFIG.get('flash_fdbs', {}).items():
			write(excludes, excludes, package, dst, buildFlashFD(source))

		for dst, data in buildFLA(CONFIG.get('flash_fla', {})).items():
			write(excludes, package, dst, data)

		for source, dst in CONFIG.get('go', {}).items():
			write(excludes, package, dst, buildGO(source))

		for path, dst in CONFIG.get('copy', {}).items():
			with open(path, 'rb') as f:
				write(excludes, package, dst, f.read())


if __name__ == '__main__':
	with open('./build.json', 'r') as fh:
		CONFIG = json.loads(fh.read())

	excludes = CONFIG.get('excludes', [])

	CONFIG['meta']['version'] = getVersion(CONFIG['meta'])

	if CONFIG.get('append_version', True):
		packageName = '%s_%s.wotmod' % (CONFIG['meta']['id'], CONFIG['meta']['version'])
	else:
		packageName = '%s.wotmod' % CONFIG['meta']['id']

	if os.path.exists('bin'):
		shutil.rmtree('bin')

	if not os.path.exists('bin'):
		os.makedirs('bin')

	pathLine = '<Path mode="recursive" mask="*.wotmod" root="res">' + os.path.abspath('bin').replace('\\', '/') + '</Path>'

	if 'clear' in sys.argv:
		clear(pathLine, sys.argv[sys.argv.index('clear') + 1])
	else:
		build(os.path.abspath(os.path.join('bin', packageName)), CONFIG)
		if 'deploy' in sys.argv:
			deploy(pathLine, sys.argv[sys.argv.index('deploy') + 1])

