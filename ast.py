#!/usr/bin/python3
# Slang AST

import abc
from . import sld
from .lexer import *
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
	r = tuple(Signature.build(i, ns) for i in l)
	if (not r): return None
	if (len(r) > 1): raise TODO(r)
	return first(r)

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
		return f"""<Code{f" '{self.name}'" if (self.name and self.name != '<code>') else ''}>"""

	def __str__(self):
		return (S('\n').join(self.nodes).indent().join('\n\n') if (self.nodes) else '').join('{}')

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
			if (i.typename == 'SPECIAL' and (i.token[0] == '#' or i.token == '\\')): del tl[ii-off]; off += 1
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

		if (tl[0].typename == 'LITERAL'): value = ASTLiteralNode.build(tl)
		else:
			types = allsubclasses(ASTLiteralStructNode)+[ASTLiteralNode, ASTFunccallNode, ASTAttrgetNode, ASTItemgetNode, ASTIdentifierNode, ASTLambdaNode]
			if (fcall): types.remove(ASTFunccallNode); types.remove(ASTLambdaNode) # XXX lambda too?
			err = set()
			for i in types:
				tll = tl.copy()
				try: value = i.build(tll)
				except SlSyntaxExpectedError as ex: err.add(ex); continue
				except SlSyntaxException: continue
				else: tl[:] = tll; break
			else: raise SlSyntaxMultiExpectedError.from_list(err)

		return cls(value, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		if (isinstance(self.value, ASTIdentifierNode)):
			if (self.value.identifier not in ns): raise SlValidationNotDefinedError(self.value, scope=ns.scope)
			if (self.value.identifier not in ns.values): warn('uninitialized', f"using value of possibly uninitialized variable '{self.value}'", self, ns)

	def optimize(self, ns):
		super().optimize(ns)
		if (isinstance(self.value, ASTIdentifierNode) and ns.values.get(self.value)): self.value = ASTLiteralNode(repr(ns.values[self.value]), lineno=self.lineno, offset=self.offset) # TODO FIXME in functions

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
		start = None
		stop = None
		step = None
		if (tl and not (tl[0].typename == 'SPECIAL' and tl[0].token == ':')): start = ASTExprNode.build(tl)
		if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ':'):
			ASTSpecialNode.build(tl)
			if (tl and not (tl[0].typename == 'SPECIAL' and tl[0].token in ']:')): stop = ASTExprNode.build(tl)
			if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ':'):
				ASTSpecialNode.build(tl)
				if (tl and not (tl[0].typename == 'SPECIAL' and tl[0].token == ']')): step = ASTExprNode.build(tl)
			key = slice(start, stop, step)
		else: key = start
		bracket = ASTSpecialNode.build(tl)
		if (bracket.special != ']'): raise SlSyntaxExpectedError("']'", bracket)

		return cls(value, key, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		valsig = Signature.build(self.value, ns)
		keysig = Signature.build(self.key, ns)
		if ((keysig, self.key) not in valsig.itemget): raise SlValidationError(f"'{valsig}' does not support itemget by key of type '{keysig}'", self, scope=ns.scope)

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
		valsig = Signature.build(self.value, ns)
		if ((self.optype.special, self.attr.identifier) not in valsig.attrops): raise SlValidationError(f"'{valsig}' does not support attribute operation '{self.optype}' with attr '{self.attr}'", self, scope=ns.scope)

class ASTExprNode(ASTPrimitiveNode):
	@classmethod
	def build(cls, tl, *, fcall=False):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		for ii, p in enumerate(operators[::-1]):
			tll = tl.copy()
			try: value = ASTBinaryExprNode.build(tll, p)
			except SlSyntaxException: continue
			else: tl[:] = tll; return value

		tll = tl.copy()
		try: value = ASTUnaryExprNode.build(tll)
		except SlSyntaxException: pass
		else: tl[:] = tll; return value

		tll = tl.copy()
		try: value = ASTValueNode.build(tll, fcall=fcall)
		except SlSyntaxException as ex: pass
		else: tl[:] = tll; return value

		try:
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
				assert (lvl > 0)
				parenthesized.append(tl.pop(0))
			value = ASTExprNode.build(parenthesized)
			if (parenthesized): raise SlSyntaxExpectedNothingError(parenthesized[0])
		except SlSyntaxException: pass # TODO
		else: return value
		raise SlSyntaxExpectedError('Expr', lineno=lineno, offset=offset)

class ASTUnaryExprNode(ASTExprNode):
	__slots__ = ('operator', 'value')

	def __init__(self, operator, value, **kwargs):
		super().__init__(**kwargs)
		self.operator, self.value = operator, value

	def __str__(self):
		return f"{self.operator}{' ' if (self.operator.operator.isalpha()) else ''}{str(self.value).join('()') if (DEBUG_PRECEDENCE or isinstance(self.value, ASTBinaryExprNode) and operator_precedence(self.value.operator.operator) >= operator_precedence(self.operator.operator)) else self.value}"

	@classmethod
	def build(cls, tl):
		ASTPrimitiveNode.build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		operator = ASTOperatorNode.build(tl)
		if (not isinstance(operator.operator, UnaryOperator)): raise SlSyntaxExpectedError('UnaryOperator', operator)
		value = ASTExprNode.build(tl)

		return cls(operator, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		valsig = Signature.build(self.value, ns)
		op = self.operator.operator
		if (op not in valsig.operators): raise SlValidationError(f"'{valsig}' does not support unary operator '{op}'", self, scope=ns.scope)

	def optimize(self, ns):
		super().optimize(ns)
		if (ns.values.get(self.value)): return ASTValueNode(ASTLiteralNode(eval(f"{'not' if (self.operator.operator == '!') else self.operator} {ns.values[self.value]}"), lineno=self.lineno, offset=self.offset), lineno=self.lineno, offset=self.offset)

class ASTBinaryExprNode(ASTExprNode):
	__slots__ = ('lvalue', 'operator', 'rvalue')

	def __init__(self, lvalue, operator, rvalue, **kwargs):
		super().__init__(**kwargs)
		self.lvalue, self.operator, self.rvalue = lvalue, operator, rvalue

	def __str__(self):
		return f"{str(self.lvalue).join('()') if (DEBUG_PRECEDENCE or isinstance(self.lvalue, ASTBinaryExprNode) and operator_precedence(self.lvalue.operator.operator) > operator_precedence(self.operator.operator)) else self.lvalue}{str(self.operator).join('  ') if (operator_precedence(self.operator.operator) > 0) else self.operator}{str(self.rvalue).join('()') if (DEBUG_PRECEDENCE or isinstance(self.rvalue, ASTBinaryExprNode) and operator_precedence(self.rvalue.operator.operator) > operator_precedence(self.operator.operator)) else self.rvalue}"

	@classmethod
	def build(cls, tl, opset):
		ASTPrimitiveNode.build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		lasti = list()
		lvl = int()
		for ii, i in enumerate(tl):
			if (i.typename == 'SPECIAL'): lvl += 1 if (i.token == '(') else -1 if (i.token == ')') else 0
			if (lvl > 0): continue
			if (i.typename == 'OPERATOR' and isinstance(i.token, BinaryOperator) and i.token in opset): lasti.append(ii)
		for i in lasti[::-1]:
			tlr, tll = tl[:i], tl[i:]
			err = set()
			try:
				lvalue = ASTExprNode.build(tlr)
				if (tlr): raise SlSyntaxExpectedNothingError(tlr[0])
				operator = ASTOperatorNode.build(tll)
				rvalue = ASTExprNode.build(tll)
			except SlSyntaxException: pass
			else: tl[:] = tll; break
		else: raise SlSyntaxExpectedError('BinaryOperator', tl[0])

		return cls(lvalue, operator, rvalue, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		lsig = Signature.build(self.lvalue, ns)
		rsig = Signature.build(self.rvalue, ns)
		op = self.operator.operator
		if ((op, rsig) not in lsig.operators): raise SlValidationError(f"'{lsig}' does not support operator '{op}' with operand of type '{rsig}'", self, scope=ns.scope)

	def optimize(self, ns):
		super().optimize(ns)
		if (self.operator.operator == '**' and ns.values.get(self.lvalue) == 2 and (ns.values.get(self.rvalue) or 0) > 0): self.operator.operator, self.lvalue.value, ns.values[self.lvalue] = BinaryOperator('<<'), ASTLiteralNode('1', lineno=self.lvalue.value.lineno, offset=self.lvalue.value.offset), 1
		if (ns.values.get(self.lvalue) and ns.values.get(self.rvalue) and self.operator.operator != 'to'): return ASTValueNode(ASTLiteralNode(repr(eval(str(self))), lineno=self.lineno, offset=self.offset), lineno=self.lineno, offset=self.offset)

class ASTLiteralStructNode(ASTNode): pass

class ASTListNode(ASTLiteralStructNode):
	__slots__ = ('type', 'values')

	def __init__(self, type, values, **kwargs):
		super().__init__(**kwargs)
		self.type, self.values = type, values

	def __repr__(self):
		return f"<List of '{self.type}'>"

	def __str__(self):
		return f"[{self.type}{': ' if (self.values) else ''}{S(', ').join(self.values)}]"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		bracket = ASTSpecialNode.build(tl)
		if (bracket.special != '['): raise SlSyntaxExpectedError("'['", bracket)
		type = ASTIdentifierNode.build(tl)
		values = list()
		if (not (tl[0].typename == 'SPECIAL' and tl[0].token == ']')):
			colon = ASTSpecialNode.build(tl)
			if (colon.special != ':'): raise SlSyntaxExpectedError("':'", colon)
			while (tl and tl[0].typename != 'SPECIAL'):
				values.append(ASTExprNode.build(tl))
				if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ','): ASTSpecialNode.build(tl)
		bracket = ASTSpecialNode.build(tl)
		if (bracket.special != ']'): raise SlSyntaxExpectedError("']'", bracket)

		return cls(type, values, lineno=lineno, offset=offset)

	def validate(self, ns):
		typesig = Signature.build(self.type, ns)
		for i in self.values:
			if (Signature.build(i, ns) != typesig): raise SlValidationError(f"List item '{i}' does not match list type '{self.type}'", self, scope=ns.scope)

class ASTTupleNode(ASTLiteralStructNode):
	__slots__ = ('types', 'values')

	def __init__(self, types, values, **kwargs):
		super().__init__(**kwargs)
		self.types, self.values = types, values

	def __repr__(self):
		return f"<Tuple ({S(', ').join(self.types)})>"

	def __str__(self):
		return f"({S(', ').join((str(self.types[i])+' ' if (self.types[i] is not None) else '')+str(self.values[i]) for i in range(len(self.values)))}{','*(len(self.values) == 1)})"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != '('): raise SlSyntaxExpectedError("'('", parenthesis)
		types = list()
		values = list()
		while (tl and not (tl[0].typename == 'SPECIAL' and tl[0].token == ')')):
			types.append(ASTIdentifierNode.build(tl) if (len(tl) >= 2 and tl[0].typename == 'IDENTIFIER' and tl[1].token != ',') else None)
			values.append(ASTExprNode.build(tl))
			if (len(values) < 2 or tl and tl[0].typename == 'SPECIAL' and tl[0].token == ','): ASTSpecialNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)

		return cls(types, values, lineno=lineno, offset=offset)

	def validate(self, ns):
		for i in range(len(self.values)):
			if (Signature.build(self.values[i], ns) != Signature.build(self.types[i], ns)): raise SlValidationError(f"Tuple item '{self.values[i]}' does not match its type '{self.types[i]}'", self, scope=ns.scope)

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
		value = ASTValueNode.build(tl) if (isinstance(modifier, ASTSpecialNode) and modifier.special == '=') else None

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
		code_ns = ns.derive(self.code.name)
		code_ns.define(self, redefine=True)
		for i in self.argdefs:
			code_ns.define(i, redefine=True)
		self.code.validate(code_ns)

	def optimize(self, ns):
		super().optimize(ns)
		code_ns = ns.derive(self.code.name)
		self.code.optimize(code_ns)

