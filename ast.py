#!/usr/bin/python3
# Slang AST

import abc
from .tokens import *
from utils import *

DEBUG_PRECEDENCE = False

def warn(class_, msg, node, ns):
	if (ns.warnclasses[class_] == False): return
	logexception(Warning(f"{msg} \033[8m({class_})\033[0m"), raw=True)

def literal_type(x):
	r = eval(str(x))
	if (isinstance(r, str) and len(r) == 1 and re.match(r"'.+?'", x.strip())): return stdlib.char
	return type(r)

def common_type(l, ns): # TODO
	r = set()
	for i in l: r.add(Signature.build(i, ns))
	if (not r): return None
	if (len(r) > 1): raise TODO(r)
	return next(iter(r))

class ASTNode(abc.ABC):
	__slots__ = ('lineno', 'offset', 'flags')

	@abc.abstractmethod
	@init_defaults
	def __init__(self, *, lineno, offset, flags: paramset):
		self.lineno, self.offset, self.flags = lineno, offset, flags

	def __repr__(self):
		return f"<{self.typename} '{self.__str__()}' on line {self.lineno}, offset {self.offset}>"

	@abc.abstractmethod
	def __str__(self):
		pass

	@abc.abstractclassmethod
	def build(cls, tl):
		if (not tl): raise SlSyntaxNoToken()

	def validate(self, ns):
		for i in self.__slots__:
			v = getattr(self, i)
			if (isiterable(v) and not isinstance(v, str)):
				for jj, j in enumerate(v):
					if (hasattr(j, 'validate')):
						j.validate(ns)
			elif (hasattr(v, 'validate') and i != 'code'):
				v.validate(ns)

	def optimize(self, ns):
		for i in self.__slots__:
			v = getattr(self, i)
			if (isiterable(v) and not isinstance(v, str)):
				for jj, j in enumerate(v.copy()):
					if (hasattr(j, 'optimize')):
						r = j.optimize(ns)
						if (r is not None): v[jj] = r
						if (v[jj].flags.optimized_out): del v[jj]
			elif (hasattr(v, 'optimize') and i != 'code'):
				r = v.optimize(ns)
				if (r is not None): setattr(self, i, r)
				if (getattr(self, i).flags.optimized_out): setattr(self, i, None)

	@classproperty
	def typename(cls):
		return cls.__name__[3:-4]

	@property
	def length(self):
		return sum(getattr(self, i).length for i in self.__slots__ if hasattr(getattr(self, i), 'length'))

class ASTRootNode(ASTNode):
	__slots__ = ('code',)

	def __init__(self, code, **kwargs):
		super().__init__(lineno=None, offset=None, **kwargs)
		self.code = code

	def __repr__(self):
		return '<Root>'

	def __str__(self):
		return '<Root>'

	@classmethod
	def build(cls, name=None):
		return cls((yield from ASTCodeNode.build(name)))

class ASTCodeNode(ASTNode):
	__slots__ = ('nodes', 'name')

	def __init__(self, nodes, *, name='<code>', **kwargs):
		super().__init__(lineno=None, offset=None, **kwargs)
		self.nodes, self.name = nodes, name

	def __repr__(self):
		return (S('\n').join(self.nodes).indent().join('\n\n') if (self.nodes) else '').join('{}')

	def __str__(self):
		return f"""<Code{f" '{self.name}'" if (self.name and self.name != '<code>') else ''}>"""

	@classmethod
	def build(cls, name):
		yield name
		code = cls([], name=name)
		while (True):
			c = yield
			if (c is None): break
			code.nodes.append(c)
		return code

	def validate(self, ns=None):
		if (ns is None): ns = Namespace(self.name)
		for i in self.nodes:
			i.validate(ns)
		return ns

	def optimize(self, ns):
		for ii, i in enumerate(self.nodes):
			r = i.optimize(ns)
			if (r is not None): self.nodes[ii] = r
			if (self.nodes[ii].flags.optimized_out): del self.nodes[ii]

class ASTTokenNode(ASTNode):
	@abc.abstractclassmethod
	def build(cls, tl):
		super().build(tl)
		off = int()
		for ii, i in enumerate(tl.copy()):
			if (i.typename == 'SPECIAL' and (i.token[0] == '#' or i.token == '\\\n')): del tl[ii-off]; off += 1
		if (not tl): raise SlSyntaxEmpty()

	@property
	def length(self):
		return sum(len(getattr(self, i)) for i in self.__slots__)

class ASTIdentifierNode(ASTTokenNode):
	__slots__ = ('identifier',)

	def __init__(self, identifier, **kwargs):
		super().__init__(**kwargs)
		self.identifier = identifier

	def __str__(self):
		return str(self.identifier)

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if (tl[0].typename != 'IDENTIFIER'): raise SlSyntaxExpectedError('IDENTIFIER', tl[0])
		identifier = tl.pop(0).token

		return cls(identifier, lineno=lineno, offset=offset)

class ASTKeywordNode(ASTTokenNode):
	__slots__ = ('keyword',)

	def __init__(self, keyword, **kwargs):
		super().__init__(**kwargs)
		self.keyword = keyword

	def __str__(self):
		return str(self.keyword)

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if (tl[0].typename != 'KEYWORD'): raise SlSyntaxExpectedError('KEYWORD', tl[0])
		keyword = tl.pop(0).token

		return cls(keyword, lineno=lineno, offset=offset)

class ASTLiteralNode(ASTTokenNode):
	__slots__ = ('literal',)

	def __init__(self, literal, **kwargs):
		super().__init__(**kwargs)
		self.literal = literal

	def __str__(self):
		return str(self.literal)

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if (tl[0].typename != 'LITERAL'): raise SlSyntaxExpectedError('LITERAL', tl[0])
		literal = tl.pop(0).token

		return cls(literal, lineno=lineno, offset=offset)

