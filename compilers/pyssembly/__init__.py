#!/usr/bin/python3
# Slang Pyssembly compiler target

import pyssembly
from . import std
from .. import *
from ...ast import *
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
		'//': 'IDIV',
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

	_self_argdef = ASTArgdefNode(Class, ASTIdentifierNode('<self>', lineno=None, offset=None), None, None, lineno=None, offset=None)

	def _class_init(self, *args, **kwargs):
		getattr(self, '<init>')()
		getattr(self, f"<constructor ({', '.join(type(i).__name__ for i in (*args, *kwargs.values()))})>")(*args, **kwargs)
	_class_init = _class_init.__code__.replace(co_name='<new>')

	@init_defaults
	def __init__(self, *, name, ns, filename, argdefs=(), lastnodens: lambda: [None, None], firstlineno=0):
		self.name, self.ns, self.filename, self.lastnodens, self.firstlineno = name, ns, filename, lastnodens, firstlineno
		self.instrs = list()
		self.consts = list()
		self.argnames = list()
		for i in argdefs:
			if (i.modifier is not None): raise NotImplementedError("argument modifiers are not supported yet")
			self.argnames.append(i.name.identifier)
		self.cellvars = self.argnames.copy()
		self.srclnotab = list()
		self.lastln = self.firstlineno
		self._class_init = self._class_init.replace(co_filename=self.filename, co_consts=tuple(i.replace(co_filename=self.filename) if (isinstance(i, CodeType)) else i for i in self._class_init.co_consts))

	def compile(self):
		return pyssembly.Code('\n'.join(self.instrs), name=self.name, filename=self.filename.strip('"'), srclnotab=self.srclnotab, firstlineno=self.firstlineno, consts=self.consts, argnames=self.argnames)

	@dispatch
	def add(self, x: ASTRootNode):
		self.add(x.code)

	@dispatch
	def add(self, x: ASTCodeNode):
		for ii, i in enumerate(x.nodes):
			assert (i.lineno >= self.lastln)
			if (i.lineno != self.lastln): self.instrs.append(f"#line {i.lineno}")
			self.lastln = i.lineno
			self.lastnodens[0] = i
			self.add(i)

	@dispatch
	def add(self, x: ASTValueNode):
		self.add(x.value)

	@dispatch
	def add(self, x: ASTVardefNode):
		typesig = Signature.build(x.type, self.ns)
		if (x.value is not None):
			self.load(x.value)
			self.store(x.name)
		elif (isinstance(typesig, Class)):
			self.instrs += [
				"LOAD		(object)",
				"GETATTR	(__new__)",
			]
			self.load(x.type.type)
			self.instrs += [
				"CALL		1",
				"DUP",
				"GETATTR	<<init>>",
				"CALL",
				"POP",
			]
			self.store(x.name)

	@dispatch
	def add(self, x: ASTAssignmentNode):
		if (x.inplace_operator is not None): self.instrs.append(f"LOAD	({x.name})")
		self.load(x.value)
		if (x.inplace_operator is not None): self.instrs.append(f"IP{self.binopmap[x.inplace_operator.operator]}")
		if (x.isattr):
			self.instrs += [
				"LOAD		$<self>",
				f"SETATTR	({x.name})",
			]
		else: self.store(x.name)

	@dispatch
	def add(self, x: ASTUnpackAssignmentNode):
		assert (x.inplace_operator is None) # TODO
		self.load(x.value)
		self.instrs.append(f"UNPACK	{len(x.names)}")
		for name in x.names:
			self.store(name)

	@dispatch
	def add(self, x: ASTAttrsetNode):
		assert (x.assignment.isattr)
		if (x.assignment.inplace_operator is not None):
			self.load(x.value)
			self.instrs += [
				"DUP",
				"GETATTR	({x.assignment.name})",
			]
			self.load(x.assignment.value)
			self.instrs += [
				f"IP{self.binopmap[x.assignment.inplace_operator.operator]}",
				"ROT",
			]
		else:
			self.load(x.assignment.value)
			self.load(x.value)
		self.instrs.append(f"SETATTR	({x.assignment.name})")

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
		name = f"{x.name.identifier}({CallArguments(args=tuple(Signature.build(i, code_ns) for i in x.argdefs))})"
		self.lastnodens[1] = code_ns
		fname = f"{self.name}.<{x.__fsig__()}>"
		f_instrs = Instrs(name=fname, ns=code_ns, filename=self.filename, argdefs=x.argdefs, lastnodens=self.lastnodens, firstlineno=x.lineno)
		f_instrs.add(x.code)
		#dlog(f"{fname} instrs:\n"+'\n'.join(f_instrs.instrs)+'\n')
		self.consts.append(f_instrs.compile().to_code())
		self.lastnodens[1] = self.ns
		self.instrs += [
			f"LOAD		{len(self.consts)-1}",
			f"LOAD		('{fname}')",
			"MKFUNC		0", # TODO: flags
		]
		self.store(name)

	@dispatch
	def add(self, x: ASTClassdefNode):
		code_ns = self.ns.derive(x.name.identifier)
		name = x.name.identifier
		self.lastnodens[1] = code_ns
		cname = str(name)
		c_instrs = Instrs(name=cname, ns=code_ns, filename=self.filename, lastnodens=self.lastnodens, firstlineno=x.lineno)
		c_instrs.consts.append(self._class_init)
		c_instrs.instrs += [
			f"LOAD		{len(self.consts)-1}",
			f"LOAD		('<new>')",
			"MKFUNC		0", # TODO: flags
		]
		c_instrs.store('__init__')
		c_instrs.add(x.code)
		self.consts.append(c_instrs.compile().to_code())
		self.lastnodens[1] = self.ns
		self.instrs += [
			"LOAD_BUILD_CLASS",
			f"LOAD		{len(self.consts)-1}",
			f"LOAD		('{cname}')",
			"MKFUNC		0", # TODO: flags?
			f"LOAD		('{cname}')",
			"CALL		2",
		]
		self.store(name)

	@dispatch
	def add(self, x: ASTKeywordExprNode):
		if (x.keyword.keyword == 'import'):
			m = re.fullmatch(r'(?:(?:(\w+):)?(?:([\w./]+)/)?([\w.]+):)?([\w*]+)', x.value.identifier)
			assert (m is not None)
			namespace, path, pkg, name = m.groups()
			if (namespace is None): namespace = 'sl'
			if (path is None): path = '.'
			if (pkg is None): pkg = name
			if (namespace == 'py'):
				assert (path == '.')
				self.instrs += [
					"LOAD		(0)", # TODO
					"LOAD		(())", # TODO
					f"IMPORT	({pkg})",
				]
				if (name == '*'): self.instrs.append("IMPALL")
				else:
					if (name != pkg): self.instrs.append("IMPFROM")
					self.store(name)
			elif (namespace == 'sl'):
				pkg = pkg.replace('.', '/')
				filename = f"{os.path.join(path, pkg)}.sl"
				src = open(filename, 'r').read()
				tl = parse_string(src)
				ast = build_ast(tl, filename)
				optimize_ast(ast, validate_ast(ast))
				instrs = Instrs(name='<module>', ns=validate_ast(ast), filename=filename)
				instrs.add(ast)
				code = instrs.compile().to_code()
				# TODO
			else: raise WTFException(namespace)
		elif (x.keyword.keyword == 'return'):
			self.load(x.value)
			self.instrs.append("RET")
		elif (x.keyword.keyword == 'delete'):
			self.delete(x.value)
		elif (x.keyword.keyword == 'break'):
			self.instrs.append("JF :end")
		else: raise NotImplementedError(x.keyword)

	@dispatch
	def add(self, x: ASTKeywordDefNode):
		name = x.name.identifier
		if (x.keyword.keyword == 'main'):
			code_ns = self.ns.derive(name)
			self.lastnodens[1] = code_ns
			f_instrs = Instrs(name=name, ns=code_ns, filename=self.filename, lastnodens=self.lastnodens, firstlineno=x.lineno)
			f_instrs.add(x.code)
			#dlog(f"{name} instrs:\n"+'\n'.join(f_instrs.instrs)+'\n')
			self.consts.append(f_instrs.compile().to_code())
			self.lastnodens[1] = self.ns
			self.instrs += [
				"LOAD		(__name__)",
				"LOAD		('__main__')",
				"CMP		(==)",
				"JFP		:nomain",
				f"LOAD		{len(self.consts)-1}",
				f"LOAD		('{name}')",
				"MKFUNC		0",
				"CALL		0",
				"POP",
				":nomain",
			]
		elif (x.keyword.keyword == 'init'):
			code_ns = self.ns.derive(name)
			self.lastnodens[1] = code_ns
			f_instrs = Instrs(name=name, argdefs=(self._self_argdef,), ns=code_ns, filename=self.filename, lastnodens=self.lastnodens, firstlineno=x.lineno)
			f_instrs.add(x.code)
			#dlog(f"{name} instrs:\n"+'\n'.join(f_instrs.instrs)+'\n')
			self.consts.append(f_instrs.compile().to_code())
			self.lastnodens[1] = self.ns
			self.instrs += [
				f"LOAD		{len(self.consts)-1}",
				f"LOAD		('{name}')",
				"MKFUNC		0",
			]
			self.store(name)
		elif (x.keyword.keyword == 'constr'):
			code_ns = self.ns.derive(name)
			self.ns.define(x, redefine=True)
			self.lastnodens[1] = code_ns
			name = f"<constructor ({S(', ').join(i.type for i in x.argdefs)})>"
			f_instrs = Instrs(name=name, ns=code_ns, filename=self.filename, argdefs=(self._self_argdef, *x.argdefs), lastnodens=self.lastnodens, firstlineno=x.lineno)
			f_instrs.add(x.code)
			#dlog(f"{name} instrs:\n"+'\n'.join(f_instrs.instrs)+'\n')
			self.consts.append(f_instrs.compile().to_code())
			self.lastnodens[1] = self.ns
			self.instrs += [
				f"LOAD		{len(self.consts)-1}",
				f"LOAD		('{name}')",
				"MKFUNC		0", # TODO: flags
			]
			self.store(name)
		else: raise NotImplementedError(x.keyword)

	@dispatch
	def add(self, x: ASTConditionalNode):
		self.load(x.condition)
		self.instrs.append("JFP	:else")
		self.add(x.code)
		self.instrs += [
			"JF	:end",
			":else",
			":end",
		]

	@dispatch
	def add(self, x: ASTForLoopNode):
		self.load(x.iterable)
		#self.cellvars.append(x.name.identifier) # TODO FIXME
		self.instrs += [
			"ITER",
			":for",
			"FOR	:else",
		]
		self.store(x.name)
		self.add(x.code) # TODO: stack effect (py38)
		self.instrs += [
			"JA	:for",
			":else",
			":end",
		]

	@dispatch
	def add(self, x: ASTWhileLoopNode):
		self.instrs += [
			":while",
		]
		self.load(x.condition)
		self.instrs.append("JFP	:else")
		self.add(x.code) # TODO: stack effect (py38)
		self.instrs += [
			"JA	:while",
			":else",
			":end",
		]

	@dispatch
	def add(self, x: ASTElseClauseNode):
		ii = -1 - self.instrs[-1].startswith('#line')
		assert (self.instrs.pop(ii) == ":end")
		self.add(x.code) # TODO: stack effect (py38)
		self.instrs.append(":end")

	@dispatch
	def load(self, x: ASTLiteralNode):
		self.instrs.append(f"LOAD	({x.literal})")

	@dispatch
	def load(self, x: ASTIdentifierNode):
		self.load(x.identifier)

	@dispatch
	def load(self, x: ASTListNode):
		for i in x.values:
			self.load(i)
		self.instrs.append(f"BUILD_LIST	{len(x.values)}")

	@dispatch
	def load(self, x: ASTTupleNode):
		for i in x.values:
			self.load(i)
		self.instrs.append(f"BUILD_TUPLE	{len(x.values)}")

	@dispatch
	def load(self, x: ASTValueNode):
		self.load(x.value)

	@dispatch
	def load(self, x: ASTFunccallNode):
		if (isinstance(x.callable, ASTValueNode) and isinstance(x.callable.value, ASTIdentifierNode) and x.callable.value.identifier in self.ns.signatures and not isinstance(self.ns.signatures[x.callable.value.identifier], Class)):
			self.load(f"{x.callable.value.identifier}({CallArguments.build(x, self.ns)})")
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
		assert (x.optype.special == '.') # TODO
		self.instrs.append(f"GETATTR	({x.attr})")

	@dispatch
	def load(self, x: ASTUnaryExprNode):
		self.load(x.value)
		self.instrs.append(self.unopmap[x.operator.operator])

	@dispatch
	def load(self, x: ASTBinaryExprNode):
		self.load(x.lvalue)
		char = isinstance(Signature.build(x.lvalue, self.ns), stdlib.char)
		if (char): self.instrs.append("CALL	(ord)	1")
		if (x.operator.operator == 'xor'): self.instrs.append("BOOL")
		self.load(x.rvalue)
		if (char and isinstance(Signature.build(x.rvalue, self.ns), stdlib.char)): self.instrs.append("CALL	(ord)	1")
		if (x.operator.operator == 'xor'): self.instrs.append("BOOL")
		if (x.operator.operator == 'to'): self.instrs.append("CALL	(range)	2")
		else: self.instrs.append(f"CMP	({x.operator.operator})" if (x.operator.operator in dis.cmp_op) else self.binopmap[x.operator.operator])
		if (x.operator.operator == 'xor'): self.instrs.append("BOOL")
		if (char and x.operator.operator not in logical_operators): self.instrs.append("CALL	(chr)	1")

	@dispatch
	def load(self, x: ASTItemgetNode):
		self.load(x.value)
		self.load(x.key)
		self.instrs.append("SUBSCR")

	@dispatch
	def load(self, x: str):
		self.instrs.append(f"LOAD	{f'${x}' if (x in self.cellvars) else f'<{x}>'}")

	@dispatch
	def load(self, x):
		self.instrs.append(f"LOAD_CONST	({repr(x)})")

	@dispatch
	def store(self, x: ASTIdentifierNode):
		self.store(x.identifier)

	@dispatch
	def store(self, x: str):
		self.instrs.append(f"STORE	{f'${x}' if (x in self.cellvars) else f'<{x}>'}")

	@dispatch
	def delete(self, x: ASTIdentifierNode):
		self.delete(x.identifier)

	@dispatch
	def delete(self, x: str):
		self.instrs.append(f"DELETE	{f'${x}' if (x in self.cellvars) else f'<{x}>'}")

