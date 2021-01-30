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
import psutil
import polib
import traceback
import collections

from datetime import datetime
from xml.etree import ElementTree
from xml.dom import minidom


class Errors(list):
	def __str__(self):
		return '\n'.join(map(str, self))

	def add(self, error):
		self.append(error)


class Error(collections.namedtuple('Error', ['builder', 'args', 'etype', 'value', 'tb'])):
	def __str__(self):
		res = []
		res.append('%s %s\n' % (self.builder, self.args)) 
		if self.etype == str:
			res.append(self.value)
		elif self.etype == subprocess.CalledProcessError:
			output = self.value.output.strip()
			if output:
				res.append('%s\n' % output)
		else:
			res.extend(traceback.format_exception(self.etype, self.value, self.tb))
		return ''.join(res)


def builder(func):
	def wrapped(errors, *args, **kwargs):
		try:
			return func(*args, errors=errors)
		except:
			etype, value, tb = sys.exc_info()
			desc = Error(func.__name__, args, etype, value, tb)
			errors.add(desc)
			print desc
			return kwargs.get('default', None)
	return wrapped


def call(*args):
	try:
		return subprocess.check_output(args, shell=True, stderr=subprocess.STDOUT, universal_newlines=True).strip()
	except subprocess.CalledProcessError as e:
		return e.output


def getVersion(meta):
	if 'version' in meta:
		return meta['version']
	
	tag = call('git', 'describe', '--abbrev=0', '--tags')
	if 'fatal:' not in tag:
		return tag
	
	if 'not a git repository' not in call('git', 'log'):
		tree = call('git', 'rev-parse', '--abbrev-ref', 'HEAD')
		commit = int(call('git', 'rev-list', 'HEAD', '--count'))
		values = (tree == 'master', commit % 1000 / 100, commit % 100 / 10, commit % 10)
		return '.'.join(map(str, map(int, values)))
	else:
		return '1.0.0'


def readSWF(path):
	path = str(os.path.abspath(path))
	name, ext = os.path.splitext(os.path.basename(path))

	swf = None
	if ext == '.xfl':
		swf = os.path.join(os.path.dirname(path), '..', name + '.swf')
	elif ext in ('.fla', '.as3proj'):
		swf = os.path.join(os.path.dirname(path), name + '.swf')

	assert swf and os.path.isfile(swf), '%s not found %s %s' % (swf, ext, path)
	
	with open(swf, 'rb') as f:
		return f.read()

@builder
def buildFLA(projects, build=False, errors=None):
	if build or '-f' in sys.argv or '-ui' in sys.argv and projects:
		build = True

		jsflFile = 'build.jsfl'
		logFileMask = 'as-build-%s.log'

		with open(jsflFile, 'wb') as fh:
			flashWD = os.getcwd().replace('\\', '/').replace(':', '|')
			
			for path in projects.keys():
				path = str(os.path.abspath(path))
				logFile = logFileMask % os.path.basename(path)
				fh.write('fl.publishDocument("file:///%s", "Default");\n' % path.replace('\\', '/').replace(':', '|'))
				fh.write('fl.compilerErrors.save("file:///%s/%s");\n' % (flashWD, logFile))

			# detect opened Animate
			for proc in psutil.process_iter(): 
				if proc.name().lower() == os.path.basename(os.environ.get('ANIMATE')).lower():
					break
			else:
				fh.write('fl.quit(false);')

		subprocess.call([os.environ.get('ANIMATE'), '-e', jsflFile, '-AlwaysRunJSFL'], stderr=subprocess.STDOUT)

		# publishing can be asynchronous when Animate is already opened
		# so waiting script file unlock to remove, which means publishing is done
		while os.path.exists(jsflFile): 
			try:
				os.remove(jsflFile)
			except:
				time.sleep(.1)

		# collect errors
		for path in projects.keys():
			logFile = logFileMask % os.path.basename(path)
			if os.path.isfile(logFile):
				with open(logFile, 'r') as f:
					log = f.read().decode('utf-8-sig')
					# summary line will be attached even if build done without any other messages
					if len(log.split('\n')) > 1:
						valid = False
						errors.add(Error('buildFLA', [projects], str, log, None))
						print log
				os.remove(logFile)
	try:
		return {
			dst: readSWF(src)
			for src, dst in projects.items()
		}
	except AssertionError:
		if not build:
			print 'buildFLA: swf not found, trying rebuild...'
			return buildFLA(errors, projects, True)
		raise