class ASTFunctionNode(ASTCallableNode):
	def validate(self, ns):
		super().validate(ns)
		code_ns = ns.derive(self.code.name)
		rettype = common_type((i.value for i in self.code.nodes if (isinstance(i, ASTKeywordExprNode) and i.keyword.keyword == 'return')), code_ns) or stdlib.void()
		if (self.type.type.identifier == 'auto'): self.type.type.identifier = rettype.typename
		else:
			expected = Signature.build(self.type, ns)
			if (rettype != expected): raise SlValidationError(f"Returning value of type '{rettype}' from function with return type '{expected}'", self, scope=ns.scope)

class ASTLambdaNode(ASTNonFinalNode, ASTFunctionNode):
	__slots__ = ('argdefs', 'type', 'code')

	def __init__(self, argdefs, type, code, **kwargs):
		super().__init__(**kwargs)
		self.argdefs, self.type, self.code = argdefs, type, code

	def __fsig__(self):
		return f"({S(', ').join(self.argdefs)}) -> {self.type}"

	def __repr__(self):
		return f"<Lambda '{self.__fsig__()} {{...}}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		return f"{self.__fsig__()} {f'= {self.code.nodes[0].value}' if (len(self.code.nodes) == 1 and isinstance(self.code.nodes[0], ASTKeywordExprNode) and self.code.nodes[0].keyword.keyword == 'return') else self.code}"

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
		return str(self.code) if (len(self.code.nodes) > 1) else str(self.code)[1:-1].strip()

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
		Signature.build(self, ns)
		super().validate(ns)