class PyssemblyCompiler(Compiler):
	ext = '.pyc'

	@classmethod
	def compile_ast(cls, ast, ns, *, filename):
		instrs = Instrs(name='<module>', ns=ns, filename=filename)

		instrs.consts.append(compile(open(std.__file__).read(), '<std>', 'exec'))
		instrs.instrs += [
			f"LOAD	{len(instrs.consts)-1}",
			"LOAD	('<std>')",
			"MKFUNC	0", # TODO?
			"CALL",
		]

		try: instrs.add(ast)
		except Exception as ex: raise SlCompilationError('Compilation error', instrs.lastnodens[0], scope=instrs.lastnodens[1].scope) from ex

		#dlog("Instrs:\n"+'\n'.join(instrs.instrs)+'\n')

		try:
			code = instrs.compile().to_code()
			#dis.show_code(code); dis.dis(code); print()
			code = pyssembly.asm(code)
		except pyssembly.PyssemblyError as ex:
			print('Error:', ex)
			try: code = ex.code.to_code()
			except pyssembly.PyssemblyError: pass
			else:
				print("\nHere is full pyssembly code 'til the errorneous line:\n")
				dis.dis(code)
			raise SlCompilationError('Pyssembly error', ast, scope=instrs.ns) from ex

		return code

# by Sdore, 2020
