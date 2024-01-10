#!/usr/bin/python3
# Slang Native (ASM) x86_64 compiler target

from . import *

word_size = 8
registers = ('rax', 'rcx', 'rdx', 'rbx', 'rsi', 'rdi', 'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')
regs64 = {i: () for i in registers}
regs32 = {'e'+i: ('r'+i, *regs64['r'+i]) for i in ('ax', 'cx', 'dx', 'bx', 'si', 'di')}
regs16 = {i: ('e'+i, *regs32['e'+i]) for i in ('ax', 'cx', 'dx', 'bx', 'si', 'di')}
regs8 = {i+j: (i+'x', *regs16[i+'x']) for i in 'acdb' for j in 'lh'}

class Instrs:
	binopmap = {
		'+': 'add',
	}
	stacksize = 0x10 # TODO

	@init_defaults
	def __init__(self, *, name, ns, filename, nargs: int, freeregs: set):
		self.name, self.ns, self.filename, self.nargs, self.freeregs = name, ns, filename, nargs, freeregs
		self.instrs = list()
		self.varoff = bidict.OrderedBidict()
		self.varsize = dict()
		self.regpool = list(registers)
		self.clobbered = set()

	def compile(self):
		saveregs = tuple(sorted(self.clobbered - self.freeregs))
		instrs = [
			"push	rbp",
			"mov	rbp, rsp",
			*(f"push {i}" for i in saveregs),
			f"sub	rsp, {self.stacksize}",
			'\n',
			*self.instrs,
			'\n',
			*(f"pop {i}" for i in saveregs[::-1]),
			"leave",
			f"ret	{self.nargs}" if (self.nargs > 0) else "ret",
		]
		return f"global {self.name}\n{self.name}:\n\t"+'\n\t'.join('\t'.join(i.split(maxsplit=1)) for i in instrs)+'\n'

	def var(self, name):
		if (self.varoff[name] == 0): return '[rbp]'
		return "[rbp%+d]" % -self.varoff[name]

	@contextlib.contextmanager
	def vars(self, *names):
		yield tuple(map(self.var, names))

	@contextlib.contextmanager
	def regs(self, n):
		regs = {self.regpool.pop(0) for _ in range(n)}
		self.clobbered |= regs
		try: yield regs
		finally: self.regpool = [i for i in registers if i in {*self.regpool, *regs}]

	#def syscall(self, rax, rdi=None, rsi=None, rdx=None, r10=None, r8=None, r9=None):
	#	self.instrs.append("

	@dispatch
	def add(self, x: ASTRootNode):
		self.add(x.code)

	@dispatch
	def add(self, x: ASTCodeNode):
		for i in x.nodes:
			self.add(i)

	@dispatch
	def add(self, x: ASTVardefNode):
		name = x.name.identifier
		try:
			ln, lo = last(self.varoff.items())
			self.varoff[name] = lo+self.varsize[ln]
		except StopIteration: self.varoff[name] = word_size
		self.varsize[name] = self.sizeof(x.type)
		if (x.value is not None): self.set(x.name, x.value)

	@dispatch
	def add(self, x: ASTFunccallNode):
		callarguments = CallArguments.build(x, self.ns)
		fsig = Signature.build(x.callable, self.ns)
		fcall = fsig.compatible_call(callarguments, self.ns)
		if (fcall is None): raise TODO(fcall)

		n = int()
		if (fcall[0] is not None): fname = f"{fsig.name}({CallArguments(args=fcall[0], ns=self.ns)})"
		else:
			if (isinstance(x.callable.value, ASTAttrgetNode)):
				ofsig = Signature.build(x.callable.value.value, self.ns)
				if (isinstance(fsig, stdlib.Builtin)):
					fname = x.callable
				else: raise NotImplementedError(ofsig)
			else: raise NotImplementedError(x.callable.value)

		for i in x.callargs.callargs:
			self.push(i)
			n += 1

		if (x.callargs.starargs or x.callkwargs.callkwargs or x.callkwargs.starkwargs): raise NotImplementedError()

		self.instrs.append(f"call {fname}")

	@dispatch
	def load(self, x: ASTValueNode, *reg):
		return self.load(x.value, *reg)

	@dispatch
	def load(self, x: ASTLiteralNode):
		return x.literal

	@dispatch
	def load(self, x):
		with self.regs(1) as (reg,):
			self.load(x, reg)
			return reg
		#reg = self.regpool.pop(0)
		#self.clobbered.add(reg)
		#self.load(x, reg)
		#return reg

	@dispatch
	def load(self, x: ASTIdentifierNode, reg):
		self.instrs.append(f"mov {reg}, {self.var(x.identifier)}")

	@dispatch
	def load(self, x: ASTBinaryExprNode, reg):
		self.load(x.lvalue, reg)
		self.instrs.append(f"{self.binopmap[x.operator.operator]} {reg}, {self.load(x.rvalue)}")

	@dispatch
	def load(self, x: str, reg):
		self.instrs.append(f"mov {reg}, {x}")

	@dispatch
	def set(self, name: ASTIdentifierNode, value):
		self.set(name.identifier, value)

	@dispatch
	def set(self, name: str, value: ASTValueNode):
		self.set(name, value.value)

	@dispatch
	def set(self, name: str, value: ASTLiteralNode):
		self.set(name, self.load(value))

	@dispatch
	def set(self, name: str, value):
		with self.vars(name) as (var,):
			self.instrs.append(f"mov {var}, {self.load(value)}")

	def push(self, x):
		self.instrs.append(f"push {self.load(x)}")

	@dispatch
	def sizeof(self, x: ASTTypedefNode):
		return self.sizeof(Signature.build(x, self.ns))

	@dispatch
	def sizeof(self, x: lambda x: hasattr(x, 'fmt')):
		return struct.calcsize(x.fmt)