class ASTOperatorNode(ASTTokenNode):
	__slots__ = ('operator',)

	def __init__(self, operator, **kwargs):
		super().__init__(**kwargs)
		self.operator = operator

	def __str__(self):
		return str(self.operator)

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if (tl[0].typename != 'OPERATOR'): raise SlSyntaxExpectedError('OPERATOR', tl[0])
		operator = tl.pop(0).token

		return cls(operator, lineno=lineno, offset=offset)

class ASTSpecialNode(ASTTokenNode):
	__slots__ = ('special',)

	def __init__(self, special, **kwargs):
		super().__init__(**kwargs)
		self.special = special

	def __str__(self):
		return str(self.special)

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if (tl[0].typename != 'SPECIAL'): raise SlSyntaxExpectedError('SPECIAL', tl[0])
		special = tl.pop(0).token
		if (special == '\\'): raise SlSyntaxEmpty()

		return cls(special, lineno=lineno, offset=offset)

class ASTPrimitiveNode(ASTNode): pass

class ASTValueNode(ASTPrimitiveNode):
	__slots__ = ('value',)

	def __init__(self, value, **kwargs):
		super().__init__(**kwargs)
		self.value = value

	def __str__(self):
		return str(self.value)

	@classmethod
	def build(cls, tl, *, fcall=False):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		types = [ASTLiteralNode, ASTFunccallNode, ASTAttrgetNode, ASTItemgetNode, ASTIdentifierNode, ASTLambdaNode]
		if (fcall): types.remove(ASTFunccallNode); types.remove(ASTLambdaNode)
		if (tl[0].typename == 'LITERAL'): value = ASTLiteralNode.build(tl)
		else:
			for i in types:
				tll = tl.copy()
				try: value = i.build(tll)
				except SlSyntaxException: continue
				else: tl[:] = tll; break
			else: raise SlSyntaxExpectedError('Value', tl[0])

		return cls(value, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		if (isinstance(self.value, ASTIdentifierNode)):
			if (self.value.identifier not in ns): raise SlValidationNotDefinedError(self.value, scope=ns.scope)
			if (self.value.identifier not in ns.values): warn('uninitialized', f"using value of possibly uninitialized variable '{self.value}'", self, ns)

	def optimize(self, ns):
		super().optimize(ns)
		if (isinstance(self.value, ASTIdentifierNode) and self.value in ns.values): self.value = ASTLiteralNode(repr(ns.values[self.value]), lineno=self.lineno, offset=self.offset) # TODO FIXME in functions

class ASTItemgetNode(ASTPrimitiveNode):
	__slots__ = ('value', 'key')

	def __init__(self, value, key, **kwargs):
		super().__init__(**kwargs)
		self.value, self.key = value, key

	def __str__(self):
		return f"{self.value}[{self.key}]"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		value = ASTIdentifierNode.build(tl) # TODO: value/expr
		bracket = ASTSpecialNode.build(tl)
		if (bracket.special != '['): raise SlSyntaxExpectedError("'['", bracket)
		key = ASTExprNode.build(tl)
		bracket = ASTSpecialNode.build(tl)
		if (bracket.special != ']'): raise SlSyntaxExpectedError("']'", bracket)

		return cls(value, key, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		valsig = Signature.build(self.value, ns)
		keysig = Signature.build(self.key, ns)
		if (keysig not in valsig.itemget): raise SlValidationError(f"'{valsig}' does not support itemget by key of type '{keysig}'", self, scope=ns.scope)

class ASTAttrgetNode(ASTPrimitiveNode):
	__slots__ = ('value', 'optype', 'attr')

	def __init__(self, value, optype, attr, **kwargs):
		super().__init__(**kwargs)
		self.value, self.optype, self.attr = value, optype, attr

	def __str__(self):
		return f"{self.value}{self.optype}{self.attr}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		value = ASTIdentifierNode.build(tl)
		optype = ASTSpecialNode.build(tl)
		if (optype.special not in attrops): raise SlSyntaxExpectedError(f"one of {attrops}", optype)
		attr = ASTIdentifierNode.build(tl)

		return cls(value, optype, attr, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		if (self.optype not in Signature.build(self.value, ns).attrops): raise SlValidationError(f"'{self.value}' does not support attribute operation '{self.optype}'", self, scope=ns.scope)

class ASTExprNode(ASTPrimitiveNode):
	@classmethod
	def build(cls, tl, *, fcall=False):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		for ii, p in enumerate(operators[::-1]):
			for i in p:
				tll = tl.copy()
				try: value = ASTBinaryExprNode.build(tll, i)
				except SlSyntaxException: continue
				else: tl[:] = tll; return value

		tll = tl.copy()
		try: value = ASTUnaryExprNode.build(tll)
		except SlSyntaxException: pass
		else: tl[:] = tll; return value

		tll = tl.copy()
		try: value = ASTValueNode.build(tll, fcall=fcall)
		except SlSyntaxException: pass
		else: tl[:] = tll; return value

		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != '('): raise SlSyntaxExpectedError('Expr', parenthesis)
		parenthesized = list()
		lvl = 1
		while (tl):
			if (tl[0].typename == 'SPECIAL'): lvl += 1 if (tl[0].token == '(') else -1 if (tl[0].token == ')') else 0
			if (lvl == 0):
				parenthesis = ASTSpecialNode.build(tl)
				if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
				break
			assert lvl > 0
			parenthesized.append(tl.pop(0))
		value = ASTExprNode.build(parenthesized)
		if (parenthesized): raise SlSyntaxExpectedNothingError(parenthesized[0])
		return value

class ASTUnaryExprNode(ASTExprNode):
	__slots__ = ('operator', 'value')

	def __init__(self, operator, value, **kwargs):
		super(ASTPrimitiveNode, self).__init__(**kwargs)
		self.operator, self.value = operator, value

	def __str__(self):
		return f"{self.operator}{' ' if (self.operator.operator.isalpha()) else ''}{str(self.value).join('()') if (DEBUG_PRECEDENCE or isinstance(self.value, ASTBinaryExprNode) and operator_precedence(self.value.operator.operator) >= operator_precedence(self.operator.operator)) else self.value}"

	@classmethod
	def build(cls, tl):
		ASTPrimitiveNode.build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		operator = ASTOperatorNode.build(tl)
		if (operator.operator in bothoperators): operator.operator = UnaryOperator(operator.operator)
		elif (not isinstance(operator.operator, UnaryOperator)): raise SlSyntaxExpectedError('UnaryOperator', operator)
		value = ASTExprNode.build(tl)

		return cls(operator, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		sig = Signature.build(self.value, ns)
		op = self.operator.operator
		if (op not in sig.operators): raise SlValidationError(f"'{sig}' does not support unary operator '{op}'", self, scope=ns.scope)

	def optimize(self, ns):
		super().optimize(ns)
		sig = Signature.build(self.value, ns)
		if (self.value in ns.values): return ASTValueNode(ASTLiteralNode(eval(f"{self.operator} {ns.values[self.value]}"), lineno=self.lineno, offset=self.offset), lineno=self.lineno, offset=self.offset)

class ASTBinaryExprNode(ASTExprNode):
	__slots__ = ('lvalue', 'operator', 'rvalue')

	def __init__(self, lvalue, operator, rvalue, **kwargs):
		super(ASTPrimitiveNode, self).__init__(**kwargs)
		self.lvalue, self.operator, self.rvalue = lvalue, operator, rvalue

	def __str__(self):
		return f"{str(self.lvalue).join('()') if (DEBUG_PRECEDENCE or isinstance(self.lvalue, ASTBinaryExprNode) and operator_precedence(self.lvalue.operator.operator) > operator_precedence(self.operator.operator)) else self.lvalue}{str(self.operator).join('  ') if (operator_precedence(self.operator.operator) > 0) else self.operator}{str(self.rvalue).join('()') if (DEBUG_PRECEDENCE or isinstance(self.rvalue, ASTBinaryExprNode) and operator_precedence(self.rvalue.operator.operator) > operator_precedence(self.operator.operator)) else self.rvalue}"

	@classmethod
	def build(cls, tl, op):
		ASTPrimitiveNode.build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		lasti = None
		lvl = int()
		for ii, i in enumerate(tl):
			if (i.typename == 'SPECIAL'): lvl += 1 if (i.token == '(') else -1 if (i.token == ')') else 0
			if (lvl > 0): continue
			if (i.typename == 'OPERATOR' and isinstance(i.token, BinaryOperator) and i.token == op): lasti = ii
		if (lasti is None): raise SlSyntaxExpectedError('BinaryOperator', tl[0])
		tll, tl[:] = tl[:lasti], tl[lasti:]
		lvalue = ASTExprNode.build(tll)
		if (tll): raise SlSyntaxExpectedNothingError(tll[0])
		operator = ASTOperatorNode.build(tl)
		rvalue = ASTExprNode.build(tl)

		return cls(lvalue, operator, rvalue, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		lsig = Signature.build(self.lvalue, ns)
		rsig = Signature.build(self.rvalue, ns)
		op = self.operator.operator
		if ((op, rsig) not in lsig.operators): raise SlValidationError(f"'{lsig}' does not support operator '{op}' with operand of type '{rsig}'", self, scope=ns.scope)

	def optimize(self, ns):
		super().optimize(ns)
		if (self.operator.operator == '**' and self.lvalue in ns.values and ns.values[self.lvalue] == 2): self.operator.operator, self.lvalue.value, ns.values[self.lvalue] = BinaryOperator('<<'), ASTLiteralNode('1', lineno=self.lvalue.value.lineno, offset=self.lvalue.value.offset), 1
		if (self.lvalue in ns.values and self.rvalue in ns.values and self.operator.operator != 'to'): return ASTValueNode(ASTLiteralNode(repr(eval(str(self))), lineno=self.lineno, offset=self.offset), lineno=self.lineno, offset=self.offset)

class ASTNonFinalNode(ASTNode): pass

class ASTTypedefNode(ASTNonFinalNode):
	__slots__ = ('modifiers', 'type')

	def __init__(self, modifiers, type, **kwargs):
		super().__init__(**kwargs)
		self.modifiers, self.type = modifiers, type

	def __str__(self):
		return f"{S(' ').join(self.modifiers)}{' ' if (self.modifiers and self.type) else ''}{self.type or ''}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		modifiers = list()
		while (tl and tl[0].typename == 'KEYWORD'):
			if (not isinstance(tl[0].token, Modifier)): raise SlSyntaxExpectedError('Modifier', tl[0])
			modifiers.append(ASTKeywordNode.build(tl))
		type = ASTIdentifierNode.build(tl)

		return cls(modifiers, type, lineno=lineno, offset=offset)

class ASTArgdefNode(ASTNonFinalNode):
	__slots__ = ('type', 'name', 'modifier', 'value')

	def __init__(self, type, name, modifier, value, **kwargs):
		super().__init__(**kwargs)
		self.type, self.name, self.modifier, self.value = type, name, modifier, value

	def __str__(self):
		return f"{f'{self.type} ' if (self.type) else ''}{self.name}{self.modifier or ''}{f'={self.value}' if (self.value is not None) else ''}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		type = ASTTypedefNode.build(tl)
		name = ASTIdentifierNode.build(tl)
		modifier = ASTOperatorNode.build(tl) if (tl and tl[0].typename == 'OPERATOR' and tl[0].token in '+**') else ASTSpecialNode.build(tl) if (tl and tl[0].typename == 'SPECIAL' and tl[0].token in '?=') else None
		value = ASTValueNode.build(tl) if (modifier == '=') else None

		return cls(type, name, modifier, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		if (isinstance(Signature.build(self.type, ns), stdlib.void)): raise SlValidationError(f"Argument cannot have type '{self.type}'", self, scope=ns.scope)

class ASTCallargsNode(ASTNonFinalNode):
	__slots__ = ('callargs', 'starargs')

	def __init__(self, callargs, starargs, **kwargs):
		super().__init__(**kwargs)
		self.callargs, self.starargs = callargs, starargs

	def __str__(self):
		return S(', ').join((*self.callargs, *(f'*{i}' for i in self.starargs)))

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		callargs = list()
		starargs = list()
		if (tl and not (tl[0].typename == 'SPECIAL' and tl[0].token == ')')):
			while (tl):
				if (tl[0].typename == 'OPERATOR' and tl[0].token == '*'):
					ASTOperatorNode.build(tl)
					starargs.append(ASTExprNode.build(tl))
				elif (len(tl) >= 2 and tl[1].typename == 'SPECIAL' and tl[1].token == '='): break
				else: callargs.append(ASTExprNode.build(tl))
				if (not tl or tl[0].typename != 'SPECIAL' or tl[0].token == ')'): break
				comma = ASTSpecialNode.build(tl)
				if (comma.special != ','): raise SlSyntaxExpectedError("','", comma)

		return cls(callargs, starargs, lineno=lineno, offset=offset)

class ASTCallkwargsNode(ASTNonFinalNode):
	__slots__ = ('callkwargs', 'starkwargs')

	def __init__(self, callkwargs, starkwargs, **kwargs):
		super().__init__(**kwargs)
		self.callkwargs, self.starkwargs = callkwargs, starkwargs

	def __str__(self):
		return S(', ').join((*(f'{k}={v}' for k, v in self.callkwargs), *(f'**{i}' for i in self.starkwargs)))

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		callkwargs = list()
		starkwargs = list()
		if (tl and not (tl[0].typename == 'SPECIAL' and tl[0].token == ')')):
			while (tl):
				if (tl[0].typename == 'OPERATOR' and tl[0].token == '**'):
					ASTOperatorNode.build(tl)
					starkwargs.append(ASTExprNode.build(tl))
				else:
					key = ASTIdentifierNode.build(tl)
					eq = ASTSpecialNode.build(tl)
					if (eq.special != '='): raise SlSyntaxExpectedError("'='", eq)
					value = ASTExprNode.build(tl)
					callkwargs.append((key, value))
				if (not tl or tl[0].typename != 'SPECIAL' or tl[0].token == ')'): break
				comma = ASTSpecialNode.build(tl)
				if (comma.special != ','): raise SlSyntaxExpectedError("','", comma)

		return cls(callkwargs, starkwargs, lineno=lineno, offset=offset)

class ASTCallableNode(ASTNode):
	def validate(self, ns):
		super().validate(ns)
		#dlog('-->', self.code.name)
		code_ns = ns.derive(self.code.name)
		for i in self.argdefs: code_ns.define(i, redefine=True)
		self.code.validate(code_ns)
		rettype = common_type((i.value for i in self.code.nodes if (isinstance(i, ASTKeywordExprNode) and i.keyword.keyword == 'return')), code_ns) or stdlib.void()
		if (self.type.type.identifier == 'auto'): self.type.type.identifier = rettype.typename
		else:
			expected = Signature.build(self.type, ns)
			if (rettype != expected): raise SlValidationError(f"Returning value of type '{rettype}' from function with return type '{expected}'", self, scope=ns.scope)
		#dlog('<--', self.code.name)

	def optimize(self, ns):
		super().optimize(ns)
		#dlog('-->', self.code.name)
		code_ns = ns.derive(self.code.name)
		for i in self.argdefs: code_ns.define(i, redefine=True)
		self.code.optimize(code_ns)
		#dlog('<--', self.code.name)

class ASTLambdaNode(ASTNonFinalNode, ASTCallableNode):
	__slots__ = ('argdefs', 'type', 'code')

	def __init__(self, argdefs, type, code, **kwargs):
		super().__init__(**kwargs)
		self.argdefs, self.type, self.code = argdefs, type, code

	def __fsig__(self):
		return f"({S(', ').join(self.argdefs)}) -> {self.type}"

	def __repr__(self):
		return f"<Lambda '{self.__fsig__()} {{...}}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		return f"{self.__fsig__()} {f'= {self.code.nodes[0].value}' if (len(self.code.nodes) == 1 and isinstance(self.code.nodes[0], ASTKeywordExprNode) and self.code.nodes[0].keyword.keyword == 'return') else repr(self.code)}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != '('): raise SlSyntaxExpectedError("'('", parenthesis)
		argdefs = list()
		while (tl and tl[0].typename != 'SPECIAL'):
			argdefs.append(ASTArgdefNode.build(tl))
			if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ','): ASTSpecialNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
		arrow = ASTOperatorNode.build(tl)
		if (arrow.operator != '->'): raise SlSyntaxExpectedError("'->'", arrow)
		type = ASTTypedefNode.build(tl)
		if (tl and (tl[0].typename != 'SPECIAL' or tl[0].token not in (*'={',))): raise SlSyntaxExpectedError("'=' or '{'", tl[0])
		cdef = ASTSpecialNode.build(tl)
		if (cdef.special != '='): raise SlSyntaxExpectedError('=', cdef)
		code = ASTCodeNode([ASTKeywordExprNode(ASTKeywordNode('return', lineno=lineno, offset=offset), ASTExprNode.build(tl), lineno=lineno, offset=offset)], name='<lambda>')

		return cls(argdefs, type, code, lineno=lineno, offset=offset)

class ASTBlockNode(ASTNonFinalNode):
	__slots__ = ('code',)

	def __init__(self, code, **kwargs):
		super().__init__(**kwargs)
		self.code = code

	def __str__(self):
		return repr(self.code) if (len(self.code.nodes) > 1) else repr(self.code)[1:-1].strip()

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if (tl[0].typename == 'SPECIAL' and tl[0].token == '{'):
			ASTSpecialNode.build(tl)
			code = (yield from ASTCodeNode.build('<block>'))
		else:
			yield '<expr>'
			code = ASTCodeNode([ASTExprNode.build(tl)], name='')

		return cls(code, lineno=lineno, offset=offset)

class ASTFinalNode(ASTNode): pass

class ASTDefinitionNode(ASTNode):
	def validate(self, ns):
		super().validate(ns)
		ns.define(self)

class ASTFuncdefNode(ASTFinalNode, ASTDefinitionNode, ASTCallableNode):
	__slots__ = ('type', 'name', 'argdefs', 'code')

	def __init__(self, type, name, argdefs, code, **kwargs):
		super().__init__(**kwargs)
		self.type, self.name, self.argdefs, self.code = type, name, argdefs, code

	def __fsig__(self):
		return f"{self.type or 'def'} {self.name}({S(', ').join(self.argdefs)})"

	def __repr__(self):
		return f"<Funcdef '{self.__fsig__()} {{...}}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		isexpr = len(self.code.nodes) == 1 and isinstance(self.code.nodes[0], ASTKeywordExprNode) and self.code.nodes[0].keyword.keyword == 'return'
		r = f"{self.__fsig__()} {f'= {self.code.nodes[0].value}' if (isexpr) else repr(self.code)}"
		return r if (isexpr) else r.join('\n\n')

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		type = ASTTypedefNode.build(tl)
		name = ASTIdentifierNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != '('): raise SlSyntaxExpectedError("'('", parenthesis)
		argdefs = list()
		while (tl and tl[0].typename != 'SPECIAL'):
			argdef = ASTArgdefNode.build(tl)
			if (argdefs and argdef.value is None and argdefs[-1].value is not None): raise SlSyntaxError(f"Non-default argument {argdef} follows default argument {argdefs[-1]}")
			argdefs.append(argdef)
			if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ','): ASTSpecialNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
		if (not tl): raise SlSyntaxExpectedError("'=' or '{'", lineno=lineno, offset=-1)
		if (tl[0].typename != 'SPECIAL' or tl[0].token not in (*'={',)): raise SlSyntaxExpectedError("'=' or '{'", tl[0])
		cdef = ASTSpecialNode.build(tl)
		if (cdef.special == '='):
			yield name.identifier
			code = ASTCodeNode([ASTKeywordExprNode(ASTKeywordNode('return', lineno=lineno, offset=offset), ASTExprNode.build(tl), lineno=lineno, offset=offset)], name=name.identifier)
		elif (cdef.special == '{'):
			code = (yield from ASTCodeNode.build(name.identifier))

		return cls(type, name, argdefs, code, lineno=lineno, offset=offset)

class ASTKeywordExprNode(ASTFinalNode):
	__slots__ = ('keyword', 'value')

	def __init__(self, keyword, value, **kwargs):
		super().__init__(**kwargs)
		self.keyword, self.value = keyword, value

	def __str__(self):
		return f"{self.keyword}{f' {self.value}' if (self.value is not None) else ''}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		keyword = ASTKeywordNode.build(tl)
		if (not isinstance(keyword.keyword, ExprKeyword)): raise SlSyntaxExpectedError('ExprKeyword', keyword)
		if (not tl): value = None
		elif (keyword.keyword == 'import'):
			lineno_, offset_ = tl[0].lineno, tl[0].offset
			value = ASTIdentifierNode(str().join(tl.pop(0).token for _ in range(len(tl))), lineno=lineno_, offset=offset_) # TODO Identifier? (or document it)
		else: value = ASTExprNode.build(tl)

		return cls(keyword, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		if (self.keyword.keyword == 'import'):
			ns.define(ASTIdentifierNode(self.value.identifier.partition('::')[2], lineno=self.value.lineno, offset=self.value.offset))
			return
		super().validate(ns)

class ASTAssignvalNode(ASTNode):
	def validate(self, ns):
		super().validate(ns)
		if (self.name.identifier not in ns): raise SlValidationNotDefinedError(self.name, scope=ns.scope)
		vartype = ns.signatures[self.name.identifier]
		if (self.value is not None):
			valtype = Signature.build(self.value, ns)
			if (vartype != valtype): raise SlValidationError(f"Assignment of '{self.value}' of type '{valtype}' to '{self.name}' of type '{vartype}'", self, scope=ns.scope)

class ASTVardefNode(ASTFinalNode, ASTAssignvalNode, ASTDefinitionNode):
	__slots__ = ('type', 'name', 'value')

	def __init__(self, type, name, value, **kwargs):
		super().__init__(**kwargs)
		self.type, self.name, self.value = type, name, value

	def __str__(self):
		return f"{self.type} {self.name}{f' = {self.value}' if (self.value is not None) else ''}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		type = ASTTypedefNode.build(tl)
		name = ASTIdentifierNode.build(tl)
		assignment = ASTSpecialNode.build(tl) if (tl and tl[0].typename == 'SPECIAL') else None
		if (assignment is not None and assignment.special != '='): raise SlSyntaxExpectedError('assignment', assignment)
		value = ASTExprNode.build(tl) if (assignment is not None) else None

		return cls(type, name, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		if (self.type.type.identifier == 'auto'): self.type.type.identifier = Signature.build(self.value, ns).typename
		super().validate(ns)

	def optimize(self, ns):
		super().optimize(ns)
		#if (ns.signatures[self.name.identifier].modifiers.const): self.flags.optimized_out = True # TODO

class ASTAssignmentNode(ASTFinalNode, ASTAssignvalNode):
	__slots__ = ('name', 'inplace_operator', 'value')

	def __init__(self, name, inplace_operator, value, **kwargs):
		super().__init__(**kwargs)
		self.name, self.inplace_operator, self.value = name, inplace_operator, value

	def __str__(self):
		return f"{self.name} {self.inplace_operator or ''}= {self.value}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		name = ASTIdentifierNode.build(tl)
		inplace_operator = ASTOperatorNode.build(tl) if (tl and tl[0].typename == 'OPERATOR') else None
		if (inplace_operator is not None and not isinstance(inplace_operator.operator, BinaryOperator)): raise SlSyntaxExpectedError('BinaryOperator', inplace_operator)
		assignment = ASTSpecialNode.build(tl)
		if (assignment.special != '='): raise SlSyntaxExpectedError('assignment', assignment)
		value = ASTExprNode.build(tl)

		return cls(name, inplace_operator, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		vartype = ns.signatures[self.name.identifier]
		valtype = Signature.build(self.value, ns)
		if (vartype.modifiers.const): raise SlValidationError(f"Assignment to const '{self.name}'", self, scope=ns.scope)

class ASTFunccallNode(ASTFinalNode):
	__slots__ = ('callable', 'callargs', 'callkwargs')

	def __init__(self, callable, callargs, callkwargs, **kwargs):
		super().__init__(**kwargs)
		self.callable, self.callargs, self.callkwargs = callable, callargs, callkwargs

	def __str__(self):
		return f"{str(self.callable).join('()') if (isinstance(self.callable, ASTValueNode) and isinstance(self.callable.value, (ASTFunccallNode, ASTLambdaNode))) else self.callable}({self.callargs}{', ' if (str(self.callargs) and str(self.callkwargs)) else ''}{self.callkwargs})"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		callable = ASTExprNode.build(tl, fcall=True)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != '('): raise SlSyntaxExpectedError("'('", parenthesis)
		callargs = ASTCallargsNode.build(tl)
		callkwargs = ASTCallkwargsNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)

		return cls(callable, callargs, callkwargs, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		fsig = Signature.build(self.callable, ns)
		if (not isinstance(fsig, Function)): raise SlValidationError(f"'{self.callable}' of type '{fsig}' is not callable", self.callable, scope=ns.scope)
		callargssig = CallArguments.build(self, ns) # TODO: starargs
		if (callargssig not in fsig.call): raise SlValidationError(f"Parameters '({callargssig})' don't match any of '{self.callable}' signatures:\n{S(fsig.callargssigstr).indent()}\n", self, scope=ns.scope)

class ASTConditionalNode(ASTFinalNode):
	__slots__ = ('condition', 'code')

	def __init__(self, condition, code, **kwargs):
		super().__init__(**kwargs)
		self.condition, self.code = condition, code

	def __str__(self):
		return f"if ({self.condition}) {self.code}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if_ = ASTKeywordNode.build(tl)
		if (if_.keyword != 'if'): raise SlSyntaxExpectedError("'if'", if_)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != '('): raise SlSyntaxExpectedError("'('", parenthesis)
		condition = ASTExprNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
		code = (yield from ASTBlockNode.build(tl))

		return cls(condition, code, lineno=lineno, offset=offset)

class ASTForLoopNode(ASTFinalNode):
	__slots__ = ('name', 'iterable', 'code')

	def __init__(self, name, iterable, code, **kwargs):
		super().__init__(**kwargs)
		self.name, self.iterable, self.code = name, iterable, code

	def __str__(self):
		return f"for {self.name} in ({self.iterable}) {self.code}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		for_ = ASTKeywordNode.build(tl)
		if (for_.keyword != 'for'): raise SlSyntaxExpectedError("'for'", for_)
		name = ASTIdentifierNode.build(tl)
		in_ = ASTKeywordNode.build(tl)
		if (in_.keyword != 'in'): raise SlSyntaxExpectedError("'in'", in_)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != '('): raise SlSyntaxExpectedError("'('", parenthesis)
		iterable = ASTExprNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
		code = (yield from ASTBlockNode.build(tl))

		return cls(name, iterable, code, lineno=lineno, offset=offset)

class ASTWhileLoopNode(ASTFinalNode):
	__slots__ = ('condition', 'code')

	def __init__(self, condition, code, **kwargs):
		super().__init__(**kwargs)
		self.condition, self.code = condition, code

	def __str__(self):
		return f"while ({self.condition}) {self.code}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		while_ = ASTKeywordNode.build(tl)
		if (while_.keyword != 'while'): raise SlSyntaxExpectedError("'while'", while_)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != '('): raise SlSyntaxExpectedError("'('", parenthesis)
		condition = ASTExprNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
		code = (yield from ASTBlockNode.build(tl))

		return cls(condition, code, lineno=lineno, offset=offset)

