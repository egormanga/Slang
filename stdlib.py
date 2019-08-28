#!/usr/bin/python3
# Slang stdlib

from .ast import Signature, Function, Object
from .tokens import *
from utils import *

class Builtin(Signature):
	def __init__(self):
		pass

	@property
	def __reprname__(self):
		return type(self).mro()[1].__name__

	@property
	def typename(self):
		return type(self).__name__

class BuiltinFunction(Builtin, Function): pass

class BuiltinObject(Builtin, Object): pass

class BuiltinType(Builtin):
	@init_defaults
	@autocast
	def __init__(self, *, modifiers: paramset):
		self.modifiers = modifiers

class void(BuiltinType): pass

class bool(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		if (valsig is None):
			if (op in map(UnaryOperator, '+-~')): return int
			if (op in map(UnaryOperator, ('not', '!'))): return bool
		raise KeyError()

class int(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		if (valsig is None):
			if (op in map(UnaryOperator, '+-~')): return int
			if (op in map(UnaryOperator, ('not', '!'))): return bool
		if (not isinstance(valsig, (int, float))): raise KeyError()
		if (op in map(BinaryOperator, ('**', *'+-*'))): return valsig
		if (op in map(BinaryOperator, ('//', '<<', '>>', *'&^|'))): return int
		if (op == BinaryOperator('/')): return float
		if (op == BinaryOperator('to')): return int
		raise KeyError()

class float(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		if (valsig is None):
			if (op in map(UnaryOperator, ('not', *'!+-'))): return float
		if (not isinstance(valsig, (int, float))): raise KeyError()
		if (op in map(BinaryOperator, ('**', *'+-*'))): return float
		if (op == BinaryOperator('/')): return float
		if (op == BinaryOperator('//')): return int
		raise KeyError()

class str(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		if (valsig is None): raise KeyError()
		if (isinstance(valsig, str) and op == BinaryOperator('+')): return str
		if (isinstance(valsig, int) and op == BinaryOperator('*')): return str
		raise KeyError()

	@staticitemget
	@instantiate
	def itemget(keysig):
		if (isinstance(keysig, int)): return char
		raise KeyError()

class char(BuiltinType):
	@staticitemget
	@instantiate
	def operators(op, valsig=None):
		if (valsig is None): raise KeyError()
		if (isinstance(valsig, str) and op == BinaryOperator('+')): return str
		if (isinstance(valsig, int) and op == BinaryOperator('*')): return str
		if (isinstance(valsig, (char, int)) and op in map(BinaryOperator, '+-')): return char
		raise KeyError()

i8 = i16 = i32 = i64 = i128 = \
u8 = u16 = u32 = u64 = u128 = int
f8 = f16 = f32 = f64 = f128 = \
uf8 = uf16 = uf32 = uf64 = uf128 = float
# TODO: implement these types

class print(BuiltinFunction):
	callargssigstr = "print(...)"

	@staticitemget
	@instantiate
	def call(callargssig):
		if (callargssig.kwargs or callargssig.starkwargs): raise KeyError()
		return void

builtin_names = {j.__name__: globals()[j.__name__] for i in map(operator.methodcaller('__subclasses__'), Builtin.__subclasses__()) for j in i}
builtin_names.update({i: globals()[i] for i in (i+j for j in map(builtins.str, (8, 16, 32, 64, 128)) for i in (*'iuf', 'uf'))})

# by Sdore, 2019