class BuiltinInstrs(Instrs):
	@init_defaults
	def __init__(self, *, freeregs: set):
		self.freeregs = freeregs

@singleton
class builtin_stdio_println(BuiltinInstrs):
	name = 'stdio.println'
	instrs = [
		"mov	al, [rbp+0x10]",
		"add	al, '0'",
		"mov	[rbp-2], al",
		"mov	al, 10",
		"mov	[rbp-1], al",

		"mov	rax, 1		; sys_write",
		"mov	rdi, 1		; stdout",
		"lea	rsi, [rbp-2]	; buf",
		"mov	rdx, 2		; count",
		"syscall",
	]
	nargs = 1
	stacksize = 2
	clobbered = {'rax', 'rcx', 'rdx', 'rdi', 'rsi', 'r11'}

class x86_64Compiler(NativeCompiler):
	ext = '.o'

	header = """
		section .text

		global _start
		_start:
			call	main
			mov	rax, 60	; sys_exit
			mov	rdi, 0	; error_code
			syscall
			hlt
	"""

	@classmethod
	def compile_ast(cls, ast, ns, *, filename):
		instrs = Instrs(name='main', ns=ns, filename=filename)
		instrs.add(ast)
		src = f"# {filename}\n{S(cls.header).unindent().strip()}\n"
		src += '\n'+builtin_stdio_println.compile()
		src += '\n'+instrs.compile()

		sname = os.path.splitext(filename)[0]+'.s'
		sfd = open(sname, 'w')
		try:
			sfd.write(src)
			sfd.close()
			log("Src:\n"+src)

			ofd, oname = tempfile.mkstemp(prefix=f"slc-{os.path.splitext(filename)[0]}-", suffix='.o')
			try:
				subprocess.run(('yasm', '-felf64', '-o', oname, sname), stderr=subprocess.PIPE, text=True, check=True)
				return os.fdopen(ofd, 'rb').read()
			except subprocess.CalledProcessError as ex: raise SlCompilationError('\n'+S(ex.stderr).indent(), ast, scope=instrs.ns) from ex
			finally:
				try: os.remove(oname)
				except OSError: pass
		finally:
			sfd.close()
			try: os.remove(sname)
			except OSError: pass

compiler = x86_64Compiler

# by Sdore, 2021