class ASTElseClauseNode(ASTFinalNode):
	__slots__ = ('code',)

	def __init__(self, code, **kwargs):
		super().__init__(**kwargs)
		self.code = code

	def __str__(self):
		return f"else {self.code}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		else_ = ASTKeywordNode.build(tl)
		if (else_.keyword != 'else'): raise SlSyntaxExpectedError("'else'", else_)
		code = (yield from ASTBlockNode.build(tl))

		return cls(code, lineno=lineno, offset=offset)

def build_ast(code, name=None, *, interactive=False):
	code = copy.deepcopy(code)
	root = ASTRootNode.build(name)
	code_stack = [(root, next(root))]
	next(root)

	final_nodes = ASTFinalNode.__subclasses__()
	if (interactive): final_nodes += (ASTExprNode,)
	for ii, tl in enumerate(code):
		if (not tl): continue
		lineno, offset = tl[0].lineno, tl[0].offset

		err = set()
		for i in final_nodes:
			try:
				c = tl.copy()
				r = i.build(c)
				if (inspect.isgenerator(r)):
					code_stack.append((r, next(r)))
					try: r = next(r)
					except StopIteration as ex: code_stack.pop(); r = ex.args[0]
					else:
						assert r is None
						if (c):
							if (c[-1].typename == 'SPECIAL' and c[-1].token == '}'): code.insert(ii+1, [c.pop()])
							code.insert(ii+1, c)
						err.clear()
						break
				assert r is not None
				if (c): raise SlSyntaxExpectedNothingError(c[0])
			except SlSyntaxEmpty: err.clear(); break
			except SlSyntaxNoToken: err.add(SlSyntaxExpectedError(f"More tokens for {i.__name__[3:-4]}", lineno=lineno, offset=offset))
			except SlSyntaxExpectedError as ex: ex.expected += f" at offset {ex.offset if (ex.offset != -1) else '<end of line>'} (for {i.__name__[3:-4]})"; err.add(ex)
			else: code_stack[-1][0].send(r); err.clear(); break
		else:
			if (len(code_stack) > 1 and tl and tl[0].typename == 'SPECIAL' and tl[0].token == '}'):
				if (tl[1:]): code.insert(ii+1, tl[1:])
				try: next(code_stack.pop()[0])
				except StopIteration as ex: code_stack[-1][0].send(ex.args[0]); err.clear()
				else: raise WTFException()
			elif (not err): raise SlSyntaxError("Unknown structure", lineno=lineno, offset=offset, length=0, scope='.'.join(i[1] for i in code_stack if i[1]))

		if (err): raise SlSyntaxMultiExpectedError(S(sorted(set(map(operator.attrgetter('expected'), err)), reverse=True)).uniquize(), S(sorted(err, key=operator.attrgetter('offset'))).uniquize(), lineno=max(err, key=operator.attrgetter('lineno')).lineno, offset=max(err, key=lambda x: x.offset if (x.offset != -1) else inf).offset, length=min(i.length for i in err if i.length), scope='.'.join(i[1] for i in code_stack if i[1]) if (code_stack[0][1] is not None) else None)

	assert len(code_stack) == 1
	try: next(code_stack.pop()[0])
	except StopIteration as ex: return ex.args[0]

