#!/usr/bin/python3

from utils.nolog import *

builtin_types = {i for i in itertools.chain(builtins.__dict__.values(), types.__dict__.values()) if isinstance(i, type)}

@dispatch
def gen(x, name: NoneType, *, scope: dict):
	return gen(x, '', scope=scope).rstrip(' ')

@dispatch
def gen(x: lambda x: x is NoneType, name: str, *, scope: dict):
	return f"void {name}"

@dispatch
def gen(x: lambda x: isinstance(x, type) and (getattr(x, '__module__', None) == '__main__' or x in builtin_types), name: str, *, scope: dict):
	return f"{x.__name__} {name}"

@dispatch
def gen(x: lambda x: typing_inspect.get_origin(x) is not None, name: str, *, scope: dict):
	o = typing_inspect.get_origin(x)
	if (o is typing.Literal):
		return gen(type(x.__args__[0]), name, scope=scope)
	elif (o is typing.Union):
		if (x.__args__[1] is NoneType): return f"{gen(x.__args__[0], name, scope=scope).rstrip()}?"
		else: return f"{'|'.join(gen(i, None, scope=scope) for i in x.__args__)} {name}"
	elif (o in (tuple, list, dict, set, frozenset)):
		return f"{o.__name__}{', '.join(gen(i, None, scope=scope) for i in x.__args__ if i is not ...).join('[]') if (x.__args__ and x.__args__ != (typing.Any,) and x.__args__ != (typing.Any, ...)) else ''} {name}" # TODO args

	# TODO FIXME:
	elif (o is collections.abc.Iterable):
		return f"iterable {name}"
	elif (o is collections.abc.Iterator):
		return f"iterator {name}"
	elif (o is collections.abc.Sequence):
		return f"sequence {name}"
	elif (o is collections.abc.Mapping):
		return f"mapping[{gen(x.__args__[0], None, scope=scope)}, {gen(x.__args__[1], None, scope=scope)}] {name}"
	elif (o is collections.abc.ItemsView):
		return f"items {name}"
	elif (o is collections.abc.KeysView):
		return f"keys {name}"
	elif (o is collections.abc.ValuesView):
		return f"values {name}"
	elif (o is collections.abc.Set):
		return f"set {name}"
	elif (o is collections.abc.Callable):
		return f"callable {name}"

	elif (o is type):
		return f"{x.__args__[0].__name__} {name}"
	else: raise NotImplementedError(x, o)

@dispatch
def gen(x: lambda x: x is typing.Any, name: str, *, scope: dict): # TODO FIXME
	return f"object {name}"

@dispatch
def gen(x: typing.TypeVar, name: str, *, scope: dict):
	return f"{x.__name__} {name}"

@dispatch
def gen(x: lambda x: isinstance(x, type) and issubclass(x, typing.Protocol), name: str, *, scope: dict):
	if (x is typing.SupportsInt):
		t = int
	elif (x is typing.SupportsFloat):
		t = float
	else: raise NotImplementedError(x)
	return gen(t, name, scope=scope)

@dispatch
def gen(x: function, name: str, *, scope: dict):
	fsig = inspect.signature(x)
	return f"{gen(typing.get_type_hints(x, scope)['return'], None, scope=scope)} {name}({', '.join(gen(v, x, k, scope=scope) for ii, (k, v) in enumerate(fsig.parameters.items()) if not (ii == 0 and k == 'self'))})"

@dispatch
def gen(x: inspect.Parameter, f, name: str, *, scope: dict):
	t = gen(typing.get_type_hints(f, scope)[x.name], name, scope=scope)
	if (x.default is not inspect._empty):
		if (x.default is ...):
			if (t[-1:] != '?'): t += '?'
		else: raise NotImplementedError(x.default)
	return t

@dispatch
def gen(x: property, name: str, *, scope: dict):
	return gen(typing.get_type_hints(x.fget, scope)['return'], name, scope=scope)

@dispatch
def gen(x: lambda x: isinstance(x, type) and x.__module__ == '__main__', name: str, *, scope: dict):
	return f"{x.__name__} {name}"

#@dispatch
#def gen(x: type, name: str, *, scope: dict):
#	return f"{type.__name__} {name}"

