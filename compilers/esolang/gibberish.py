#!/usr/bin/python3
# Slang Esolang Gibberish compilation target (PoC)
# https://esolangs.org/wiki/Gibberish_(programming_language)

from .. import *
from ...ast import *
from utils import *

class Instrs:
	binopmap = {
		'+': b'ea',
		'-': b'es',
		'*': b'em',
		'/': b'ed',
		'<<': b'fl',
		'>>': b'fr',
		'&': b'ga',
	}

	@init_defaults
	@autocast
	def __init__(self, ns, stack: Slist, functions: dict):
		self.ns, self.stack, self.functions = ns, stack, functions
		self.code = bytearray()

	@dispatch
	def add(self, x: ASTRootNode):
		self.add(x.code)

	@dispatch
	def add(self, x: ASTCodeNode):
		for i in x.nodes:
			self.add(i)

	@dispatch
	def add(self, x: ASTVardefNode):
		if (x.value is not None):
			self.load(x.value)
			self.stack[-1] = Signature.build(x, self.ns)

	@dispatch
	def add(self, x: ASTAssignmentNode):
		sig = Signature.build(x.name, self.ns)
		for ii, i in enumerate(self.stack):
			if (i == sig): self.stack[ii] = None
		self.load(x.value)
		self.stack[-1] = sig

	@dispatch
	def add(self, x: ASTFunccallNode):
		self.load(x)
		self.code += b'ev'
		self.stack.pop()

	@dispatch
	def add(self, x: ASTFuncdefNode):
		code_ns = self.ns.derive(x.name.identifier)
		if (x.name.identifier == 'main'):
			assert not x.argdefs
			name = x.name.identifier
		else: name = f"{x.name.identifier}__{self.ns.signatures[x.name.identifier].call.index(CallArguments(args=tuple(Signature.build(i, code_ns) for i in x.argdefs)))}"
		f_instrs = Instrs(ns=code_ns, stack=(Signature.build(i, code_ns) for i in x.argdefs), functions=self.functions.copy())
		f_instrs.add(x.code)
		#dlog(f"{x.__fsig__()} instrs:\n"+'\n'.join(f_instrs.instrs)+'\n')
		self.functions[name] = f_instrs

	@dispatch
	def add(self, x: ASTKeywordExprNode):
		if (x.keyword.keyword == 'return'):
			self.load(x.value)
		else: raise NotImplementedError(x.keyword)

	@dispatch
	def load(self, x: ASTLiteralNode):
		s = str(eval(str(x.literal))).encode().split(b']')
		if (s):
			s[0] = b'['+s[0]
			s[-1] += b']'
		self.code += b'][93]eigtec['.join(s) + b'c'*(len(s)-1)
		if (issubclass(literal_type(x.literal), (int, float))): self.code += b'ei'
		self.stack.append(None)

	@dispatch
	def load(self, x: ASTIdentifierNode):
		dlog(self.stack)
		sig = Signature.build(x, self.ns)
		i = self.stack.rindex(sig)
		self.code += (b'[%d]eip' if (i >= 10) else b'%dep') % i
		self.stack.append(sig)

	@dispatch
	def load(self, x: ASTValueNode):
		self.load(x.value)

	@dispatch
	def load(self, x: ASTFunccallNode):
		assert not (x.callargs.starargs or x.callkwargs.callkwargs or x.callkwargs.starkwargs)
		if (x.callable.value.identifier == 'print'):
			for i in x.callargs.callargs[:-1]:
				self.load(i)
				self.code += b'eq[32]eigteq'
				self.stack.pop()
			if (x.callargs.callargs):
				self.load(x.callargs.callargs[-1])
				self.stack.pop()
			else: self.code += b'[]'
			self.code += b'eo'
			self.stack.append(None)
			return
		for i in x.callargs.callargs[::-1]:
			self.load(i)
			self.stack.pop()
		self.code += self.functions[f"{x.callable.value.identifier}__{self.ns.signatures[x.callable.value.identifier].call.index(CallArguments.build(x, self.ns))}" if (isinstance(x.callable, ASTValueNode) and isinstance(x.callable.value, ASTIdentifierNode) and x.callable.value.identifier in self.ns.signatures) else x.callable.value.identifier].code#.join((b'{', b'}'))

	@dispatch
	def load(self, x: ASTBinaryExprNode):
		self.load(x.lvalue)
		self.load(x.rvalue)
		self.code += self.binopmap[x.operator.operator]
		self.stack.pop()
		self.stack.pop()
		self.stack.append(None)

class GibberishCompiler(Compiler):
	ext = '.gib'

	@classmethod
	def compile_ast(cls, ast, ns, *, filename):
		instrs = Instrs(ns=ns)
		instrs.add(ast)
		code = bytes(instrs.code)
		dlog("Code:\n"+code.decode())
		return code

compiler = GibberishCompiler

# by Sdore, 2020