def walk_ast_nodes(node):
	if (isiterable(node) and not isinstance(node, str)):
		for i in node: yield from walk_ast_nodes(i)
	if (not isinstance(node, ASTNode)): return
	yield node
	for i in node.__slots__: yield from walk_ast_nodes(getattr(node, i))

class _SignatureBase: pass

class Signature(_SignatureBase):
	__slots__ = ('typename', 'modifiers')

	operators = dict()
	call = dict()
	itemget = dict()
	attrops = ()

	@init_defaults
	@autocast
	def __init__(self, *, typename, modifiers: paramset, attrops: tuple):
		self.typename, self.modifiers, self.attrops = typename, modifiers, attrops

	@property
	def __reprname__(self):
		return type(self).__name__

	def __repr__(self):
		return f"<{self.__reprname__} {type(self).__name__}>"

	def __eq__(self, x):
		return self.typename == x.typename

	def __hash__(self):
		return hash(tuple(getattr(self, i) for i in self.__slots__))

	@classmethod
	@dispatch
	def build(cls, x: ASTArgdefNode, ns): # TODO: modifiers
		return cls.build(x.type, ns)

	@classmethod
	@dispatch
	def build(cls, x: ASTVardefNode, ns):
		r = cls.build(x.type, ns)
		ns.signatures[x.name.identifier] = r
		if (x.value is not None): ns.values[x.name] = x.value if (not r.modifiers.volatile and r.modifiers.const) else None
		return r

	@classmethod
	@dispatch
	def build(cls, x: ASTTypedefNode, ns):
		if (x.type.identifier not in builtin_names): raise SlValidationNotDefinedError(x.type, scope=ns.scope)
		return builtin_names[x.type.identifier](modifiers=x.modifiers)

	@classmethod
	@dispatch
	def build(cls, x: ASTValueNode, ns):
		return cls.build(x.value, ns)

	@classmethod
	@dispatch
	def build(cls, x: ASTLiteralNode, ns):
		return builtin_names[literal_type(x.literal).__name__]()

	@classmethod
	@dispatch
	def build(cls, x: ASTIdentifierNode, ns):
		if (x.identifier in builtin_names): return builtin_names[x.identifier]()
		if (x.identifier not in ns): raise SlValidationNotDefinedError(x, scope=ns.scope)
		return ns.signatures[x.identifier]

	@classmethod
	@dispatch
	def build(cls, x: ASTFunccallNode, ns):
		return cls.build(x.callable, ns).call[CallArguments.build(x, ns)]

	@classmethod
	@dispatch
	def build(cls, x: ASTFuncdefNode, ns):
		return Function.build(x, ns)

	@classmethod
	@dispatch
	def build(cls, x: ASTItemgetNode, ns):
		return cls.build(x.value, ns).itemget[cls.build(x.key, ns)]

	@classmethod
	@dispatch
	def build(cls, x: ASTAttrgetNode, ns):
		return cls.build(x.value, ns).attrops[x.optype]

	@classmethod
	@dispatch
	def build(cls, x: ASTUnaryExprNode, ns):
		return cls.build(x.value, ns).operators[x.operator.operator]

	@classmethod
	@dispatch
	def build(cls, x: ASTBinaryExprNode, ns):
		return cls.build(x.lvalue, ns).operators[x.operator.operator, cls.build(x.rvalue, ns)]

	@classmethod
	@dispatch
	def build(cls, x: _SignatureBase, ns):
		return x