@builder
def buildFlashFD(path, errors=None):
	path = str(os.path.abspath(path))
	assert os.path.isfile(path), '%s not found' % path
	fdbuild = os.environ.get('FDBUILD')
	flexsdk = os.environ.get('FLEXSDK')
	if fdbuild and os.path.exists(fdbuild) and flexsdk and os.path.exists(flexsdk):
		args = [fdbuild, '-compiler:' + flexsdk, path]
		subprocess.check_output(args,
								shell=True,
								universal_newlines=True,
								stderr=subprocess.STDOUT)
	return readSWF(path)


@builder
def buildPython(path, filename, errors=None):
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


@builder
def buildGO(module, gopath, errors=None):
	"""
		Calls and returns stdout go in project work dir
	"""
	env = dict(os.environ)
	env['GOPATH'] = gopath

	filename = os.path.join(env['GOPATH'], 'bin', '%s.exe' % os.path.split(module)[-1])

	if '-f' in sys.argv or '-tools' in sys.argv or not os.path.isfile(filename):
		cwd = os.path.join(env['GOPATH'], 'src', module)
		try:
			if os.path.exists(cwd):
				shutil.rmtree(cwd)

			shutil.copytree(module, cwd)
				
			subprocess.check_output(['go', 'get'], cwd=cwd, env=env, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
			subprocess.check_output(['go', 'test'], cwd=cwd, env=env, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
			subprocess.check_output(['go', 'build', '-o', filename, '-ldflags', '-H=windowsgui'], cwd=cwd, env=env, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
		finally:
			if os.path.exists(cwd):
				shutil.rmtree(cwd)

	with open(filename, 'rb') as f:
		return f.read()


@builder
def buildPO(path, errors=None):
	return polib.pofile(path).to_binary()


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
	errros = Errors()
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
					write(excludes, package, fname + '.pyc', buildPython(errros, path, name))
				elif fext == '.po':
					write(excludes, package, fname + '.mo', buildPO(errros, path))

				if CONFIG.get('add_sources', False) or fext != '.pyc' or CONFIG.get('pass_pyc_files', False):
					if 'copy' not in CONFIG:
						CONFIG['copy'] = {}
					CONFIG['copy'][path] = dst

		for source, dst in CONFIG.get('flash_fdbs', {}).items():
			write(excludes, package, dst, buildFlashFD(errros, source))

		for dst, data in buildFLA(errros, CONFIG.get('flash_fla', {}), default={}).items():
			write(excludes, package, dst, data)

		gopath = str(os.path.abspath(CONFIG.get('gopath', tempfile.mkdtemp())))
		for source, dst in CONFIG.get('go', {}).items():
			write(excludes, package, dst, buildGO(errros, source, gopath))

		for path, dst in CONFIG.get('copy', {}).items():
			with open(path, 'rb') as f:
				write(excludes, package, dst, f.read())
	return errros

def getArg(idx, default):
	if idx < len(sys.argv):
		return sys.argv[idx]
	return default

def kill(executable):
	print 'Find and kill', executable
	while True:
		found = False
		for proc in psutil.process_iter():
			if proc.name() == executable:
				try:
					found = True

					print 'Kill', proc.pid
					psutil.Process(proc.pid).kill()
				except Exception as ex:
					print ex
		if not found:
			return
		time.sleep(0.1)

if __name__ == '__main__':
	if 'run' in sys.argv:
		runIdx = sys.argv.index('run')
		clientSuffix = getArg(runIdx + 1, '')
		executable = 'WorldOfTanks%s.exe' % clientSuffix
		kill(executable)
	else:
		runIdx = -1

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
		errors = build(os.path.abspath(os.path.join('bin', packageName)), CONFIG)
		if errors:
			print 'BUILD FAILED'
			print errors
			sys.exit(1)

		if 'deploy' in sys.argv:
			clientPath = getArg(sys.argv.index('deploy') + 1, None)
			assert clientPath is not None
			deploy(pathLine, clientPath)

			if runIdx != -1:
				args = getArg(runIdx + 2, '').split(' ')
				args.insert(0, os.path.join(clientPath, executable))
				print 'Run client:', ' '.join(args)
				subprocess.call(args)
		print 'BUILD DONE'
