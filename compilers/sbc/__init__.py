#!/usr/bin/python3
# Slang Bytecode (SBC) compiler target

from . import *
from .. import *
from ...ast import *
from utils import *

NOP	= 0x00
POP	= 0x01
DUP	= 0x02
RET	= 0x03
CODE	= 0x04
IF	= 0x05
LOOP	= 0x06
ELSE	= 0x07
END	= 0x08
CALL	= 0x09
ASGN	= 0x0A
BLTIN	= 0x0B
CONST	= 0x0C
SGET	= 0x0D
SSET	= 0x0E

def readVarInt(s):
	r = int()
	i = int()
	while (True):
		b = s.recv(1)[0]
		r |= (b & (1 << 7)-1) << (7*i)
		if (not b & (1 << 7)): break
		i += 1
	return r

def writeVarInt(v):
	assert v >= 0
	r = bytearray()
	while (True):
		c = v & (1 << 7)-1
		v >>= 7
		if (v): c |= (1 << 7)
		r.append(c)
		if (not v): break
	return bytes(r)

class Instrs:
	unopmap = {
		'!': 'not',
		'+': 'abs',
		'-': 'neg',
		'~': 'inv',
		'++': 'inc',
		'--': 'dec',
		'**': 'sqr',
		'not': 'not',
	}
	binopmap = {
		'+': 'add',
		'-': 'sub',
		'*': 'mul',
		'/': 'div',
		'//': 'idiv',
		'%': 'mod',
		'**': 'pow',
		'<<': 'ls',
		'>>': 'rs',
		'&': 'and',
		'^': 'xor',
		'|': 'or',

		'&&': 'and',
		'^^': 'xor',
		'||': 'or',
		'==': 'eq',
		'!=': 'ne',
		'<': 'lt',
		'>': 'gt',
		'<=': 'le',
		'>=': 'ge',

		'is': 'is',
		'is not': 'isnot',
		'in': 'in',
		'not in': 'notin',
		'isof': 'isof',
		'and': 'and',
		'but': 'and',
		'xor': 'xor',
		'or': 'or',
		'to': 'range',
	}

	@init_defaults
	def __init__(self, *, name, ns, filename, scpcells: indexset):
		self.name, self.ns, self.filename, self.scpcells = name, ns, filename, scpcells
		self.instrs = bytearray()
		self.opmap = dict()

	def compile(self):
		return bytes(self.instrs)

	@dispatch
	def add(self, opcode: int, *args: int):
		self.instrs.append(opcode)
		if (args): self.instrs += bytes(args)

	@dispatch
	def add(self, x: ASTRootNode):
		self.add(x.code)

	@dispatch
	def add(self, x: ASTBlockNode):
		self.add(x.code)

	@dispatch
	def add(self, x: ASTCodeNode):
		for i in x.nodes:
			self.add(i)

	@dispatch
	def add(self, x: ASTValueNode):
		self.add(x.value)

	@dispatch
	def add(self, x: ASTVardefNode):
		if (x.value is not None):
			self.load(x.value, sig=Signature.build(x.type, ns=self.ns))
			self.store(x.name)

	@dispatch
	def add(self, x: ASTFunccallNode):
		self.load(x)
		self.add(POP)

	@dispatch
	def add(self, x: ASTKeywordDefNode):
		if (x.keyword.keyword == 'main'):
			name = '<main>'
			code_ns = self.ns.derive(name)
			f_instrs = Instrs(name=name, ns=code_ns, filename=self.filename)
			f_instrs.add(x.code)
			self.add(CODE)
			self.instrs += f_instrs.instrs
			self.add(END)
			self.add(CALL, 0)
			self.add(POP)
		else: raise NotImplementedError(x.keyword)

	@dispatch
	def add(self, x: ASTConditionalNode):
		self.load(x.condition)
		self.add(IF)
		self.add(x.code)
		self.add(END)

	@dispatch
	def add(self, x: ASTForLoopNode):
		self.load(x.iterable)
		self.builtin('iter', 1)
		self.store(x.name)
		self.add(DUP, 0)
		self.add(LOOP)
		self.add(x.code)
		self.builtin('iter', 1)
		self.store(x.name)
		self.add(DUP, 0)
		self.add(END)

	@dispatch
	def add(self, x: ASTWhileLoopNode):
		self.load(x.condition)
		self.add(LOOP)
		self.add(x.code)
		self.load(x.condition)
		self.add(END)

	@dispatch
	def add(self, x: ASTElseClauseNode):
		assert (self.instrs[-1] == END)
		end = self.instrs.pop()
		self.add(ELSE)
		self.add(x.code)
		self.add(end)

	@dispatch
	def load(self, x: ASTLiteralNode, *, sig=None):
		if (sig is None): sig = Signature.build(x, ns=self.ns)

		if (hasattr(sig, 'fmt')):
			t, v = sig.__class__.__name__, struct.pack(sig.fmt, int(x.literal))
		elif (isinstance(sig, stdlib.int)):
			t, v = 'i', writeVarInt(eval_literal(x))
		elif (isinstance(sig, stdlib.str)):
			t, v = 's', eval_literal(x).encode('utf-8')
		elif (isinstance(sig, stdlib.char)):
			t, v = 'c', eval_literal(x).encode('utf-8') # TODO
		else: raise NotImplementedError(sig)

		self.add(CONST)
		self.instrs += t.encode('utf-8')+b'\0' + writeVarInt(len(v)) + v

	@dispatch
	def load(self, x: ASTIdentifierNode, **kwargs):
		self.load(x.identifier, **kwargs)

	@dispatch
	def load(self, x: ASTValueNode, **kwargs):
		self.load(x.value, **kwargs)

	@dispatch
	def load(self, x: ASTFunccallNode):
		nargs = int()

		for i in x.callargs.callargs:
			self.load(i)
			nargs += 1
		if (x.callargs.starargs): raise NotImplementedError()

		if (x.callkwargs.callkwargs): raise NotImplementedError()
		if (x.callkwargs.starkwargs): raise NotImplementedError()

		if (isinstance(x.callable, ASTValueNode) and isinstance(x.callable.value, ASTIdentifierNode) and x.callable.value.identifier in self.ns.signatures):
			raise NotImplementedError()
			#name = f"{x.callable.value.identifier}({CallArguments.build(x, self.ns)})"
			#self.load(name)
			#self.load(name+'.len')
			#self.add(EXEC)
		else:
			self.load(x.callable)
			self.add(CALL, nargs)

	@dispatch
	def load(self, x: ASTAttrgetNode):
		if (str(x.value) != 'stdio'): raise NotImplementedError(x)
		if (x.optype.special != '.'): raise NotImplementedError(x)
		self.builtin(str(x.attr))

	@dispatch
	def load(self, x: ASTBinaryExprNode, **kwargs):
		self.load(x.lvalue, **kwargs)
		self.load(x.rvalue, **kwargs)
		self.builtin(self.binopmap[x.operator.operator], 2)

	@dispatch
	def load(self, x: str, **kwargs):
		self.add(SGET, self.scpcells[x])

	@dispatch
	def store(self, x: ASTIdentifierNode):
		self.store(x.identifier)

	@dispatch
	def store(self, x: str):
		self.add(SSET, self.scpcells[x])

	@dispatch
	def assign(self, builtin: str,
			 nargs_code: lambda nargs_code: isinstance(nargs_code, int) and 0 <= nargs_code < 4,
			 nargs_stack: lambda nargs_stack: isinstance(nargs_stack, int) and 0 <= nargs_stack < 64,
			 opcode: int = None):
		self.builtin(builtin)
		if (opcode is None): opcode = first(sorted(set(range(0x10, 0x100)) - set(self.opmap.values())))
		self.add(ASGN, opcode, (nargs_code << 6) | nargs_stack)
		self.opmap[builtin, nargs_code, nargs_stack] = opcode

	@dispatch
	def builtin(self, builtin: str):
		self.add(BLTIN)
		self.instrs += builtin.encode('ascii')+b'\0'

	@dispatch
	def builtin(self, builtin: str, nargs: int):
		if (nargs is not None and len(self.opmap) < 0xf0): self.assign(builtin, 0, nargs)
		if ((builtin, 0, nargs) in self.opmap): self.add(self.opmap[builtin, 0, nargs])
		else: self.builtin(builtin); self.add(CALL, nargs)

class SBCCompiler(Compiler):
	ext = '.sbc'

	@classmethod
	def compile_ast(cls, ast, ns, *, filename):
		instrs = Instrs(name='<module>', ns=ns, filename=filename)
		instrs.add(ast)
		code = instrs.compile()
		return code

compiler = SBCCompiler

# by Sdore, 2020