class Function(Signature):
	__slots__ = ('name', 'call')

	def __init__(self, *, name, **kwargs):
		super().__init__(typename='function', **kwargs)
		self.name = name
		self.call = listmap()

	def __repr__(self):
		return f"<Function {self.name}>"

	@property
	def callargssigstr(self):
		return '\n'.join(f"{self.name}({args})" for args, ret in self.call.items())

	@classmethod
	@dispatch
	def build(cls, x: ASTFuncdefNode, ns, *, redefine=False):
		name = x.name.identifier
		if (name not in ns): ns.signatures[name] = cls(name=name)
		callargssig = CallArguments(args=tuple(Signature.build(i, ns) for i in x.argdefs))
		if (not redefine and callargssig in ns.signatures[name].call): raise SlValidationRedefinedError(x, ns.signatures[name].call[callargssig], scope=ns.scope)
		ns.signatures[name].call[callargssig] = Signature.build(x.type, ns)
		return ns.signatures[name]

class Object(Signature):
	__slots__ = ('attrops',)

class CallArguments:
	__slots__ = ('args', 'starargs', 'kwargs', 'starkwargs')

	@init_defaults
	@autocast
	def __init__(self, *, args: tuple, starargs: tuple, kwargs: tuple, starkwargs: tuple):
		self.args, self.starargs, self.kwargs, self.starkwargs = args, starargs, kwargs, starkwargs

	def __repr__(self):
		return S(', ').join((*self.args, *('*'+i for i in self.starargs), *(f"{v} {k}" for k, v in self.kwargs), *('**'+i for i in self.starkwargs)))

	def __eq__(self, x):
		return all(getattr(self, i) == getattr(x, i) for i in self.__slots__)

	def __hash__(self):
		return hash(tuple(getattr(self, i) for i in self.__slots__))

	@property
	def nargs(self):
		return sum(len(getattr(self, i)) for i in self.__slots__)

	@classmethod
	@dispatch
	def build(cls, x: ASTFunccallNode, ns): # TODO: starargs
		return cls(args=tuple(Signature.build(i, ns) for i in x.callargs.callargs), kwargs=tuple((k, Signature.build(v, ns)) for k, v in x.callkwargs.callkwargs))