@dispatch
def gen(x: lambda x: isinstance(x, type) and x.__module__ == '__main__', *, scope: dict):
	r = []

	for k, v in typing.get_type_hints(x, scope).items():
		r.append(f"{gen(v, k, scope=scope)};".lstrip(';'))

	for k, v in x.__dict__.items():
		if (k in ('__module__', '__doc__')): continue
		if (not isinstance(v, property) and (not isinstance(v, function) or getattr(v, '__module__', None) != '__main__')): continue
		r.append(f"{gen(v, k, scope=scope)};".lstrip(';'))

	if (not r): return ''
	return f"class {x.__name__} {{\n\t"+'\n\t'.join(r)+'\n}'

@dispatch
def gen(x: CodeType, *, package):
	r = {'__name__': '__main__', '__package__': package}
	exec(x, r)
	return '\n\n'.join(Slist(gen(i, scope=r) for i in r.values() if isinstance(i, type) and i.__module__ == '__main__').strip(''))

class AnnotationsFileLoader(importlib.machinery.SourceFileLoader):
	header = "from __future__ import annotations"

	def get_data(self, path):
		dlog(path)
		data = super().get_data(path)
		if (not path.endswith('.pyi')): return data
		return (self.header+'\n\n').encode() + data

def path_hook_factory(f):
	def path_hook(path):
		finder = f(path)
		finder._loaders.insert(0, ('.pyi', AnnotationsFileLoader))
	return path_hook

@apmain
@aparg('typeshed', metavar='<typeshed repo path>')
@aparg('output', metavar='<stdlib .sld output dir>')
def main(cargs):
	if (sys.version_info < (3,8)): raise NotImplementedError("Currently only Python 3.8+ is supported.")

	dirs = ('stdlib', 'stubs')

	import __future__

	sys.dont_write_bytecode = True
	sys.path = [__future__.__file__] + [os.path.join(cargs.typeshed, i) for i in dirs] + [os.path.join(cargs.typeshed, 'stubs', i, j) for i in os.listdir(os.path.join(cargs.typeshed, 'stubs')) for j in os.listdir(os.path.join(cargs.typeshed, 'stubs', i))]
	#sys.path_hooks[-1] = path_hook_factory(sys.path_hooks[-1])
	#sys.path_hooks[-1] = importlib.machinery.FileFinder.path_hook((AnnotationsFileLoader, ['.pyi']+[i for i in importlib.machinery.all_suffixes() if i != '.pyc']))
	sys.path_hooks = [importlib.machinery.FileFinder.path_hook((AnnotationsFileLoader, ['.pyi']))]
	sys.meta_path = [sys.meta_path[2]]

	skipped = int()
	for d in dirs:
		for v in sorted(os.listdir(os.path.join(cargs.typeshed, d))):
			if (v in ('@python2', '_typeshed')): continue
			for p, _, n in os.walk(os.path.join(cargs.typeshed, d, v)):
				if ('@python2' in p): continue
				o = os.path.join(cargs.output, p.partition(os.path.join(cargs.typeshed, d, v, ''))[2])
				os.makedirs(o, exist_ok=True)
				for i in sorted(n, key=lambda x: 'builtins.pyi' not in x):
					if (not i.endswith('.pyi')): continue
					filename = os.path.join(p, i)
					log(filename)
					code = compile(b"from __future__ import annotations\n\n"+open(filename, 'rb').read(), filename, 'exec')
					try: r = gen(code, package=os.path.splitext(filename)[0].replace('/', '.'))
					except Exception as ex:
						if ('builtins.pyi' in i): raise
						logexception(ex)
						skipped += 1
						raise # XXX
					else:
						if (not r): continue
						if ('builtins.pyi' in i): r = 'import sld:std:*;\n\n'+r
						else: r = 'import py:builtins:*;\n\n'+r
						open(os.path.join(o, os.path.splitext(i)[0]+'.sld'), 'w').write(r+'\n')

	if (skipped): print(f"\033[93m{skipped} errors caught ({skipped} files skipped).\033[0m")
	print("\033[1mSuccess!\033[0m")

if (__name__ == '__main__'): exit(main(nolog=True))
else: logimported()

# by Sdore, 2021
