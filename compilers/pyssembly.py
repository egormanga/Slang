#!/usr/bin/python3
# Slang Pyssembly compiler target

import pyssembly
from . import *
from Slang.ast import *
from utils import *

class Instrs:
	unopmap = {
		'+': 'POS',
		'-': 'NEG',
		'!': 'NOT',
		'~': 'INV',
		'not': 'NOT',
	}

	binopmap = {
		'+': 'ADD',
		'-': 'SUB',
		'*': 'MUL',
		'/': 'DIV',
		'//': 'FLOORDIV',
		'%': 'MOD',
		'**': 'POW',
		'<<': 'LSHIFT',
		'>>': 'RSHIFT',
		'&': 'AND',
		'|': 'OR',
		'^': 'XOR',
		'and': 'AND',
		'or': 'OR',
	}

	@init_defaults
	def __init__(self, *, name, ns, filename, argdefs=()):
		self.name, self.ns, self.filename = name, ns, filename
		self.instrs = list()
		self.consts = list()
		self.argnames = list()
		for i in argdefs:
			if (i.modifier is not None): raise SlCompilationError("argument modifiers are not supported yet", i.modifier)
			self.argnames.append(i.name.identifier)
		self.cellvars = self.argnames.copy()
		self.srclnotab = list()

	def compile(self):
		return pyssembly.Code('\n'.join(self.instrs), name=self.name, filename=self.filename.strip('"'), srclnotab=self.srclnotab, consts=self.consts, argnames=self.argnames)

	@dispatch
	def add(self, x: ASTRootNode):
		self.add(x.code)

	@dispatch
	def add(self, x: ASTCodeNode):
		lastln = int()
		for i in x.nodes:
			self.srclnotab.append(i.lineno-lastln)
			lastln = i.lineno
			l = len(self.instrs)
			self.add(i)
			self.srclnotab += [0]*(len(self.instrs)-l-1)

	@dispatch
	def add(self, x: ASTValueNode):
		self.add(x.value)

	@dispatch
	def add(self, x: ASTVardefNode):
		if (x.value is not None):
			self.load(x.value)
			self.store(x.name)

	@dispatch
	def add(self, x: ASTAssignmentNode):
		if (x.inplace_operator is not None): self.instrs.append(f"LOAD	({x.name})")
		self.load(x.value)
		if (x.inplace_operator is not None): self.instrs.append(f"INP_{self.binopmap[x.inplace_operator.operator]}")
		self.store(x.name)

	@dispatch
	def add(self, x: ASTFunccallNode):
		self.load(x)
		self.instrs.append("POP")

	@dispatch
	def add(self, x: ASTBlockNode):
		self.add(x.code)

	@dispatch
	def add(self, x: ASTFuncdefNode):
		code_ns = self.ns.derive(x.name.identifier)
		name = f"{x.name.identifier}__{self.ns.signatures[x.name.identifier].call.index(CallArguments(args=tuple(Signature.build(i, code_ns) for i in x.argdefs)))}"
		f_instrs = Instrs(name=f"{self.name}.{name}", ns=code_ns, filename=self.filename, argdefs=x.argdefs)
		f_instrs.add(x.code)
		#dlog(f"{x.__fsig__()} instrs:\n"+'\n'.join(f_instrs.instrs)+'\n')
		self.consts.append(f_instrs.compile().to_code())
		self.instrs += [
			f"LOAD	{len(self.consts)-1}",
			f"LOAD	('{self.name}.{name}')",
			f"MAKE_FUNCTION	0", # TODO: flags
		]
		self.store(name)

	@dispatch
	def add(self, x: ASTKeywordExprNode):
		if (x.keyword.keyword == 'import'):
			ns, _, name = x.value.identifier.partition('::')
			assert ns == 'py'
			self.instrs += [
				"LOAD	(0)", # TODO
				"LOAD	(None)", # TODO
			]
			self.instrs.append(f"IMPORT_NAME	({name})")
			self.store(name)
		elif (x.keyword.keyword == 'return'):
			self.load(x.value)
			self.instrs.append("RET")
		else: raise NotImplementedError(x.keyword)

	@dispatch
	def add(self, x: ASTConditionalNode):
		self.load(x.condition)
		self.instrs.append("JPOPF	:else")
		self.add(x.code)
		self.instrs += [
			"JUMPF	:end",
			":else",
			":end",
		]

	@dispatch
	def add(self, x: ASTForLoopNode):
		self.load(x.iterable)
		#self.cellvars.append(x.name.identifier) # TODO FIXME
		self.instrs += [
			"SETUP_LOOP	:end",
			"ITER",
			":for",
			"FOR	:else",
		]
		self.store(x.name)
		self.add(x.code)
		self.instrs += [
			"JUMPA	:for",
			":else",
			"POP_BLOCK",
			":end",
		]

	@dispatch
	def add(self, x: ASTWhileLoopNode):
		self.instrs += [
			"SETUP_LOOP	:end",
			":while",
		]
		self.load(x.condition)
		self.instrs.append("JPOPF	:else")
		self.add(x.code)
		self.instrs += [
			"JUMPA	:while",
			":else",
			"POP_BLOCK",
			":end",
		]

	@dispatch
	def add(self, x: ASTElseClauseNode):
		assert (self.instrs[-1] == ":end")
		popped = [self.instrs.pop()]
		if (self.instrs[-1] == "POP_BLOCK"): popped.append(self.instrs.pop())
		self.add(x.code)
		self.instrs += reversed(popped)

	@dispatch
	def load(self, x: ASTLiteralNode):
		self.instrs.append(f"LOAD	({x.literal})")

	@dispatch
	def load(self, x: ASTIdentifierNode):
		self.load(x.identifier)

	@dispatch
	def load(self, x: ASTValueNode):
		self.load(x.value)

	@dispatch
	def load(self, x: ASTFunccallNode):
		if (isinstance(x.callable, ASTValueNode) and isinstance(x.callable.value, ASTIdentifierNode) and x.callable.value.identifier in self.ns.signatures):
			self.load(f"{x.callable.value.identifier}__{self.ns.signatures[x.callable.value.identifier].call.index(CallArguments.build(x, self.ns))}")
		else: self.load(x.callable)
		n = int()

		for i in x.callargs.callargs:
			self.load(i)
			n += 1
		if (x.callargs.starargs):
			if (n):
				self.instrs.append(f"BUILD_TUPLE	{n}")
				n = 1
			for i in x.callargs.starargs:
				self.load(i)
				n += 1
			self.instrs.append(f"BUILD_TUPLE_UNPACK_WITH_CALL	{n}")
			n = 0

		for i in x.callkwargs.callkwargs:
			self.load(f"'{i[0]}'")
			self.load(i[1])
			n += 1
		if (n and (x.callargs.starargs or x.callkwargs.starkwargs)):
			self.instrs.append(f"BUILD_MAP	{n}")
			n = 1
		if (x.callkwargs.starkwargs):
			for i in x.callkwargs.starkwargs:
				self.load(i)
				n += 1
			self.instrs.append(f"BUILD_MAP_UNPACK_WITH_CALL	{n}")
			n = 1

		self.instrs.append(f"CALL{'EX' if (x.callargs.starargs or x.callkwargs.starkwargs) else 'KW' if (x.callkwargs.callkwargs) else ''}	{n}")

	@dispatch
	def load(self, x: ASTAttrgetNode):
		self.load(x.value)
		assert x.optype.special == '.' # TODO
		self.instrs.append(f"GETATTR	({x.attr})")

	@dispatch
	def load(self, x: ASTUnaryExprNode):
		self.load(x.value)
		self.instrs.append(self.unopmap[x.operator.operator])

	@dispatch
	def load(self, x: ASTBinaryExprNode):
		self.load(x.lvalue)
		char = isinstance(Signature.build(x.lvalue, self.ns), stdlib.char)
		if (char): self.instrs.append("CALL	(ord) 1")
		if (x.operator.operator == 'xor'): self.instrs.append("BOOL")
		self.load(x.rvalue)
		if (char and isinstance(Signature.build(x.rvalue, self.ns), stdlib.char)): self.instrs.append("CALL	(ord) 1")
		if (x.operator.operator == 'xor'): self.instrs.append("BOOL")
		if (x.operator.operator == 'to'): self.instrs.append("CALL	(range) 2")
		else: self.instrs.append(self.binopmap[x.operator.operator])
		if (x.operator.operator == 'xor'): self.instrs.append("BOOL")
		if (char and x.operator.operator not in keyword_operators): self.instrs.append("CALL	(chr) 1")

	@dispatch
	def load(self, x: ASTItemgetNode):
		self.load(x.value)
		self.load(x.key)
		self.instrs.append("SUBSCR")

	@dispatch
	def load(self, x: str):
		self.instrs.append(f"LOAD	{f'${x}' if (x in self.cellvars) else f'({x})'}")

	@dispatch
	def store(self, x: ASTIdentifierNode):
		self.store(x.identifier)

	@dispatch
	def store(self, x: str):
		self.instrs.append(f"STORE	{f'${x}' if (x in self.cellvars) else f'({x})'}")

class PyssemblyCompiler(Compiler):
	@classmethod
	def compile_ast(cls, ast, ns, *, filename):
		instrs = Instrs(name='<module>', ns=ns, filename=filename)
		instrs.add(ast)
		#dlog("Instrs:\n"+'\n'.join(instrs.instrs)+'\n')
		code = instrs.compile().to_code()
		#dis.show_code(code)
		#dis.dis(code)
		#print()
		return code

# by Sdore, 2019