class Namespace:
	__slots__ = ('signatures', 'scope', 'values', 'refcount', 'flags', 'warnclasses')

	class _Values:
		@init_defaults
		def __init__(self, values: dict):
			self.values = values

		def __contains__(self, x):
			try: self[x]
			except (DispatchError, KeyError): return False
			else: return True

		@dispatch
		def __getitem__(self, x: ASTLiteralNode):
			return eval(str(x.literal))

		@dispatch
		def __getitem__(self, x: ASTValueNode):
			return self[x.value]

		@dispatch
		def __getitem__(self, x: ASTIdentifierNode):
			return self.values[x.identifier]

		@dispatch
		def __getitem__(self, x: str):
			return self.values[x]

		@dispatch
		def __setitem__(self, k, v: ASTValueNode):
			self[k] = v.value

		@dispatch
		def __setitem__(self, x: ASTIdentifierNode, v: ASTLiteralNode):
			self.values[x.identifier] = eval(str(v.literal))

		@dispatch
		def __setitem__(self, x: ASTIdentifierNode, v: NoneType):
			pass

		@dispatch
		def __setitem__(self, k: str, v):
			self.values[k] = v

		@dispatch
		def __setitem__(self, k, v):
			pass

		@dispatch
		def __delitem__(self, x: ASTValueNode):
			del self[x.value]

		@dispatch
		def __delitem__(self, x: ASTIdentifierNode):
			del self.values[x.identifier]

		def copy(self):
			return self.__class__(values=self.values.copy())

	@init_defaults
	def __init__(self, scope, *, signatures: dict, values: _Values, refcount: lambda: Sdict(int), warnclasses: paramset, **kwargs):
		self.scope, self.signatures, self.values, self.refcount, self.warnclasses = scope, signatures, values, refcount, warnclasses
		self.flags = paramset(k for k, v in kwargs.items() if v)
		#self.derive.clear_cache()

	def __repr__(self):
		return f"<Namespace of scope '{self.scope}'>"

	def __contains__(self, x):
		return x in builtin_names or x in self.signatures

	@cachedfunction
	def derive(self, scope):
		return Namespace(signatures=self.signatures.copy(), values=self.values.copy(), scope=self.scope+'.'+scope)

	@dispatch
	def define(self, x: ASTIdentifierNode):
		if (x.identifier in self): raise SlValidationRedefinedError(x, self.signatures[x.identifier], scope=self.scope)
		self.values[x.identifier] = None
		self.signatures[x.identifier] = None

	@dispatch
	def define(self, x: ASTFuncdefNode):
		return self.define(x, redefine=True)

	@dispatch
	def define(self, x, redefine=False):
		if (redefine):
			try: del self.values[x.name]
			except KeyError: pass
		elif (x.name.identifier in self): raise SlValidationRedefinedError(x.name, self.signatures[x.name.identifier], scope=self.scope)
		self.signatures[x.name.identifier] = Signature.build(x, self)

