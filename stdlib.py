#!/usr/bin/python3
# Slang stdlib

from .ast import Signature, Function, Object, Collection, CallArguments, MultiCollection
from .tokens import *
from utils import *

class Builtin(Signature):
	@classitemget
	def attrops(cls, optype, attr):
		if (optype == '.'):
			try: return getattr(cls, attr)()
			except AttributeError: raise KeyError()
		raise KeyError()

	@property
	def __reprname__(self):
		return first(i.__name__ for i in self.__class__.mro() if i.__name__.startswith('Builtin'))

	@property
	def typename(self):
		return self.__class__.__name__

class BuiltinFunction(Builtin, Function):
	def __init__(self):
		super().__init__(name=self.__class__.__name__)

class BuiltinObject(Builtin, Object): pass

class BuiltinType(Builtin):
	def __eq__(self, x):
		return (super().__eq__(x) or issubclass(x.__class__, self.__class__) or issubclass(self.__class__, x.__class__))

	@staticitemget
	@instantiate
	def operators(op, valsig=None, selftype=None):
		if (valsig is None):
			if (op in operators[9]): return bool  # unary `not'
		else:
			assert (selftype is not None)
			if (isinstance(valsig, selftype) and op in operators[8]): return bool  # comparisons
			if (op in operators[10]+operators[11]+operators[12]): return type(valsig)  # binary `and'. `xor', `or'
		raise KeyError()

@singleton
class Any(BuiltinType):
	def __eq__(self, x):
		return True

class auto(BuiltinType): pass

class void(BuiltinType):
	@staticitemget
	def operators(op, valsig=None):
		raise KeyError()

class bool(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		try: return BuiltinType.operators(op, valsig=valsig, selftype=bool)
		except KeyError: pass
		if (valsig is None):
			if (op in map(UnaryOperator, '+-~')): return int
			if (op == UnaryOperator('!')): return bool
		raise KeyError()

class int(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		try: return BuiltinType.operators(op, valsig=valsig, selftype=int)
		except KeyError: pass
		if (valsig is None):
			if (op in map(UnaryOperator, '+-~')): return int
			if (op == UnaryOperator('!')): return bool
		if (isinstance(valsig, (int, float))):
			if (op in map(BinaryOperator, ('**', *'+-*%'))): return valsig
			if (op in map(BinaryOperator, ('//', '<<', '>>', *'&^|'))): return int
			if (op == BinaryOperator('/')): return float
		if (isinstance(valsig, int)):
			if (op == BinaryOperator('to')): return range
		raise KeyError()

class float(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		try: return BuiltinType.operators(op, valsig=valsig, selftype=float)
		except KeyError: pass
		if (valsig is None):
			if (op in map(UnaryOperator, '+-')): return float
			if (op == UnaryOperator('!')): return bool
		if (isinstance(valsig, (int, float))):
			if (op in map(BinaryOperator, ('**', *'+-*%'))): return float
			if (op == BinaryOperator('/')): return float
			if (op == BinaryOperator('//')): return int
		raise KeyError()

class str(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		try: return BuiltinType.operators(op, valsig=valsig, selftype=str)
		except KeyError: pass
		if (valsig is not None):
			if (isinstance(valsig, (char, str)) and op == BinaryOperator('+')): return str
			if (isinstance(valsig, int) and op == BinaryOperator('*')): return str
		raise KeyError()

	@staticitemget
	@instantiate
	def itemget(keysig, key):
		if (isinstance(keysig, int)): return char
		raise KeyError()

	class rstrip(BuiltinFunction):
		callargssigstr: "rstrip(char)"

		@staticmethod
		@instantiate
		def compatible_call(callarguments, ns):
			if (callarguments.kwargs or callarguments.starkwargs): return None
			return (None, str())

	class count(BuiltinFunction):
		callargssig: "count(char)"

		@staticmethod
		@instantiate
		def compatible_call(callarguments, ns):
			if (callarguments.kwargs or callarguments.starkwargs): return None
			return (None, int())

class char(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		try: return BuiltinType.operators(op, valsig=valsig, selftype=char)
		except KeyError: pass
		if (valsig is not None):
			if (isinstance(valsig, str) and op in map(BinaryOperator, ('+', 'in'))): return str
			if (isinstance(valsig, int) and op == BinaryOperator('*')): return str
			if (isinstance(valsig, (char, int)) and op in map(BinaryOperator, '+-')): return char
		raise KeyError()

class i8(int): fmt: 'b'
class u8(int): fmt: 'B'
class i16(int): fmt: 'h'
class u16(int): fmt: 'H'
class i32(int): fmt: 'i'
class u32(int): fmt: 'I'
class i64(int): fmt: 'q'
class u64(int): fmt: 'Q'
#class i128(int): fmt: '
#class u128(int): fmt: '

#class f8(float): fmt: '
#class f16(float): fmt: 'e'
#class f32(float): fmt: 'f'
#class f64(float): fmt: 'd'
#class f128(float): fmt: '
#uf8 = uf16 = uf32 = uf64 = uf128 = float

class range(BuiltinType):
	keytype: int
	valtype: int

	@staticitemget
	def operators(op, valsig=None):
		raise KeyError()

class iterable(Collection, BuiltinType): pass

class list(iterable):
	keytype: int

	def __init__(self, *, valtype=Any):
		super().__init__(keytype=self.keytype, valtype=valtype)

	@staticitemget
	def attrops(optype, attr):
		if (optype == '.'):
			if (attr == 'each'): return _each()
		raise KeyError()

class tuple(iterable, MultiCollection):
	keytype: int

	def __init__(self, *, valtypes=()):
		super().__init__(keytype=self.keytype, valtypes=valtypes)

class stdio(BuiltinObject):
	class println(BuiltinFunction):
		callargssigstr: "println(...)"

		@staticmethod
		def compatible_call(callarguments, ns):
			if (callarguments.kwargs or callarguments.starkwargs): return None
			return (None, void())

class _map(BuiltinFunction):
	@staticmethod
	def compatible_call(callarguments, ns):
		if (len(callarguments.args) != 1 or
		    callarguments.starargs or
		    callarguments.kwargs or
		    callarguments.starkwargs): return None
		return (None, list(valtype=Any))


class _each(BuiltinFunction):
	@staticmethod
	def compatible_call(callarguments, ns):
		if (len(callarguments.args) != 1 or
		    callarguments.starargs or
		    callarguments.kwargs or
		    callarguments.starkwargs): return None
		#fsig = Signature.build(callarguments.args[0], ns)
		return (None, list(valtype=Any))

builtin_names = {k: v for i in map(allsubclassdict, Builtin.__subclasses__()) for k, v in i.items()}
builtin_names.update({i: globals()[i] for i in (i+j for j in map(builtins.str, (8, 16, 32, 64, 128)) for i in (*'iuf', 'uf') if i+j in globals())})

# by Sdore, 2020