class ASTFuncdefNode(ASTFinalNode, ASTDefinitionNode, ASTFunctionNode):
	__slots__ = ('type', 'name', 'argdefs', 'code')

	def __init__(self, type, name, argdefs, code, **kwargs):
		super().__init__(**kwargs)
		self.type, self.name, self.argdefs, self.code = type, name, argdefs, code

	def __fsig__(self):
		return f"{self.type or 'def'} {self.name}({S(', ').join(self.argdefs)})"

	def __repr__(self):
		return f"<Funcdef '{self.__fsig__()} {{...}}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		isexpr = (len(self.code.nodes) == 1 and isinstance(self.code.nodes[0], ASTKeywordExprNode) and self.code.nodes[0].keyword.keyword == 'return')
		r = f"{self.__fsig__()} {f'= {self.code.nodes[0].value}' if (isexpr) else self.code}"
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

class ASTClassdefNode(ASTFinalNode, ASTDefinitionNode, ASTCallableNode):
	__slots__ = ('name', 'bases', 'code', 'type')

	argdefs = ()

	def __init__(self, name, bases, code, **kwargs):
		super().__init__(**kwargs)
		self.name, self.bases, self.code = name, bases, code
		self.type = ASTTypedefNode([], self.name, lineno=self.lineno, offset=self.offset)

	def __repr__(self):
		return f"<Classdef '{self.name}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		return f"class {self.name}{S(', ').join(self.bases).join('()') if (self.bases) else ''} {self.code}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		class_ = ASTKeywordNode.build(tl)
		if (class_.keyword != 'class'): raise SlSyntaxExpectedError("'class'", class_)
		name = ASTIdentifierNode.build(tl)
		bases = list()
		if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == '('):
			parenthesis = ASTSpecialNode.build(tl)
			if (parenthesis.special != '('): raise SlSyntaxExpectedError("'('", parenthesis)
			while (tl and tl[0].typename != 'SPECIAL'):
				bases.append(ASTIdentifierNode.build(tl))
				if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ','): ASTSpecialNode.build(tl)
			parenthesis = ASTSpecialNode.build(tl)
			if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
		cdef = ASTSpecialNode.build(tl)
		if (cdef.special != '{'): raise SlSyntaxExpectedError("'{'", cdef)
		code = (yield from ASTCodeNode.build(name.identifier))

		return cls(name, bases, code, lineno=lineno, offset=offset)

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
		if (keyword.keyword == 'import'):
			if (not tl): raise SlSyntaxExpectedMoreTokensError('import', lineno=lineno)
			lineno_, offset_ = tl[0].lineno, tl[0].offset
			value = ASTIdentifierNode(str().join(tl.pop(0).token for _ in range(len(tl))), lineno=lineno_, offset=offset_) # TODO Identifier? (or document it)
		elif (keyword.keyword == 'delete'):
			value = ASTIdentifierNode.build(tl)
			#if (not value): raise SlSyntaxExpectedError('identifier', lineno=lineno, offset=-1)
		elif (tl): value = ASTExprNode.build(tl)
		else: value = None

		return cls(keyword, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		if (self.keyword.keyword == 'import'):
			m = re.fullmatch(r'(?:(?:(\w+):)?(?:([\w./]+)/)?([\w.]+):)?([\w*]+)', self.value.identifier)
			assert (m is not None)
			namespace, path, pkg, name = m.groups()
			if (namespace is None): namespace = 'sl'
			if (path is None): path = '.'
			if (pkg is None): pkg = name
			pkg = pkg.replace('.', '/')
			if (namespace != 'sl'):
				filename = f"{os.path.join(path, pkg)}.sld"
				f = sld.parse(open(filename).read())
				module_ns = f.namespace
			else:
				filename = f"{os.path.join(path, pkg)}.sl"
				src = open(filename, 'r').read()
				try:
					tl = parse_string(src)
					ast = build_ast(tl, filename)
					optimize_ast(ast, validate_ast(ast))
					module_ns = validate_ast(ast)
				except (SlSyntaxError, SlValidationError) as ex:
					ex.line = src.split('\n')[ex.lineno-1]
					raise SlValidationError(f"Error importing {self.value}", self, scope=ns.scope) from ex
			if (name != '*'): ns.define(ASTIdentifierNode(name, lineno=self.value.lineno, offset=self.value.offset)) # TODO object
			else: ns.signatures.update(module_ns.signatures) # TODO?
			#return # XXX?
		elif (self.keyword.keyword == 'delete'):
			if (self.value.identifier not in ns): raise SlValidationNotDefinedError(self.value, scope=ns.scope)
			ns.delete(self.value)
		super().validate(ns)

class ASTKeywordDefNode(ASTFinalNode):
	__slots__ = ('keyword', 'name', 'argdefs', 'code')

	def __init__(self, keyword, name, argdefs, code, **kwargs):
		super().__init__(**kwargs)
		self.keyword, self.name, self.argdefs, self.code = keyword, name, argdefs, code
		if (self.name is None): self.name = ASTIdentifierNode(self.code.name, lineno=self.lineno, offset=self.offset)

	def __repr__(self):
		return f"<KeywordDef '{self.name}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		return f"{self.keyword}{' '+S(', ').join(self.argdefs).join('()') if (isinstance(self.keyword.keyword, DefArgsKeyword)) else f' {self.name}' if (isinstance(self.keyword.keyword, DefNamedKeyword)) else ''} {self.code}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		keyword = ASTKeywordNode.build(tl)
		if (not isinstance(keyword.keyword, DefKeyword)): raise SlSyntaxExpectedError('DefKeyword', keyword)
		name = None
		argdefs = None
		if (isinstance(keyword.keyword, DefNamedKeyword)):
			name = ASTIdentifierNode.build(tl)
		elif (isinstance(keyword.keyword, DefArgsKeyword)):
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
		cdef = ASTSpecialNode.build(tl)
		if (cdef.special != '{'): raise SlSyntaxExpectedError('{', cdef)
		code = (yield from ASTCodeNode.build(f"<{keyword}>"))

		return cls(keyword, name, argdefs, code, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		code_ns = ns.derive(self.code.name)
		if (isinstance(self.keyword.keyword, DefArgsKeyword)):
			for i in self.argdefs:
				code_ns.define(i, redefine=True)
		self.code.validate(code_ns)

	def optimize(self, ns):
		super().optimize(ns)
		code_ns = ns.derive(self.code.name)
		self.code.optimize(code_ns)

class ASTAssignvalNode(ASTNode):
	def validate(self, ns):
		super().validate(ns)
		if (self.name.identifier not in ns): raise SlValidationNotDefinedError(self.name, scope=ns.scope)
		vartype = Signature.build(self.name, ns)
		if (self.value is not None):
			valtype = Signature.build(self.value, ns)
			if (valtype != vartype and vartype != valtype): raise SlValidationError(f"Assignment of value '{self.value}' of type '{valtype}' to variable '{self.name}' of type '{vartype}'", self, scope=ns.scope)

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
		assignment = None
		value = None
		if (tl and tl[0].typename == 'SPECIAL'):
			assignment = ASTSpecialNode.build(tl)
			if (assignment.special != '='): raise SlSyntaxExpectedError('assignment', assignment)
			value = ASTExprNode.build(tl)

		return cls(type, name, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		if (self.type.type.identifier == 'auto'): self.type.type.identifier = Signature.build(self.value, ns).typename
		ns.define(self)
		super().validate(ns)

	def optimize(self, ns):
		super().optimize(ns)
		#if (Signature.build(self.name, ns).modifiers.const): self.flags.optimized_out = True # TODO

class ASTAssignmentNode(ASTFinalNode, ASTAssignvalNode):
	__slots__ = ('name', 'isattr', 'assignment', 'inplace_operator', 'value')

	def __init__(self, name, isattr, assignment, inplace_operator, value, **kwargs):
		super().__init__(**kwargs)
		self.name, self.isattr, self.assignment, self.inplace_operator, self.value = name, isattr, assignment, inplace_operator, value

	def __str__(self):
		return f"{'.'*self.isattr}{self.name} {self.inplace_operator or ''}= {self.value}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		isattr = bool()
		if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == '.'): ASTSpecialNode.build(tl); isattr = True
		name = ASTIdentifierNode.build(tl)
		inplace_operator = None
		if (tl and tl[0].typename == 'OPERATOR'):
			inplace_operator = ASTOperatorNode.build(tl)
			if (not isinstance(inplace_operator.operator, BinaryOperator)): raise SlSyntaxExpectedError('BinaryOperator', inplace_operator)
		assignment = ASTSpecialNode.build(tl)
		if (assignment.special not in ('=', ':=')): raise SlSyntaxExpectedError('assignment', assignment)
		value = ASTExprNode.build(tl)

		return cls(name, isattr, assignment, inplace_operator, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		valtype = Signature.build(self.value, ns)
		if (self.assignment.special == ':='): ns.define(self.name, valtype, redefine=True)
		if (self.isattr): return # TODO
		super().validate(ns)
		vartype = Signature.build(self.name, ns)
		if (vartype.modifiers.const): raise SlValidationError(f"Assignment to const '{self.name}'", self, scope=ns.scope)

class ASTUnpackAssignmentNode(ASTFinalNode, ASTAssignvalNode):
	__slots__ = ('names', 'assignment', 'inplace_operator', 'value')

	def __init__(self, names, assignment, inplace_operator, value, **kwargs):
		super().__init__(**kwargs)
		self.names, self.assignment, self.inplace_operator, self.value = names, assignment, inplace_operator, value

	def __str__(self):
		return f"{S(', ').join(self.names)} {self.inplace_operator or ''}= {self.value}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		names = list()
		while (tl and tl[0].typename != 'SPECIAL'):
			names.append(ASTIdentifierNode.build(tl))
			if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ','): ASTSpecialNode.build(tl)
		inplace_operator = ASTOperatorNode.build(tl) if (tl and tl[0].typename == 'OPERATOR') else None
		if (inplace_operator is not None and not isinstance(inplace_operator.operator, BinaryOperator)): raise SlSyntaxExpectedError('BinaryOperator', inplace_operator)
		assignment = ASTSpecialNode.build(tl)
		if (assignment.special not in ('=', ':=')): raise SlSyntaxExpectedError('assignment', assignment)
		value = ASTExprNode.build(tl)

		return cls(names, assignment, inplace_operator, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		valtype = Signature.build(self.value, ns)
		if (self.assignment.special == ':='):
			for name, type in zip(self.names, valtype.valtypes):
				ns.define(name, type, redefine=True)
		vartypes = tuple(Signature.build(i, ns) for i in self.names)
		for name, vartype in zip(self.names, vartypes):
			if (vartype.modifiers.const): raise SlValidationError(f"Assignment to const '{name}'", self, scope=ns.scope)
		if (vartypes != valtype.valtypes): raise SlValidationError(f"Unpacking assignment of '{valtype}' to variables of types {vartypes}", self, scope=ns.scope)

class ASTAttrsetNode(ASTFinalNode):
	__slots__ = ('value', 'assignment')

	def __init__(self, value, assignment, **kwargs):
		super().__init__(**kwargs)
		self.value, self.assignment = value, assignment

	def __str__(self):
		return f"{self.value}{self.assignment}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		value = ASTIdentifierNode.build(tl)
		assignment = ASTAssignmentNode.build(tl)
		if (not assignment.isattr): raise SlSyntaxExpectedError('attrset', assignment)

		return cls(value, assignment, lineno=lineno, offset=offset)

	def validate(self, ns):
		assert (self.assignment.isattr)
		super().validate(ns)
		# TODO: attr check
		#valsig = Signature.build(self.value, ns)
		#if ((self.optype.special, self.attr.identifier) not in valsig.attrops): raise SlValidationError(f"'{valsig}' does not support attribute operation '{self.optype}' with attr '{self.attr}'", self, scope=ns.scope)

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
		if (not isinstance(fsig, Callable)): raise SlValidationError(f"'{self.callable}' of type '{fsig}' is not callable", self.callable, scope=ns.scope)
		callargssig = CallArguments.build(self, ns) # TODO: starargs
		if (callargssig not in fsig.call): raise SlValidationError(f"Parameters '({callargssig})' don't match any of '{self.callable}' signatures:\n{S(fsig.callargssigstr).indent()}\n", self, scope=ns.scope)

class ASTConditionalNode(ASTFinalNode):
	__slots__ = ('condition', 'code')

	def __init__(self, condition, code, **kwargs):
		super().__init__(**kwargs)
		self.condition, self.code = condition, code

	def __repr__(self):
		return f"<Conditional if '{self.condition}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		return f"if {self.condition} {self.code}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if_ = ASTKeywordNode.build(tl)
		if (if_.keyword != 'if'): raise SlSyntaxExpectedError("'if'", if_)
		condition = ASTExprNode.build(tl)
		code = (yield from ASTBlockNode.build(tl))

		return cls(condition, code, lineno=lineno, offset=offset)

class ASTForLoopNode(ASTFinalNode):
	__slots__ = ('name', 'iterable', 'code')

	def __init__(self, name, iterable, code, **kwargs):
		super().__init__(**kwargs)
		self.name, self.iterable, self.code = name, iterable, code

	def __repr__(self):
		return f"<ForLoop '{self.name}' in '{self.iterable}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		return f"for {self.name} in {self.iterable} {self.code}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		for_ = ASTKeywordNode.build(tl)
		if (for_.keyword != 'for'): raise SlSyntaxExpectedError("'for'", for_)
		name = ASTIdentifierNode.build(tl)
		in_ = ASTOperatorNode.build(tl)
		if (in_.operator != 'in'): raise SlSyntaxExpectedError("'in'", in_)
		iterable = ASTExprNode.build(tl)
		code = (yield from ASTBlockNode.build(tl))

		return cls(name, iterable, code, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		# TODO: validate iterability
		ns.define(self.name, Signature.build(self.iterable, ns).valtype)
		ns.weaken(self.name)

class ASTWhileLoopNode(ASTFinalNode):
	__slots__ = ('condition', 'code')

	def __init__(self, condition, code, **kwargs):
		super().__init__(**kwargs)
		self.condition, self.code = condition, code

	def __repr__(self):
		return f"<WhileLoop while '{self.condition}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		return f"while {self.condition} {self.code}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		while_ = ASTKeywordNode.build(tl)
		if (while_.keyword != 'while'): raise SlSyntaxExpectedError("'while'", while_)
		condition = ASTExprNode.build(tl)
		code = (yield from ASTBlockNode.build(tl))

		return cls(condition, code, lineno=lineno, offset=offset)

class ASTElseClauseNode(ASTFinalNode):
	__slots__ = ('code',)

	def __init__(self, code, **kwargs):
		super().__init__(**kwargs)
		self.code = code

	def __repr__(self):
		return f"<ElseClause on line {self.lineno}, offset {self.offset}>"

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
						assert (r is None)
						if (c):
							if (c[-1].typename == 'SPECIAL' and c[-1].token == '}'): code.insert(ii+1, [c.pop()])
							code.insert(ii+1, c)
						err.clear()
						break
				assert (r is not None)
				if (c): raise SlSyntaxExpectedNothingError(c[0])
			except SlSyntaxEmpty: err.clear(); break
			except SlSyntaxNoToken: err.add(SlSyntaxExpectedMoreTokensError(i.__name__[3:-4], lineno=lineno, offset=-2))
			except SlSyntaxMultiExpectedError as ex: pass#err.add(ex) # TODO FIXME
			except SlSyntaxExpectedError as ex: ex.usage = i.__name__[3:-4]; err.add(ex)
			else: code_stack[-1][0].send(r); err.clear(); break
		else:
			if (len(code_stack) > 1 and tl and tl[0].typename == 'SPECIAL' and tl[0].token == '}'):
				if (tl[1:]): code.insert(ii+1, tl[1:])
				try: next(code_stack.pop()[0])
				except StopIteration as ex: code_stack[-1][0].send(ex.args[0]); err.clear()
				else: raise WTFException()
			elif (not err): raise SlSyntaxError("Unknown structure", lineno=lineno, offset=offset, length=0, scope='.'.join(i[1] for i in code_stack if i[1]))

		if (err): raise SlSyntaxMultiExpectedError.from_list(err, scope='.'.join(i[1] for i in code_stack if i[1]) if (code_stack[0][1] is not None) else None)

	assert (len(code_stack) == 1)
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

	@init_defaults
	@autocast
	def __init__(self, *, typename, modifiers: paramset):
		self.typename, self.modifiers = typename, modifiers

	@property
	def __reprname__(self):
		return self.__class__.__name__

	def __repr__(self):
		return f"<{self.__reprname__} '{self.name}'>"

	def __eq__(self, x):
		return (x is not None and self.typename == x.typename)

	def __hash__(self):
		return hash(tuple(getattr(self, i) for i in self.__slots__))

	@property
	def name(self):
		return self.typename

	@staticitemget
	def itemget(x):
		raise KeyError()

	@staticitemget
	def attrops(optype, attr):
		raise KeyError()

	@classmethod
	@dispatch
	def build(cls, x: ASTArgdefNode, ns): # TODO: modifiers
		return cls.build(x.type, ns)

	@classmethod
	@dispatch
	def build(cls, x: ASTAssignvalNode, ns):
		r = cls.build(x.type, ns)
		#ns.signatures[x.name.identifier] = r
		if (x.value is not None): ns.values[x.name] = x.value if (not r.modifiers.volatile and r.modifiers.const) else None
		return r

	@classmethod
	@dispatch
	def build(cls, x: ASTTypedefNode, ns):
		r = cls.build(x.type, ns)
		r.modifiers.update(x.modifiers)
		return r

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
	def build(cls, x: ASTListNode, ns):
		return Collection(keytype=stdlib.int, valtype=Signature.build(x.type, ns))

	@classmethod
	@dispatch
	def build(cls, x: ASTTupleNode, ns):
		return MultiCollection(keytype=stdlib.int, valtypes=tuple(Signature.build(t if (t is not None) else v, ns) for t, v in zip(x.types, x.values)))

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
	def build(cls, x: ASTClassdefNode, ns):
		return Class.build(x, ns)

	@classmethod
	@dispatch
	def build(cls, x: ASTKeywordDefNode, ns):
		return KeywordDef.build(x, ns)

	@classmethod
	@dispatch
	def build(cls, x: ASTItemgetNode, ns):
		return cls.build(x.value, ns).itemget[cls.build(x.key, ns), x.key]

	@classmethod
	@dispatch
	def build(cls, x: ASTAttrgetNode, ns):
		return cls.build(x.value, ns).attrops[x.optype.special, x.attr.identifier]

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

class Callable(Signature, abc.ABC):
	__slots__ = ('call',)

	@abc.abstractproperty
	def callargssigstr(self):
		pass

class Function(Callable):
	__slots__ = ('name',)

	def __init__(self, *, name, **kwargs):
		super().__init__(typename='function', **kwargs)
		self.name = name
		self.call = listmap()

	@property
	def callargssigstr(self):
		return '\n'.join(f"{self.name}({args})" for args, ret in self.call.items())

	@staticitemget
	def attrops(optype, attr):
		if (optype == '.'):
			if (attr == 'map'): return stdlib._map()
		raise KeyError()

	@classmethod
	@dispatch
	def build(cls, x: ASTFuncdefNode, ns, *, redefine=False):
		name = x.name.identifier
		if (name not in ns): ns.signatures[name] = cls(name=name)
		callargssig = CallArguments(args=tuple(Signature.build(i, ns) for i in x.argdefs))
		if (not redefine and callargssig in ns.signatures[name].call): raise SlValidationRedefinedError(x.name, ns.signatures[name].call[callargssig], scope=ns.scope)
		ns.signatures[name].call[callargssig] = Signature.build(x.type, ns)
		return ns.signatures[name]

class KeywordDef(Callable):
	__slots__ = ('name',)

	def __init__(self, *, name, **kwargs):
		super().__init__(typename='keyworddef', **kwargs)
		self.name = name
		self.call = listmap()

	@property
	def callargssigstr(self):
		return '\n'.join(f"{self.name}({args})" for args, ret in self.call.items())

	@classmethod
	@dispatch
	def build(cls, x: ASTKeywordDefNode, ns, *, redefine=False):
		name = x.name.identifier
		if (name not in ns): ns.signatures[name] = cls(name=name)
		callargssig = CallArguments(args=tuple(Signature.build(i, ns) for i in x.argdefs or ()))
		if (not redefine and callargssig in ns.signatures[name].call): raise SlValidationRedefinedError(x.name, ns.signatures[name].call[callargssig], scope=ns.scope)
		ns.signatures[name].call[callargssig] = stdlib.void
		return ns.signatures[name]

class Object(Signature): pass

class Collection(Object):
	__slots__ = ('keytype', 'valtype')

	def __init__(self, *, keytype, valtype):
		self.keytype, self.valtype = keytype, valtype

	@property
	def typename(self):
		return self.valtype.typename

	@itemget
	@instantiate
	def itemget(self, keysig, key):
		if (keysig == self.keytype): return self.valtype
		raise KeyError()

class MultiCollection(Collection):
	__slots__ = ('valtypes', 'typename')

	def __init__(self, *, keytype, valtypes):
		Object.__init__(self, typename='tuple')
		self.keytype, self.valtypes = keytype, valtypes

	@itemget
	@instantiate
	def itemget(self, keysig, key):
		if (keysig == self.keytype): return self.valtypes[int(key)]
		raise KeyError()

class Class(Object, Callable):
	__slots__ = ('name', 'scope', 'constructor')

	def __init__(self, *, name, scope, **kwargs):
		super().__init__(typename='class', **kwargs)
		self.name, self.scope = name, scope
		self.constructor = listmap()

	def __str__(self):
		return self.name

	@property
	def callargssigstr(self):
		return '\n'.join(f"{self.name}({args})" for args, ret in self.call.items())

	@itemget
	def call(self, callargssig):
		return self.constructor[callargssig]

	@itemget
	def attrops(self, optype, attr):
		if (optype == '.'):
			return self.scope.signatures[attr]
		raise KeyError()

	@classmethod
	@dispatch
	def build(cls, x: ASTClassdefNode, ns, *, redefine=False):
		name = x.name.identifier
		if (not redefine and name in ns): raise SlValidationRedefinedError(x.name, ns.signatures[name], scope=ns.scope)
		else: ns.signatures[name] = cls(name=name, scope=ns.derive(x.code.name))
		for i in x.code.nodes:
			if (isinstance(i, ASTKeywordDefNode) and i.keyword.keyword == 'constr'):
				callargssig = CallArguments(args=tuple(Signature.build(j, ns) for j in i.argdefs or ()))
				if (not redefine and callargssig in ns.signatures[name].constructor): raise SlValidationRedefinedError(x.name, ns.signatures[name].constructor[callargssig], scope=ns.scope)
				ns.signatures[name].constructor[callargssig] = ns.signatures[name]
		return ns.signatures[name]

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
	__slots__ = ('signatures', 'scope', 'values', 'weak', 'refcount', 'flags', 'warnclasses')

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
			return self[x.identifier]

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
			del self[x.identifier]

		@dispatch
		def __delitem__(self, x: str):
			del self.values[x]

		def get(self, x):
			try: return self[x]
			except (DispatchError, KeyError): return None

		def items(self):
			return self.values.items()

		def copy(self):
			return self.__class__(values=self.values.copy())

	@init_defaults
	def __init__(self, scope, *, signatures: dict, values: _Values, weak: set, refcount: lambda: Sdict(int), warnclasses: paramset, **kwargs):
		self.scope, self.signatures, self.values, self.weak, self.refcount, self.warnclasses = scope, signatures, values, weak, refcount, warnclasses
		self.flags = paramset(k for k, v in kwargs.items() if v)
		#self.derive.clear_cache() # TODO FIXME (also cachedproperty)

	def __repr__(self):
		return f"<Namespace of scope '{self.scope}'>"

	def __contains__(self, x):
		return (x in builtin_names or x in self.signatures)

	@cachedfunction
	def derive(self, scope):
		return Namespace(signatures=self.signatures.copy(), values=self.values.copy(), weak=self.weak.copy(), scope=self.scope+'.'+scope)

	#@dispatch
	#def define(self, x: ASTIdentifierNode):
	#	if (x.identifier in self and x.identifier not in self.weak): raise SlValidationRedefinedError(x, self.signatures[x.identifier], scope=self.scope)
	#	self.values[x] = None
	#	self.signatures[x.identifier] = None
	#	self.weak.discard(x.identifier)

	@dispatch
	def define(self, x: ASTFuncdefNode):
		return self.define(x, redefine=True)

	#@dispatch
	#def define(self, x: str, *, value=None):
	#	assert (x not in self)
	#	self.values[x] = value
	#	self.signatures[x] = None

	@dispatch
	def define(self, x: lambda x: hasattr(x, 'name'), sig=None, *, redefine=False):
		if (redefine):
			try: del self.values[x.name]
			except KeyError: pass
			try: del self.signatures[x.name.identifier]
			except KeyError: pass
		self.define(x.name, sig if (sig is not None) else Signature.build(x, self), redefine=redefine)

	@dispatch
	def define(self, x: ASTIdentifierNode, sig, *, redefine=False):
		if (redefine):
			try: del self.values[x]
			except KeyError: pass
			try: del self.signatures[x.identifier]
			except KeyError: pass
		elif (x.identifier in self and x.identifier not in self.weak): raise SlValidationRedefinedError(x, self.signatures[x.identifier], scope=self.scope)
		self.signatures[x.identifier] = sig
		self.weak.discard(x.identifier)

	@dispatch
	def weaken(self, x: ASTIdentifierNode):
		self.weak.add(x.identifier)

	@dispatch
	def delete(self, x: ASTIdentifierNode):
		ok = bool()
		try: del self.values[x]
		except KeyError: pass
		else: ok = True
		try: del self.signatures[x.identifier]
		except KeyError: pass
		else: ok = True
		self.weak.discard(x.identifier)
		if (not ok): raise SlValidationNotDefinedError(x, scope=self.scope)

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
		offset = (self.node.offset-l) if (self.node.offset >= 0) else (len(line)+self.node.offset+1)
		return (f'\033[2m(in {self.scope})\033[0m ' if (self.scope is not None) else '')+f"Validation error: {self.desc}{self.at}"+(':\n'+\
			'  \033[1m'+line[:offset]+'\033[91m'*(self.node.offset >= 0)+line[offset:]+'\033[0m\n'+\
			'  '+' '*offset+'\033[95m^'+'~'*(self.node.length-1)+'\033[0m' if (line) else '') + \
			(f"\n\n\033[1;95mCaused by:\033[0m\n{self.__cause__}" if (self.__cause__ is not None) else '')

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

# by Sdore, 2020