from . import stdlib
from .stdlib import builtin_names

def validate_ast(ast, ns=None):
	Namespace.derive.clear_cache()
	return ast.code.validate(ns)

class SlValidationException(Exception): pass

class SlValidationError(SlValidationException):
	__slots__ = ('desc', 'node', 'line', 'scope')

	def __init__(self, desc, node, line='', *, scope=None):
		self.desc, self.node, self.line, self.scope = desc, node, line, scope

	def __str__(self):
		l, line = lstripcount(self.line.partition('\n')[0].replace('\t', ' '), ' \t')
		offset = (self.node.offset-l) if (self.node.offset != -1) else len(line)
		return (f'\033[2m(in {self.scope})\033[0m ' if (self.scope is not None) else '')+f"Validation error: {self.desc}{self.at}"+(':\n'+\
			'  \033[1m'+line[:offset]+'\033[91m'+line[offset:]+'\033[0m\n'+\
			'  '+' '*offset+'\033[95m^'+'~'*(self.node.length-1) if (line) else '')

	@property
	def at(self):
		return f" at line {self.node.lineno}, offset {self.node.offset}"

	@property
	def lineno(self):
		return self.node.lineno

class SlValidationNotDefinedError(SlValidationError):
	def __init__(self, identifier, **kwargs):
		super().__init__(f"'{identifier.identifier}' is not defined", identifier, **kwargs)

class SlValidationRedefinedError(SlValidationError):
	def __init__(self, identifier, definition, **kwargs):
		super().__init__(f"'{identifier}' redefined (defined as '{definition}')", identifier, **kwargs)# at lineno {definition.lineno}

def optimize_ast(ast, ns): return ast.code.optimize(ns)

# by Sdore, 2019
