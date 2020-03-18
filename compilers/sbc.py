#!/usr/bin/python3
# Slang Bytecode (SBC) compiler target

from . import *
from Slang.ast import *
from utils import *

NOP	= 0x00
END	= 0x01
POP	= 0x02
RET	= 0x03
BLTIN	= 0x04
CODE	= 0x05

POS	= 0x10
NEG	= 0x11
NOT	= 0x12
INV	= 0x13
ATOI	= 0x14
ITOA	= 0x15
ITOF	= 0x16
CEIL	= 0x17
FLR	= 0x18
RND	= 0x19
CTOS	= 0x1a

ADD	= 0x20
SUB	= 0x21
MUL	= 0x22
DIV	= 0x23
IDIV	= 0x24
MOD	= 0x25
POW	= 0x26
LSH	= 0x27
RSH	= 0x28
AND	= 0x29
OR	= 0x2a
XOR	= 0x2b

EQ	= 0x30
NE	= 0x31
LT	= 0x32
GT	= 0x33
LE	= 0x34
GE	= 0x35
IS	= 0x36
ISNOT	= 0x37

IF	= 0x40
ELSE	= 0x41
EXEC	= 0x42

ALLOC	= 0xa0
EXTEND	= 0xa1
CONST	= 0xa2
JUMPF	= 0xa3
JUMPB	= 0xa4
SCPGET	= 0xa5
SCPSET	= 0xa6
CALL	= 0xa7

HASARG	= 0xa0

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
	unops = '+-!~'
	binops = (*'+-*/%', '**', '<<', '>>', '&', '|', '^')
	unopmap = {
		'+': POS,
		'-': NEG,
		'!': NOT,
		'~': INV,
		'not': NOT,
	}
	binopmap = {
		'+': ADD,
		'-': SUB,
		'*': MUL,
		'/': DIV,
		'//': IDIV,
		'%': MOD,
		'**': POW,
		'<<': LSH,
		'>>': RSH,
		'&': AND,
		'|': OR,
		'^': XOR,

		'==': EQ,
		'!=': NE,
		'<': LT,
		'>': GT,
		'<=': LE,
		'>=': GE,
		'is': IS,
		'is not': ISNOT,
	}

	@init_defaults
	def __init__(self, *, name, ns, filename, scpcells: indexset):
		self.name, self.ns, self.filename, self.scpcells = name, ns, filename, scpcells
		self.instrs = bytearray()

	def compile(self):
		return bytes(self.instrs)

	@dispatch
	def add(self, opcode: lambda x: isinstance(x, int) and x < HASARG):
		self.instrs.append(opcode)

	@dispatch
	def add(self, opcode: lambda x: isinstance(x, int) and x >= HASARG, oparg: int):
		self.instrs.append(opcode)
		self.instrs.append(oparg)

	@dispatch
	def add(self, x: ASTRootNode):
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
			self.load(x.value)
			self.store(x.name)

	@dispatch
	def add(self, x: ASTAssignmentNode):
		if (x.inplace_operator is not None): raise NotImplementedError()
		self.load(x.value)
		self.store(x.name)

	@dispatch
	def add(self, x: ASTFunccallNode):
		self.load(x)
		self.add(POP)

	@dispatch
	def add(self, x: ASTBlockNode):
		self.add(x.code)

	@dispatch
	def add(self, x: ASTFuncdefNode):
		code_ns = self.ns.derive(x.name.identifier)
		name = f"{x.name.identifier}__{self.ns.signatures[x.name.identifier].call.index(CallArguments(args=tuple(Signature.build(i, code_ns) for i in x.argdefs)))}"
		fname = f"{self.name}.<{x.__fsig__()}>"
		self.scpcells[name]
		f_instrs = Instrs(name=fname, ns=code_ns, filename=self.filename, scpcells=self.scpcells.copy())
		for i in x.argdefs:
			f_instrs.scpcells[i.name.identifier]
		f_instrs.add(x.code)
		self.add(CODE)
		self.instrs += f_instrs.instrs
		self.add(END)
		self.store(name+'.len')
		self.store(name)

	@dispatch
	def add(self, x: ASTKeywordExprNode):
		if (x.keyword.keyword == 'import'):
			ns, _, name = x.value.identifier.partition('::')
			raise TODO
			self.store(name)
		elif (x.keyword.keyword == 'return'):
			self.load(x.value)
			self.add(RET)
		else: raise NotImplementedError(x.keyword)

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
			self.add(EXEC)
			self.add(POP)
		else: raise NotImplementedError(x.keyword)

	@dispatch
	def add(self, x: ASTConditionalNode):
		self.load(x.condition)
		self.add(IF)
		self.add(x.code)
		self.add(END)

	#@dispatch
	def add_(self, x: ASTForLoopNode):
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

	#@dispatch
	def add_(self, x: ASTWhileLoopNode):
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

	#@dispatch
	def add_(self, x: ASTElseClauseNode):
		assert (self.instrs[-1] == ":end")
		popped = [self.instrs.pop()]
		if (self.instrs[-1] == "POP_BLOCK"): popped.append(self.instrs.pop())
		self.add(x.code)
		self.instrs += reversed(popped)

	@dispatch
	def load(self, x: ASTLiteralNode):
		sig = Signature.build(x, ns=self.ns)
		if (hasattr(sig, 'fmt')):
			v = struct.pack(sig.fmt, int(x.literal))
		elif (isinstance(sig, stdlib.int)):
			v = writeVarInt(int(x.literal))
		elif (isinstance(sig, stdlib.str)):
			v = x.literal.encode('utf8')
		else: raise NotImplementedError(sig)
		self.add(CONST, len(v))
		self.instrs += v

	@dispatch
	def load(self, x: ASTIdentifierNode):
		self.load(x.identifier)

	@dispatch
	def load(self, x: ASTValueNode):
		self.load(x.value)

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
			name = f"{x.callable.value.identifier}__{self.ns.signatures[x.callable.value.identifier].call.index(CallArguments.build(x, self.ns))}"
			self.load(name)
			self.load(name+'.len')
			self.add(EXEC)
		else:  # builtin
			#self.add(ITOA) # TODO FIXME cast
			self.add(BLTIN)
			self.instrs += x.callable.value.identifier.encode('ascii')+b'\0'
			self.add(CALL, nargs)

	#@dispatch
	def load_(self, x: ASTAttrgetNode):
		self.load(x.value)
		assert x.optype.special == '.' # TODO
		self.instrs.append(f"GETATTR	({x.attr})")

	@dispatch
	def load(self, x: ASTUnaryExprNode):
		self.load(x.value)
		self.add(self.unopmap[x.operator.operator])

	@dispatch
	def load(self, x: ASTBinaryExprNode):
		self.load(x.lvalue)
		self.load(x.rvalue)
		if (x.operator.operator == 'to'): raise NotImplementedError()
		else: self.add(self.binopmap[x.operator.operator])

	#@dispatch
	def load_(self, x: ASTItemgetNode):
		self.load(x.value)
		self.load(x.key)
		self.instrs.append("SUBSCR")

	@dispatch
	def load(self, x: str):
		self.add(SCPGET, self.scpcells[x])

	@dispatch
	def store(self, x: ASTIdentifierNode):
		self.store(x.identifier)

	@dispatch
	def store(self, x: str):
		self.add(SCPSET, self.scpcells[x])

class SBCCompiler(Compiler):
	ext = '.sbc'

	@classmethod
	def compile_ast(cls, ast, ns, *, filename):
		instrs = Instrs(name='<module>', ns=ns, filename=filename)
		instrs.add(ast)
		code = instrs.compile()
		return code

# by Sdore, 2019
