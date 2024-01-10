#!/usr/bin/python3
# Slang AST

import abc
from . import sld
from .lexer import *
from utils import *

DEFAULT_OLEVEL = 0
TAB_SIZE = 4
DEBUG_PRECEDENCE = False

def warn(class_, msg, node, ns):
	if (ns.warnclasses and class_ not in ns.warnclasses): return
	logexception(Warning(f"{msg} \033[2m(at line {node.lineno}, offset {node.offset})\033[0m \033[8m({class_})\033[0m"), raw=True, once=True)

def eval_literal(x):
	return eval(literal_repr(x))

def literal_repr(x):
	return (str if (isinstance(x, ASTNode)) else repr)(x)

def literal_type(x):
	r = eval(str(x))
	if (isinstance(r, str) and len(r) == 1 and re.match(r"'.+?'", x.strip())): return stdlib.char
	return type(r)

def common_type(l, ns): # TODO
	r = Slist(Signature.build(i, ns) for i in l).uniquize()
	r.reverse(); r = r.uniquize()
	if (not r): return None
	r = [i for i in r if not isinstance(i, stdlib.auto)]
	if (len(r) > 1): raise TODO(r)
	return first(r)

class ASTNode(ABCSlots):
	lineno: ...
	offset: ...
	flags: ...

	@abc.abstractmethod
	@init_defaults
	def __init__(self, *, lineno, offset, flags: paramset):
		self.lineno, self.offset, self.flags = lineno, offset, flags

	def __repr__(self):
		return f"<{self.typename} `{self.__str__()}' on line {self.lineno}, offset {self.offset}>"

	@abc.abstractmethod
	def __str__(self):
		return ''

	@abc.abstractclassmethod
	def build(cls, tl):
		if (not tl): raise SlSyntaxNoToken()

	def validate(self, ns):
		for i in allslots(self):
			v = getattr(self, i)
			if (isiterablenostr(v)):
				for jj, j in enumerate(v):
					if (hasattr(j, 'validate')):
						j.validate(ns)
			elif (hasattr(v, 'validate') and not isinstance(v, ASTCodeNode)):
				v.validate(ns)

	def optimize(self, ns):
		for i in allslots(self):
			v = getattr(self, i)
			if (isiterablenostr(v)):
				for jj, j in enumerate(v.copy()):
					if (hasattr(j, 'optimize')):
						r = j.optimize(ns)
						if (r is not None): v[jj] = r
						if (v[jj].flags.optimized_out): del v[jj]
			elif (hasattr(v, 'optimize') and not isinstance(v, ASTCodeNode)):
				r = v.optimize(ns)
				if (r is not None): setattr(self, i, r)
				if (getattr(self, i).flags.optimized_out): setattr(self, i, None)
		self.flags.optimized = 1

	@classproperty
	def typename(cls):
		return cls.__name__[3:-4]

	@property
	def length(self):
		#dlog(max((getattr(self, i) for i in allslots(self) if hasattr(getattr(self, i), 'offset')), key=lambda x: (x.lineno, x.offset)
		return sum(getattr(self, i).length for i in allslots(self) if hasattr(getattr(self, i), 'length'))

class ASTRootNode(ASTNode):
	code: ...

	def __init__(self, code, **kwargs):
		super().__init__(**kwargs)
		self.code = code

	def __repr__(self):
		return '<Root>'

	def __str__(self):
		return '<Root>'

	@classmethod
	def build(cls, name=None):
		code = (yield from ASTCodeNode.build([], name=name))
		return cls(code, lineno=code.lineno, offset=code.offset)

	def validate(self, ns=None):
		if (ns is None): ns = Namespace(self.code.name)
		super().validate(ns)
		self.code.validate(ns)
		return ns

	def optimize(self, ns, level=DEFAULT_OLEVEL):
		ns.olevel = level
		super().optimize(ns)
		self.code.optimize(ns)

class ASTCodeNode(ASTNode):
	nodes: ...
	name: ...

	def __init__(self, nodes, *, name='<code>', **kwargs):
		super().__init__(**kwargs)
		self.nodes, self.name = nodes, name

	def __repr__(self):
		return f"""<Code{f" `{self.name}'" if (self.name and self.name != '<code>') else ''}>"""

	def __str__(self):
		return (S('\n').join(map(lambda x: x.join('\n\n') if ('\n' in x) else x, map(str, self.nodes))).indent().replace('\n\n\n', '\n\n').strip('\n').join('\n\n') if (self.nodes) else '').join('{}')

	@classmethod
	def build(cls, tl, *, name):
		if (tl):
			cdef = ASTSpecialNode.build(tl)
			if (cdef.special != '{'): raise SlSyntaxExpectedError("'{'", cdef)
			lineno, offset = cdef.lineno, cdef.offset
		else: lineno = offset = None

		yield name
		nodes = list()
		while (True):
			c = yield
			if (c is None): break
			if (lineno is None): lineno, offset = c.lineno, c.offset
			nodes.append(c)

		return cls(nodes, name=name, lineno=lineno, offset=offset)

	#def validate(self, ns): # super
	#	for i in self.nodes:
	#		i.validate(ns)

	def optimize(self, ns):
		for ii, i in enumerate(self.nodes):
			r = i.optimize(ns)
			if (r is not None): self.nodes[ii] = r
		self.nodes = [i for i in self.nodes if not i.flags.optimized_out]

class ASTTokenNode(ASTNode):
	length: ...

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.length = sum(len(getattr(self, i)) for i in allslots(self) if isinstance(getattr(self, i, None), str))

	@abc.abstractclassmethod
	def build(cls, tl):
		super().build(tl)
		off = int()
		for ii, i in enumerate(tl.copy()):
			if (i.typename == 'SPECIAL' and (i.token[0] == '#' or i.token == '\\')): del tl[ii-off]; off += 1
		if (not tl): raise SlSyntaxEmpty()

class ASTIdentifierNode(ASTTokenNode):
	identifier: ...

	def __init__(self, identifier, **kwargs):
		self.identifier = identifier
		super().__init__(**kwargs)

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
	keyword: ...

	def __init__(self, keyword, **kwargs):
		self.keyword = keyword
		super().__init__(**kwargs)

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
	literal: ...

	def __init__(self, literal, **kwargs):
		self.literal = literal
		super().__init__(**kwargs)

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
	operator: ...

	def __init__(self, operator, **kwargs):
		self.operator = operator
		super().__init__(**kwargs)

	def __str__(self):
		return str(self.operator)

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if (tl[0].typename != 'OPERATOR'): raise SlSyntaxExpectedError('OPERATOR', tl[0])
		operator = tl.pop(0).token

		return cls(operator, lineno=lineno, offset=offset)

class ASTUnaryOperatorNode(ASTOperatorNode):
	@classmethod
	def build(cls, tl):
		operator = super().build(tl)
		if (not isinstance(operator.operator, UnaryOperator)): raise SlSyntaxExpectedError('UnaryOperator', operator)
		operator.operator = UnaryOperator(operator.operator)
		return operator

class ASTBinaryOperatorNode(ASTOperatorNode):
	@classmethod
	def build(cls, tl):
		operator = super().build(tl)
		if (not isinstance(operator.operator, BinaryOperator)): raise SlSyntaxExpectedError('BinaryOperator', operator)
		operator.operator = BinaryOperator(operator.operator)
		return operator

class ASTSpecialNode(ASTTokenNode):
	special: ...

	def __init__(self, special, **kwargs):
		self.special = special
		super().__init__(**kwargs)

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
	value: ...

	def __init__(self, value, **kwargs):
		super().__init__(**kwargs)
		self.value = value

	def __str__(self):
		return str(self.value)

	@classmethod
	def build(cls, tl, *, fcall=False, attrget=False):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		types = [*allsubclasses(ASTUnaryOperationNode), ASTFunccallNode, ASTItemgetNode, ASTAttrgetNode, ASTIdentifierNode, ASTLambdaNode, ASTLiteralNode, *allsubclasses(ASTLiteralStructNode)]
		if (fcall): types.remove(ASTFunccallNode); types.remove(ASTLambdaNode) # XXX lambda too?
		if (attrget): types.remove(ASTAttrgetNode)
		err = set()
		for i in types:
			tll = tl.copy()
			try: value = i.build(tll, **{'attrget': attrget} if (i in (ASTFunccallNode,)) else {})
			except SlSyntaxExpectedError as ex: err.add(ex); continue
			except SlSyntaxException: continue
			else: tl[:] = tll; break
		else: raise SlSyntaxMultiExpectedError.from_list(err)

		return cls(value, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		if (isinstance(self.value, ASTIdentifierNode)):
			if (self.value.identifier not in ns): raise SlValidationNotDefinedError(self.value, self, scope=ns.scope)
			if (ns.values.get(self.value.identifier) is None): raise SlValidationError(f"{self.value.identifier} is not initialized", self.value, self, scope=ns.scope)

	def optimize(self, ns):
		super().optimize(ns)
		if (isinstance(self.value, ASTIdentifierNode) and ns.values.get(self.value) not in (None, ...)): self.value = ns.values[self.value] if (isinstance(ns.values[self.value], ASTNode)) else ASTLiteralNode(literal_repr(ns.values[self.value]), lineno=self.lineno, offset=self.offset) # TODO FIXME in functions

class ASTItemgetNode(ASTPrimitiveNode):
	value: ...
	key: ...

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
		if ((keysig, self.key) not in valsig.itemget): raise SlValidationError(f"`{valsig}' does not support itemget by key of type `{keysig}'", self.key, self, scope=ns.scope)

class ASTAttrgetNode(ASTPrimitiveNode):
	value: ...
	optype: ...
	attr: ...

	def __init__(self, value, optype, attr, **kwargs):
		super().__init__(**kwargs)
		self.value, self.optype, self.attr = value, optype, attr

	def __str__(self):
		return f"{self.value}{self.optype}{self.attr}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		value = ASTValueNode.build(tl, attrget=True)
		optype = ASTSpecialNode.build(tl)
		if (optype.special not in attrops): raise SlSyntaxExpectedError(f"one of {attrops}", optype)
		attr = ASTIdentifierNode.build(tl)

		return cls(value, optype, attr, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		valsig = Signature.build(self.value, ns)
		if ((self.optype.special, self.attr.identifier) not in valsig.attrops): raise SlValidationError(f"`{valsig}' does not support attribute operation `{self.optype}' with attr `{self.attr}'", self.optype, self, scope=ns.scope)

class ASTExprNode(ASTPrimitiveNode):
	@classmethod
	def build(cls, tl, *, fcall=False, attrget=False):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		for ii, p in enumerate(operators[::-1]):
			tll = tl.copy()
			try: value = ASTBinaryExprNode.build(tll, p)
			except SlSyntaxException: continue
			else: tl[:] = tll; return value

		for i in allsubclasses(ASTUnaryOperationNode):
			tll = tl.copy()
			try: value = i.build(tll)
			except SlSyntaxException: pass
			else: tl[:] = tll; return value

		tll = tl.copy()
		try: value = ASTUnaryExprNode.build(tll)
		except SlSyntaxException: pass
		else: tl[:] = tll; return value

		tll = tl.copy()
		try: value = ASTValueNode.build(tll, fcall=fcall, attrget=attrget)
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
	operator: ...
	value: ...

	def __init__(self, operator, value, **kwargs):
		super().__init__(**kwargs)
		self.operator, self.value = operator, value

	def __str__(self):
		return f"{self.operator}{' ' if (self.operator.operator.isalpha()) else ''}{str(self.value).join('()') if (DEBUG_PRECEDENCE or isinstance(self.value, ASTBinaryExprNode) and operator_precedence(self.value.operator.operator) >= operator_precedence(self.operator.operator)) else self.value}"

	@classmethod
	def build(cls, tl):
		ASTPrimitiveNode.build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		operator = ASTUnaryOperatorNode.build(tl)
		value = ASTExprNode.build(tl)

		return cls(operator, value, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		valsig = Signature.build(self.value, ns)
		op = self.operator.operator
		if (op not in valsig.operators): raise SlValidationError(f"`{valsig}' does not support unary operator `{op}'", self.operator, self, scope=ns.scope)

	def optimize(self, ns):
		super().optimize(ns)
		if (isinstance(self.value, ASTUnaryExprNode)): return self.value.value
		elif (ns.values.get(self.value) not in (None, ...)): return ASTValueNode(ASTLiteralNode(literal_repr(eval(f"{'not' if (self.operator.operator == '!') else self.operator} ({literal_repr(ns.values[self.value])})")), lineno=self.lineno, offset=self.offset), lineno=self.lineno, offset=self.offset)

class ASTBinaryExprNode(ASTExprNode):
	lvalue: ...
	operator: ...
	rvalue: ...

	def __init__(self, lvalue, operator, rvalue, **kwargs):
		super().__init__(**kwargs)
		self.lvalue, self.operator, self.rvalue = lvalue, operator, rvalue

	def __str__(self):
		opp = operator_precedence(self.operator.operator)
		return f"{str(self.lvalue).join('()') if (DEBUG_PRECEDENCE or isinstance(self.lvalue, ASTBinaryExprNode) and operator_precedence(self.lvalue.operator.operator) > opp) else self.lvalue}{str(self.operator).join('  ') if (self.operator.operator not in '+-**/') else self.operator}{str(self.rvalue).join('()') if (DEBUG_PRECEDENCE or isinstance(self.rvalue, ASTBinaryExprNode) and operator_precedence(self.rvalue.operator.operator) > opp) else self.rvalue}"

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
				operator = ASTBinaryOperatorNode.build(tll)
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
		if ((op, rsig) not in lsig.operators): raise SlValidationError(f"`{lsig}' does not support operator `{op}' with operand of type `{rsig}'", self.operator, self, scope=ns.scope)

	def optimize(self, ns):
		super().optimize(ns)
		if (self.operator.operator == '**' and ns.values.get(self.lvalue) == 2 and ns.values.get(self.rvalue) is not ... and (ns.values.get(self.rvalue) or 0) > 0): self.operator.operator, self.lvalue.value = BinaryOperator('<<'), ASTLiteralNode('1', lineno=self.lvalue.value.lineno, offset=self.lvalue.value.offset)
		if (ns.values.get(self.lvalue) not in (None, ...) and ns.values.get(self.rvalue) not in (None, ...) and self.operator.operator != 'to'): return ASTValueNode(ASTLiteralNode(literal_repr(eval(f"({literal_repr(ns.values[self.lvalue])}) {self.operator} ({literal_repr(ns.values[self.rvalue])})")), lineno=self.lineno, offset=self.offset), lineno=self.lineno, offset=self.offset)

class ASTLiteralStructNode(ASTNode): pass

class ASTListNode(ASTLiteralStructNode):
	type: ...
	values: ...

	def __init__(self, type, values, **kwargs):
		super().__init__(**kwargs)
		self.type, self.values = type, values

	def __repr__(self):
		return f"<List of `{self.type}'>"

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
		super().validate(ns)
		typesig = Signature.build(self.type, ns)
		for i in self.values:
			if (Signature.build(i, ns) != typesig): raise SlValidationError(f"List item `{i}' does not match list type `{self.type}'", i, self, scope=ns.scope)

class ASTTupleNode(ASTLiteralStructNode):
	types: ...
	values: ...

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
		super().validate(ns)
		for i in range(len(self.values)):
			if (Signature.build(self.values[i], ns) != Signature.build(self.types[i], ns)): raise SlValidationError(f"Tuple item `{self.values[i]}' does not match its type `{self.types[i]}'", self.values[i], self, scope=ns.scope)

class ASTNonFinalNode(ASTNode): pass

class ASTTypedefNode(ASTNonFinalNode):
	modifiers: ...
	type: ...

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
	type: ...
	name: ...
	modifier: ...
	defvalue: ...

	def __init__(self, type, name, modifier, defvalue, **kwargs):
		super().__init__(**kwargs)
		self.type, self.name, self.modifier, self.defvalue = type, name, modifier, defvalue

	def __str__(self):
		return f"{f'{self.type} ' if (self.type) else ''}{self.name}{self.modifier or ''}{f'={self.defvalue}' if (self.defvalue is not None) else ''}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		type = ASTTypedefNode.build(tl)
		name = ASTIdentifierNode.build(tl)
		modifier = ASTOperatorNode.build(tl) if (tl and tl[0].typename == 'OPERATOR' and tl[0].token in '+**') else ASTSpecialNode.build(tl) if (tl and tl[0].typename == 'SPECIAL' and tl[0].token in '?=') else None
		defvalue = ASTExprNode.build(tl) if (isinstance(modifier, ASTSpecialNode) and modifier.special == '=') else None

		return cls(type, name, modifier, defvalue, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		assert (self.modifier != '=' or self.defvalue is not None)
		if (isinstance(Signature.build(self.type, ns), stdlib.void)): raise SlValidationError(f"Argument cannot have type `{self.type}'", self.type, self, scope=ns.scope)

	@property
	def mandatory(self):
		return not (self.modifier is not None and self.modifier in '?=')

class ASTCallargsNode(ASTNonFinalNode):
	callargs: ...
	starargs: ...

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
				elif (len(tl) >= 2 and tl[1].typename == 'SPECIAL' and tl[1].token in '=:'): break
				else: callargs.append(ASTExprNode.build(tl))
				if (not tl or tl[0].typename != 'SPECIAL' or tl[0].token == ')'): break
				comma = ASTSpecialNode.build(tl)
				if (comma.special != ','): raise SlSyntaxExpectedError("','", comma)

		return cls(callargs, starargs, lineno=lineno, offset=offset)

class ASTCallkwargsNode(ASTNonFinalNode):
	callkwargs: ...
	starkwargs: ...

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
					if (eq.special not in '=:'): raise SlSyntaxExpectedError("'=' or ':'", eq)
					value = ASTExprNode.build(tl)
					callkwargs.append((key, value))
				if (not tl or tl[0].typename != 'SPECIAL' or tl[0].token == ')'): break
				comma = ASTSpecialNode.build(tl)
				if (comma.special != ','): raise SlSyntaxExpectedError("','", comma)

		return cls(callkwargs, starkwargs, lineno=lineno, offset=offset)

class ASTCallableNode(ASTNode):
	def validate(self, ns): # XXX.
		super().validate(ns)
		code_ns = ns.derive(self.code.name)
		if (hasattr(self, 'name')):
			code_ns.define(self, redefine=True)
			code_ns.values[self.name] = ...
		for i in self.argdefs:
			code_ns.define(i, redefine=True)
			code_ns.values[i.name] = ...
		self.code.validate(code_ns)

	def optimize(self, ns):
		super().optimize(ns)
		code_ns = ns.derive(self.code.name)
		for i in self.argdefs:
			code_ns.values[i.name] = ...
		code_ns.values.parent = None # XXX
		self.code.optimize(code_ns)

class ASTFunctionNode(ASTCallableNode):
	def validate(self, ns): # XXX.
		super().validate(ns)
		code_ns = ns.derive(self.code.name)
		rettype = Signature.build(self.type, ns)
		return_nodes = tuple(i.value for i in self.code.nodes if (isinstance(i, ASTKeywordExprNode) and i.keyword.keyword == 'return'))
		if (not return_nodes and rettype != stdlib.void()): raise SlValidationError(f"Not returning value from function with return type `{rettype}'", self.code, self, scope=ns.scope)
		for i in return_nodes:
			fsig = Signature.build(i, code_ns)
			if (rettype == stdlib.void() and fsig != rettype): raise SlValidationError(f"Returning value from function with return type `{rettype}'", i, self, scope=ns.scope)
			if (common_type((fsig, rettype), code_ns) is None): raise SlValidationError(f"Returning value of incompatible type `{fsig}' from function with return type `{rettype}'", i, self, scope=ns.scope)

class ASTLambdaNode(ASTNonFinalNode, ASTFunctionNode):
	argdefs: ...
	type: ...
	code: ...

	def __init__(self, argdefs, type, code, **kwargs):
		super().__init__(**kwargs)
		self.argdefs, self.type, self.code = argdefs, type, code

	def __fsig__(self):
		return f"({S(', ').join(self.argdefs)}) -> {self.type}"

	def __repr__(self):
		return f"<Lambda `{self.__fsig__()} {{...}}' on line {self.lineno}, offset {self.offset}>"

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
			argdef = ASTArgdefNode.build(tl)
			if (argdefs and argdef.defvalue is None and argdefs[-1].defvalue is not None): raise SlSyntaxError(f"Non-default argument {argdef} follows default argument {argdefs[-1]}")
			argdefs.append(argdef)
			if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ','): ASTSpecialNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
		arrow = ASTSpecialNode.build(tl)
		if (arrow.special != '->'): raise SlSyntaxExpectedError("'->'", arrow)
		type = ASTTypedefNode.build(tl)
		if (tl and (tl[0].typename != 'SPECIAL' or tl[0].token not in (*'={',))): raise SlSyntaxExpectedError("'=' or '{'", tl[0])
		cdef = ASTSpecialNode.build(tl)
		if (cdef.special != '='): raise SlSyntaxExpectedError('=', cdef)
		code = ASTCodeNode([ASTKeywordExprNode(ASTKeywordNode('return', lineno=lineno, offset=offset), ASTExprNode.build(tl), lineno=lineno, offset=offset)], name='<lambda>', lineno=lineno, offset=offset)

		return cls(argdefs, type, code, lineno=lineno, offset=offset)

class ASTBlockNode(ASTNonFinalNode):
	code: ...

	def __init__(self, code, **kwargs):
		super().__init__(**kwargs)
		self.code = code

	def __str__(self):
		return str(self.code) if (len(self.code.nodes) > 1) else str(self.code)[1:-1].strip()

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		if (tl[0].typename == 'SPECIAL' and tl[0].token == '{'): code = (yield from ASTCodeNode.build(tl, name='<block>'))
		else:
			yield '<expr>'
			expr = ASTExprNode.build(tl)
			code = ASTCodeNode([expr], name='', lineno=expr.lineno, offset=expr.offset)

		return cls(code, lineno=lineno, offset=offset)

	def validate(self, ns):
		super().validate(ns)
		self.code.validate(ns)

	def optimize(self, ns):
		super().optimize(ns)
		self.code.optimize(ns)

class ASTFinalNode(ASTNode): pass

class ASTDefinitionNode(ASTNode):
	def validate(self, ns): # XXX.
		Signature.build(self, ns)
		ns.define(self)
		super().validate(ns)

class ASTFuncdefNode(ASTFinalNode, ASTDefinitionNode, ASTFunctionNode):
	type: ...
	name: ...
	argdefs: ...
	code: ...

	def __init__(self, type, name, argdefs, code, **kwargs):
		super().__init__(**kwargs)
		self.type, self.name, self.argdefs, self.code = type, name, argdefs, code

	def __fsig__(self):
		return f"{self.type or 'def'} {self.name}({S(', ').join(self.argdefs)})"

	def __repr__(self):
		return f"<Funcdef `{self.__fsig__()} {{...}}' on line {self.lineno}, offset {self.offset}>"

	def __str__(self):
		isexpr = (len(self.code.nodes) == 1 and isinstance(self.code.nodes[0], ASTKeywordExprNode) and self.code.nodes[0].keyword.keyword == 'return')
		r = f"{self.__fsig__()} {f'= {self.code.nodes[0].value}' if (isexpr) else self.code}"
		return r

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
			if (argdefs and argdef.defvalue is None and argdefs[-1].defvalue is not None): raise SlSyntaxError(f"Non-default argument {argdef} follows default argument {argdefs[-1]}")
			argdefs.append(argdef)
			if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ','): ASTSpecialNode.build(tl)
		parenthesis = ASTSpecialNode.build(tl)
		if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
		if (not tl): raise SlSyntaxExpectedError("'=' or '{'", lineno=lineno, offset=-1)
		if (tl[0].typename != 'SPECIAL' or tl[0].token not in (*'={',)): raise SlSyntaxExpectedError("'=' or '{'", tl[0])
		if (tl[0].token == '{'): code = (yield from ASTCodeNode.build(tl, name=name.identifier))
		else:
			cdef = ASTSpecialNode.build(tl)
			assert (cdef.special == '=')
			yield name.identifier
			code = ASTCodeNode([ASTKeywordExprNode(ASTKeywordNode('return', lineno=lineno, offset=offset), ASTExprNode.build(tl), lineno=lineno, offset=offset)], name=name.identifier, lineno=lineno, offset=offset)

		return cls(type, name, argdefs, code, lineno=lineno, offset=offset)

class ASTClassdefNode(ASTFinalNode, ASTDefinitionNode, ASTCallableNode):
	name: ...
	bases: ...
	code: ...
	type: ...

	argdefs = ()

	def __init__(self, name, bases, code, **kwargs):
		super().__init__(**kwargs)
		self.name, self.bases, self.code = name, bases, code
		self.type = ASTTypedefNode([], self.name, lineno=self.lineno, offset=self.offset)

	def __repr__(self):
		return f"<Classdef `{self.name}' on line {self.lineno}, offset {self.offset}>"

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
		if (not tl or tl[0].typename != 'SPECIAL' or tl[0].token != '{'): raise SlSyntaxExpectedError("'{'", tl[0])
		code = (yield from ASTCodeNode.build(tl, name=name.identifier))

		return cls(name, bases, code, lineno=lineno, offset=offset)

class ASTKeywordExprNode(ASTFinalNode):
	keyword: ...
	value: ...

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
		elif (keyword.keyword == 'delete'): value = ASTIdentifierNode.build(tl)
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
					ex.srclines = src.split('\n')
					raise SlValidationError(f"Error importing {self.value}", self.value, self, scope=ns.scope) from ex
			if (name != '*'): ns.define(ASTIdentifierNode(name, lineno=self.value.lineno, offset=self.value.offset)) # TODO object
			else: ns.signatures.update(module_ns.signatures) # TODO?
		elif (self.keyword.keyword == 'delete'):
			if (self.value.identifier not in ns): raise SlValidationNotDefinedError(self.value, self, scope=ns.scope)
			ns.delete(self.value)
		super().validate(ns)

class ASTKeywordDefNode(ASTFinalNode):
	keyword: ...
	name: ...
	argdefs: ...
	code: ...

	def __init__(self, keyword, name, argdefs, code, **kwargs):
		super().__init__(**kwargs)
		self.keyword, self.name, self.argdefs, self.code = keyword, name, argdefs, code
		if (self.name is None): self.name = ASTIdentifierNode(self.code.name, lineno=self.lineno, offset=self.offset)

	def __repr__(self):
		return f"<KeywordDef `{self.name}' on line {self.lineno}, offset {self.offset}>"

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
				if (argdefs and argdef.defvalue is None and argdefs[-1].defvalue is not None): raise SlSyntaxError(f"Non-default argument {argdef} follows default argument {argdefs[-1]}")
				argdefs.append(argdef)
				if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == ','): ASTSpecialNode.build(tl)
			parenthesis = ASTSpecialNode.build(tl)
			if (parenthesis.special != ')'): raise SlSyntaxExpectedError("')'", parenthesis)
		if (not tl or tl[0].typename != 'SPECIAL' or tl[0].token != '{'): raise SlSyntaxExpectedError('{', tl[0])
		code = (yield from ASTCodeNode.build(tl, name=f"<{keyword}>"))

		return cls(keyword, name, argdefs, code, lineno=lineno, offset=offset)

	def validate(self, ns): # XXX.
		super().validate(ns)
		code_ns = ns.derive(self.code.name)
		if (isinstance(self.keyword.keyword, DefArgsKeyword)):
			for i in self.argdefs:
				code_ns.define(i, redefine=True)
				code_ns.values[i.name] = ...
		self.code.validate(code_ns)

	def optimize(self, ns):
		super().optimize(ns)
		code_ns = ns.derive(self.code.name)
		if (isinstance(self.keyword.keyword, DefArgsKeyword)):
			for i in self.argdefs:
				code_ns.values[i.name] = ...
		self.code.optimize(code_ns)

class ASTAssignvalNode(ASTNode):
	def validate(self, ns):
		super().validate(ns)
		if (self.name.identifier not in ns): raise SlValidationNotDefinedError(self.name, self, scope=ns.scope)
		varsig = Signature.build(self.name, ns)
		if (self.value is not None):
			valsig = Signature.build(self.value, ns)
			if (valsig != varsig and varsig != valsig): raise SlValidationError(f"Assignment of value `{self.value}' of type `{valsig}' to variable `{self.name}' of type `{varsig}'", self.value, self, scope=ns.scope)
		varsig.flags.modified = True
		ns.values[self.name] = self.value if (not varsig.modifiers.volatile) else ...

	def optimize(self, ns):
		super().optimize(ns)
		varsig = Signature.build(self.name, ns)
		varsig.flags.modified = True
		ns.values[self.name] = self.value if (not varsig.modifiers.volatile) else ...

class ASTVardefNode(ASTFinalNode, ASTAssignvalNode, ASTDefinitionNode):
	type: ...
	name: ...
	value: ...

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

	def validate(self, ns): # XXX.
		if (self.type.type.identifier == 'auto'): self.type.type.identifier = Signature.build(self.value, ns).typename
		self.flags.optimized_out = False
		super().validate(ns)
		if (self.value is not None):
			varsig = Signature.build(self.name, ns)
			varsig.flags.modified = False

	def optimize(self, ns):
		super().optimize(ns)
		varsig = Signature.build(self.name, ns)
		self.flags.optimized_out = False
		if (self.value is not None): varsig.flags.modified = False
		#if (not varsig.flags.modified and not varsig.modifiers.volatile): # TODO
		#	self.value = None
		#	self.flags.optimized_out = True

class ASTAssignmentNode(ASTFinalNode, ASTAssignvalNode):
	name: ...
	isattr: ...
	assignment: ...
	inplace_operator: ...
	value: ...

	def __init__(self, name, isattr, assignment, inplace_operator, value, **kwargs):
		super().__init__(**kwargs)
		self.name, self.isattr, self.assignment, self.inplace_operator, self.value = name, isattr, assignment, inplace_operator, value

	def __str__(self):
		return f"{'.'*self.isattr}{self.name} {self.inplace_operator or ''}{self.assignment} {self.value}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		isattr = False
		if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == '.'): ASTSpecialNode.build(tl); isattr = True
		name = ASTIdentifierNode.build(tl)
		inplace_operator = None
		if (tl and tl[0].typename == 'OPERATOR'): inplace_operator = ASTBinaryOperatorNode.build(tl)
		assignment = ASTSpecialNode.build(tl)
		if (assignment.special not in ('=', ':=')): raise SlSyntaxExpectedError('assignment', assignment)
		value = ASTExprNode.build(tl)

		return cls(name, isattr, assignment, inplace_operator, value, lineno=lineno, offset=offset)

	def validate(self, ns): # XXX.
		valsig = Signature.build(self.value, ns)
		if (self.assignment.special == ':='): ns.define(self.name, valsig, redefine=True)
		if (self.isattr): return # TODO
		super().validate(ns)
		varsig = Signature.build(self.name, ns)
		if (varsig.modifiers.const): raise SlValidationError(f"Assignment to const `{self.name}'", self.name, self, scope=ns.scope)
		if (self.inplace_operator is not None): ns.values[self.name] = ... # TODO folding

	def optimize(self, ns):
		super().optimize(ns)
		if (self.inplace_operator is not None): ns.values[self.name] = ... # TODO folding

class ASTUnpackAssignmentNode(ASTFinalNode, ASTAssignvalNode):
	names: ...
	assignment: ...
	inplace_operator: ...
	value: ...

	def __init__(self, names, assignment, inplace_operator, value, **kwargs):
		super().__init__(**kwargs)
		self.names, self.assignment, self.inplace_operator, self.value = names, assignment, inplace_operator, value

	def __str__(self):
		return f"{S(', ').join(self.names)} {self.inplace_operator or ''}{self.assignment} {self.value}"

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

	def validate(self, ns): # XXX.
		valsig = Signature.build(self.value, ns)
		if (self.assignment.special == ':='):
			for name, type in zip(self.names, valsig.valtypes):
				ns.define(name, type, redefine=True)
		ASTNode.validate(self, ns)
		for name, (ii, valtype) in zip(self.names, enumerate(valsig.valtypes)):
			if (name.identifier not in ns): raise SlValidationNotDefinedError(name, self, scope=ns.scope)
			varsig = Signature.build(name, ns)
			if (varsig.modifiers.const): raise SlValidationError(f"Assignment to const `{name}'", name, self, scope=ns.scope)
			if (varsig != valtype): raise SlValidationError(f"Assignment of `{valtype}' to variable {name} of type {varsig}", self.value.value.values[ii] if (isinstance(self.value, ASTValueNode) and hasattr(self.value.value, 'values')) else name, self, scope=ns.scope)
			varsig.flags.modified = True
			if (self.inplace_operator is not None): ns.values[name] = ... # TODO folding

	def optimize(self, ns):
		super().optimize(ns)
		if (self.inplace_operator is not None): ns.values[self.name] = ... # TODO folding

class ASTUnaryOperationNode(ASTPrimitiveNode):
	name: ...
	isattr: ...
	unary_operator: ...

	def __init__(self, name, isattr, unary_operator, **kwargs):
		super().__init__(**kwargs)
		self.name, self.isattr, self.unary_operator = name, isattr, unary_operator

	def validate(self, ns):
		if (self.isattr): return # TODO
		super().validate(ns)
		varsig = Signature.build(self.name, ns)
		if (varsig.modifiers.const): raise SlValidationError(f"Unary operation `{self.unary_operator}' on const `{self.name}'", self.name, self, scope=ns.scope)

class ASTUnaryPreOperationNode(ASTUnaryOperationNode, ASTFinalNode):
	def __str__(self):
		return f"{self.unary_operator}{'.'*self.isattr}{self.name}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		unary_operator = ASTUnaryOperatorNode.build(tl)
		if (unary_operator.operator not in unaryops): raise SlSyntaxExpectedError('Unary operation', unary_operator)
		isattr = False
		if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == '.'): ASTSpecialNode.build(tl); isattr = True
		name = ASTIdentifierNode.build(tl)

		return cls(name, isattr, unary_operator, lineno=lineno, offset=offset)

class ASTUnaryPostOperationNode(ASTUnaryOperationNode, ASTFinalNode):
	def __str__(self):
		return f"{'.'*self.isattr}{self.name}{self.unary_operator}"

	@classmethod
	def build(cls, tl):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		isattr = False
		if (tl and tl[0].typename == 'SPECIAL' and tl[0].token == '.'): ASTSpecialNode.build(tl); isattr = True
		name = ASTIdentifierNode.build(tl)
		unary_operator = ASTUnaryOperatorNode.build(tl)
		if (unary_operator.operator not in unaryops): raise SlSyntaxExpectedError('Unary operation', unary_operator)

		return cls(name, isattr, unary_operator, lineno=lineno, offset=offset)

class ASTAttrsetNode(ASTFinalNode):
	value: ...
	assignment: ...

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
		#if ((self.optype.special, self.attr.identifier) not in valsig.attrops): raise SlValidationError(f"`{valsig}' does not support attribute operation `{self.optype}' with attr `{self.attr}'", self.optype, self, scope=ns.scope)

class ASTFunccallNode(ASTFinalNode):
	callable: ...
	callargs: ...
	callkwargs: ...

	def __init__(self, callable, callargs, callkwargs, **kwargs):
		super().__init__(**kwargs)
		self.callable, self.callargs, self.callkwargs = callable, callargs, callkwargs

	def __str__(self):
		return f"{str(self.callable).join('()') if (isinstance(self.callable, ASTValueNode) and isinstance(self.callable.value, (ASTFunccallNode, ASTLambdaNode))) else self.callable}({self.callargs}{', ' if (str(self.callargs) and str(self.callkwargs)) else ''}{self.callkwargs})"

	@classmethod
	def build(cls, tl, *, attrget=False):
		super().build(tl)
		lineno, offset = tl[0].lineno, tl[0].offset

		callable = ASTExprNode.build(tl, fcall=True, attrget=attrget)
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
		if (not isinstance(fsig, Callable)): raise SlValidationError(f"`{self.callable}' of type `{fsig}' is not callable", self.callable, self, scope=ns.scope)
		callarguments = CallArguments.build(self, ns)
		if (fsig.compatible_call(callarguments, ns) is None): raise SlValidationError(f"Parameters `({callarguments})' don't match any of `{self.callable}' signatures:\n{S(fsig.callargssigstr).indent()}\n", self, scope=ns.scope)

	def optimize(self, ns):
		fsig = Signature.build(self.callable, ns)
		if (fsig.code is not None):
			code_ns = ns.derive(fsig.code.name)
			fsig.code.validate(code_ns)
		super().optimize(ns)

class ASTConditionalNode(ASTFinalNode):
	condition: ...
	code: ...

	def __init__(self, condition, code, **kwargs):
		super().__init__(**kwargs)
		self.condition, self.code = condition, code

	def __repr__(self):
		return f"<Conditional if `{self.condition}' on line {self.lineno}, offset {self.offset}>"

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
	name: ...
	iterable: ...
	code: ...

	def __init__(self, name, iterable, code, **kwargs):
		super().__init__(**kwargs)
		self.name, self.iterable, self.code = name, iterable, code

	def __repr__(self):
		return f"<ForLoop `{self.name}' in `{self.iterable}' on line {self.lineno}, offset {self.offset}>"

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
		# TODO: validate iterability
		ns.define(self.name, Signature.build(self.iterable, ns).valtype)
		ns.weaken(self.name)
		ns.values[self.name] = ...
		super().validate(ns)

	def optimize(self, ns):
		self.code.validate(ns)
		super().optimize(ns)

class ASTWhileLoopNode(ASTFinalNode):
	code: ...  # needs to be validated/optimized first (case when the condition is modified from loop body)
	condition: ...

	def __init__(self, condition, code, **kwargs):
		super().__init__(**kwargs)
		self.condition, self.code = condition, code

	def __repr__(self):
		return f"<WhileLoop while `{self.condition}' on line {self.lineno}, offset {self.offset}>"

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

	#def validate(self, ns):
	#	Signature.build(self.condition, ns).modifiers.volatile = True
	#	super().validate(ns)

	def optimize(self, ns):
		self.code.validate(ns)
		super().optimize(ns)

class ASTElseClauseNode(ASTFinalNode):
	code: ...

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
					except StopIteration as ex: code_stack.pop(); r = ex.value
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
			except SlSyntaxNoToken: err.add(SlSyntaxExpectedMoreTokensError(i.__name__[3:-4], lineno=lineno, offset=-1))
			except SlSyntaxMultiExpectedError as ex: pass#err.add(ex) # TODO FIXME
			except SlSyntaxExpectedError as ex: ex.usage = i.__name__[3:-4]; err.add(ex)
			else:
				code_stack[-1][0].send(r)
				err.clear()
				break
		else:
			if (len(code_stack) > 1 and tl and tl[0].typename == 'SPECIAL' and tl[0].token == '}'):
				if (tl[1:]): code.insert(ii+1, tl[1:])
				try: next(code_stack.pop()[0])
				except StopIteration as ex: code_stack[-1][0].send(ex.value); err.clear()
				else: raise WTFException()
			elif (not err): raise SlSyntaxError("Unknown structure", lineno=lineno, offset=offset, length=0, scope='.'.join(i[1] for i in code_stack if i[1]))

		if (err): raise SlSyntaxMultiExpectedError.from_list(err, scope='.'.join(i[1] for i in code_stack if i[1]) if (code_stack[0][1] is not None) else None)

	if (len(code_stack) > 1): raise SlSyntaxExpectedMoreTokensError(code_stack[-1][1], lineno=lineno)

	assert (len(code_stack) == 1)
	try: next(code_stack.pop()[0])
	except StopIteration as ex: return ex.value

def walk_ast_nodes(node):
	if (isiterable(node) and not isinstance(node, str)):
		for i in node: yield from walk_ast_nodes(i)
	if (not isinstance(node, ASTNode)): return
	yield node
	for i in allslots(node): yield from walk_ast_nodes(getattr(node, i))

class _SignatureBase(ABCSlots): pass
class Signature(_SignatureBase):
	operators = {}
	typename: ...
	modifiers: paramset
	flags: paramset

	@init(typename=..., modifiers=..., flags=...)
	def __init__(self):
		super().__init__()

	@property
	def __reprname__(self):
		return self.__class__.__name__

	def __repr__(self):
		return f"<{self.__reprname__} `{self.name}'>"

	def __str__(self):
		return self.name

	def __eq__(self, x):
		return (x is not None and self.typename == x.typename)

	def __hash__(self):
		return hash(tuple(getattr(self, i) for i in allslots(self)))

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
		#if (x.value is not None): ns.values[x.name] = x.value if (False and not r.modifiers.volatile and r.modifiers.const) else ... # XXX TODO (see False)
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
		#return Collection(keytype=stdlib.int(), valtype=Signature.build(x.type, ns))
		return stdlib.list(valtype=Signature.build(x.type, ns))

	@classmethod
	@dispatch
	def build(cls, x: ASTTupleNode, ns):
		#return MultiCollection(keytype=stdlib.int(), valtypes=tuple(Signature.build(t if (t is not None) else v, ns) for t, v in zip(x.types, x.values)))
		return stdlib.tuple(valtypes=tuple(Signature.build(t if (t is not None) else v, ns) for t, v in zip(x.types, x.values)))

	@classmethod
	@dispatch
	def build(cls, x: ASTFunccallNode, ns):
		callarguments = CallArguments.build(x, ns)
		return cls.build(x.callable, ns).compatible_call(callarguments, ns)[1]

	@classmethod
	@dispatch
	def build(cls, x: ASTLambdaNode, ns):
		return Lambda.build(x, ns)

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
	def build(cls, x: ASTUnaryOperationNode, ns):
		return cls.build(x.name, ns)

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

class Callable(Signature):
	call: ...
	code: ...

	def __init__(self, *, code=None, **kwargs):
		super().__init__(**kwargs)
		self.code = code

	def compatible_call(self, callarguments, ns):
		try: return first((k, v) for k, v in self.call.items() if callarguments.compatible(k))
		except StopIteration: return None

	@abc.abstractproperty
	def callargssigstr(self):
		pass

class Function(Callable):
	typename = 'function'
	name: ...

	def __init__(self, *, name, code=None, **kwargs):
		super().__init__(**kwargs)
		self.name, self.code = name, code
		self.call = listmap()

	@property
	def callargssigstr(self):
		return '\n'.join(f"{ret.typename} {self.name}({S(', ').join(args)})" for args, ret in self.call.items())

	@staticitemget
	def attrops(optype, attr):
		if (optype == '.'):
			if (attr == 'map'): return stdlib._map()
		raise KeyError()

	@classmethod
	@dispatch
	def build(cls, x: ASTFuncdefNode, ns, *, redefine=False):
		name = x.name.identifier
		if (name not in ns): fsig = ns.signatures[name] = cls(name=name, code=x.code)
		else: fsig = ns.signatures[name]

		argdefs = tuple(x.argdefs)
		if (not redefine and argdefs in fsig.call and name not in ns.weak): raise SlValidationRedefinedError(x.name, x.__fsig__(), scope=ns.scope)
		if (x.type.type.identifier == 'auto'): # XXX@ TODO FIXME
			code_ns = ns.derive(x.code.name)
			rettype = common_type((i.value for i in x.code.nodes if (isinstance(i, ASTKeywordExprNode) and i.keyword.keyword == 'return')), code_ns) or stdlib.void()
		else: rettype = Signature.build(x.type, ns)
		fsig.call[argdefs] = rettype
		dlog(fsig.call, x)
		return fsig

class Lambda(Callable):
	typename = 'lambda'

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.call = listmap()

	@property
	def callargssigstr(self):
		return '\n'.join(f"({S(', ').join(args)}) -> {ret.typename}" for args, ret in self.call.items())

	@staticitemget
	def attrops(optype, attr):
		if (optype == '.'):
			if (attr == 'map'): return stdlib._map()
		raise KeyError()

	@classmethod
	@dispatch
	def build(cls, x: ASTLambdaNode, ns, *, redefine=False):
		fsig = cls(code=x.code)
		argdefs = tuple(x.argdefs)
		if (x.type.type.identifier == 'auto'):
			code_ns = ns.derive(x.code.name)
			rettype = common_type((i.value for i in x.code.nodes if (isinstance(i, ASTKeywordExprNode) and i.keyword.keyword == 'return')), code_ns) or stdlib.void()
		else: rettype = Signature.build(x.type, ns)
		fsig.call[argdefs] = rettype
		return fsig

class KeywordDef(Callable):
	typename = 'keyworddef'
	name: ...

	def __init__(self, *, name, **kwargs):
		super().__init__(**kwargs)
		self.name = name
		self.call = listmap()

	@property
	def callargssigstr(self):
		return '\n'.join(f"{self.name}({S(', ').join(args)})" for args, ret in self.call.items())

	@classmethod
	@dispatch
	def build(cls, x: ASTKeywordDefNode, ns, *, redefine=False):
		name = x.name.identifier
		if (name not in ns): fsig = ns.signatures[name] = cls(name=name, code=x.code)
		else: fsig = ns.signatures[name]

		argdefs = tuple(x.argdefs) if (x.argdefs is not None) else ()
		if (not redefine and argdefs in fsig.call and name not in ns.weak): raise SlValidationRedefinedError(x.name, fsig.call[argdefs], scope=ns.scope)
		fsig.call[argdefs] = stdlib.void
		return fsig

class Object(Signature):
	typename = 'Object'

class Collection(Object):
	typename = 'collection'
	keytype: ...
	valtype: ...

	def __init__(self, *, keytype, valtype, **kwargs):
		super().__init__(**kwargs)
		self.keytype, self.valtype = keytype, valtype

	def __repr__(self):
		return f"<Collection of `{self.valtype.typename}' by `{self.keytype}'>"

	@property
	def typename(self):
		return self.valtype.typename
	@typename.setter
	def typename(self, x):
		pass

	@itemget
	@instantiate
	def itemget(self, keysig, key):
		if (keysig == self.keytype): return self.valtype
		raise KeyError()

class MultiCollection(Collection):
	typename = 'MultiCollection'
	valtypes: ...

	def __init__(self, *, keytype, valtypes):
		super().__init__(keytype=keytype, valtype=stdlib.Any)
		self.valtypes = valtypes

	@itemget
	@instantiate
	def itemget(self, keysig, key):
		if (keysig == self.keytype): return self.valtypes[int(key)]
		raise KeyError()

class Class(Object, Callable):
	typename = 'class'
	name: ...
	scope: ...
	constructor: ...

	def __init__(self, *, name, scope, **kwargs):
		super().__init__(**kwargs)
		self.name, self.scope = name, scope
		self.constructor = listmap()

	def __str__(self):
		return self.name

	def compatible_call(self, callarguments, ns):
		try: return first((k, v) for k, v in self.constructor.items() if callarguments.compatible(k))
		except StopIteration: return None

	@property
	def callargssigstr(self):
		return '\n'.join(f"{self.name}({S(', ').join(args)})" for args, ret in self.constructor.items())

	@itemget
	def call(self, argdefs):
		return self.constructor[argdefs]

	@itemget
	def attrops(self, optype, attr):
		if (optype == '.'):
			return self.scope.signatures[attr]
		raise KeyError()

	@classmethod
	@dispatch
	def build(cls, x: ASTClassdefNode, ns, *, redefine=False):
		name = x.name.identifier
		#if (not redefine and name in ns and name not in ns.weak): raise SlValidationRedefinedError(x.name, ns.signatures[name], scope=ns.scope)
		fsig = ns.signatures[name] = cls(name=name, scope=ns.derive(x.code.name), code=x.code)

		for i in x.code.nodes:
			if (isinstance(i, ASTKeywordDefNode) and i.keyword.keyword == 'constr'):
				argdefs = tuple(i.argdefs) if (i.argdefs is not None) else ()
				if (not redefine and argdefs in fsig.constructor and name not in ns.weak): raise SlValidationRedefinedError(x.name, fsig.constructor[argdefs], scope=ns.scope)
				fsig.constructor[argdefs] = fsig

		return fsig

class CallArguments(Slots):
	args: ...
	starargs: ...
	kwargs: ...
	starkwargs: ...
	ns: ...

	@init_defaults
	@autocast
	def __init__(self, *, args: tuple, starargs: tuple, kwargs: tuple, starkwargs: tuple, ns):
		self.args, self.starargs, self.kwargs, self.starkwargs, self.ns = args, starargs, kwargs, starkwargs, ns

	def __str__(self):
		return S(', ').join((*self.args, *('*'+i for i in self.starargs), *(f"{v} {k}" for k, v in self.kwargs), *('**'+i for i in self.starkwargs)))

	def __eq__(self, x):
		return all(getattr(self, i) == getattr(x, i) for i in allslots(self))

	@dispatch
	def compatible(self, x: typing.Iterable[ASTArgdefNode]):
		# type(x[i]) = ASTArgdefNode
		# type(args[i]) = ASTExprNode
		# type(starargs[i]) = ASTExprNode
		# type(kwargs[i]) = tuple(ASTIdentifierNode, ASTExprNode)
		# type(starkwargs[i]) = ASTExprNode

		x = Slist(x)
		args, starargs, kwargs, starkwargs = list(self.args), list(self.starargs), dict(self.kwargs), list(self.starkwargs)
		has_mandatory_left = bool(x)
		optional_left = max(0, len(args) - len(tuple(i for i in x if i.mandatory)))
		to_fill_optionals = list()

		#dlog(1, x, args)

		while (x):
			x.discard()
			for ii, arg in enumerate(x):  # type, name, modifier, defvalue
				if (not arg.mandatory):
					if (has_mandatory_left):
						if (len(args) > optional_left): to_fill_optionals.append(args.pop(0))
						continue
					elif (to_fill_optionals):
						args += to_fill_optionals
						to_fill_optionals.clear()

				if (args):
					posarg = args.pop(0)
					sig = Signature.build(posarg, self.ns)
					if (common_type((arg.type, sig), self.ns) is None): return False
					x.to_discard(ii)
					continue

				if (starargs):
					stararg = starargs.pop(0)
					sig = Signature.build(stararg, self.ns)
					#if (common_type((arg.type, *stararg.type), self.ns) is not None): return False # TODO: typecheck!
					x.to_discard(ii)
					continue

				if (kwargs):
					continue

				if (starkwargs):
					continue

				# XXX!

				break
			else: has_mandatory_left = False; continue
			x.discard()
			break

		return not any((has_mandatory_left, args, starargs, kwargs, starkwargs))

	#@property # XXX needed? | FIXME star[kw]args
	#def nargs(self):
	#	return len(self.args) + sum(i.length for i in self.starargs) + len(self.kwargs) + sum(i.length for i in self.starkwargs)
	#	#return sum(len(getattr(self, i)) for i in allslots(self))

	@classmethod
	@dispatch
	def build(cls, x: ASTFunccallNode, ns):
		return cls(args=x.callargs.callargs,
			   starargs=x.callargs.starargs,
			   kwargs=x.callkwargs.callkwargs,
			   starkwargs=x.callkwargs.starkwargs,
			   ns=ns)

class Namespace(Slots):
	class _Signatures(Slots):
		signatures: dict
		parent: None

		@init(signatures=..., parent=...)
		def __init__(self):
			super().__init__()
			assert (self.parent not in (self, self.signatures))
			if (isinstance(self.parent, Namespace._Signatures)): assert (self.parent.parent not in (self, self.signatures))

		def __iter__(self):
			return iter(self.keys())

		@dispatch
		def __contains__(self, x: str):
			return x in self.signatures or (self.parent is not None and x in self.parent)

		@dispatch
		def __getitem__(self, x: str):
			try: return self.signatures[x]
			except KeyError:
				if (self.parent is not None):
					try: return self.parent[x]
					except KeyError: pass
				raise

		@dispatch
		def __setitem__(self, k: str, v: Signature):
			self.signatures[k] = v

		@dispatch
		def __delitem__(self, x: ASTIdentifierNode):
			del self[x.identifier]

		@dispatch
		def __delitem__(self, x: str):
			del self.signatures[x]

		def items(self):
			return self.signatures.items() if (self.parent is None) else {**self.parent, **self.signatures}.items()

		def keys(self):
			return self.signatures.keys() if (self.parent is None) else (*self.signatures.keys(), *self.parent.keys())

		def copy(self):
			return self.__class__(signatures=self.signatures.copy(), parent=self.parent)

	class _Values(Slots):
		values: dict
		parent: None

		@init(values=..., parent=...)
		def __init__(self):
			super().__init__()
			assert (self.parent not in (self, self.values))
			if (isinstance(self.parent, Namespace._Values)): assert (self.parent.parent not in (self, self.values))

		@dispatch
		def __getitem__(self, x: ASTLiteralNode):
			return eval_literal(x)

		@dispatch
		def __getitem__(self, x: ASTValueNode):
			return self[x.value]

		@dispatch
		def __getitem__(self, x: ASTIdentifierNode):
			return self[x.identifier]

		@dispatch
		def __getitem__(self, x: str):
			try: return self.values[x]
			except KeyError:
				if (self.parent is not None):
					try: return self.parent[x]
					except KeyError: pass
					#except RecursionError: pass # TODO FIXME XXX! ??? (tests/fib.sl)
				raise

		@dispatch
		def __setitem__(self, k, v: ASTValueNode):
			self[k] = v.value

		@dispatch
		def __setitem__(self, x: ASTIdentifierNode, v: ASTLiteralNode):
			self[x.identifier] = eval_literal(v)

		@dispatch
		def __setitem__(self, x: ASTIdentifierNode, v):
			self[x.identifier] = v

		@dispatch
		def __setitem__(self, k: str, v):
			if (self.parent is None or k in self.values): self.values[k] = v
			else: self.parent[k] = v

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
			except KeyError: return None

		def items(self):
			return self.values.items() if (self.parent is None) else {**self.parent, **self.values}.items()

		def copy(self):
			return self.__class__(values=self.values.copy(), parent=self.parent)

	scope: ...
	signatures: lambda: Namespace._Signatures(parent=builtin_names)
	values: lambda: Namespace._Values(parent={i: ... for i in builtin_names})
	weak: set
	refcount: lambda: Sdict(int)
	warnclasses: paramset
	flags: lambda: Sdict(paramset)
	olevel: int

	@init(signatures=..., values=..., weak=..., refcount=..., warnclasses=..., flags=..., olevel=...)
	def __init__(self, scope):
		self.scope = scope

	def __repr__(self):
		return f"<Namespace of scope `{self.scope}'>"

	def __contains__(self, x):
		return x in self.signatures

	@lrucachedfunction
	def derive(self, scope, *, append=True):
		assert (type(scope) is str)
		#return Namespace(signatures=self.signatures.copy(), values=self._Values(parent=self.values), weak=self.weak, scope=self.scope+'.'+scope if (append) else scope)
		return Namespace(signatures=self.signatures, values=self._Values(parent=self.values), weak=self.weak | set(self.signatures), scope=self.scope+'.'+scope if (append) else scope) # XXX.
		#return Namespace(signatures=self._Signatures(parent=self.signatures), values=self._Values(parent=self.values), weak=self.weak | set(self.signatures), scope=self.scope+'.'+scope if (append) else scope)

	@dispatch
	def define(self, x: ASTFuncdefNode):
		self.define(x, redefine=True)
		self.values[x.name] = ...

	@dispatch
	def define(self, x: lambda x: hasattr(x, 'name'), sig=None, *, redefine=False):
		if (redefine):
			try: del self.signatures[x.name]
			except KeyError: pass
			try: del self.values[x.name]
			except KeyError: pass
		self.define(x.name, sig if (sig is not None) else Signature.build(x, self), redefine=redefine)

	@dispatch
	def define(self, x: ASTIdentifierNode, sig, *, redefine=False):
		if (not redefine and x.identifier in self and x.identifier not in self.weak): raise SlValidationRedefinedError(x, self.signatures[x.identifier], scope=self.scope)
		self.signatures[x.identifier] = sig
		self.values.values[x.identifier] = None
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
	return ast.validate(ns)

class SlNodeException(Exception, ABCSlots):
	node: ...
	ctxnode: ...
	srclines: ...
	scope: ...

	def __init__(self, node, ctxnode=None, *, srclines=(), scope=None):
		self.node, self.ctxnode, self.srclines, self.scope = node, ctxnode if (ctxnode is not None) else node, srclines, scope

	def __str__(self):
		line = self.srclines[self.lineno-1].partition('\n')[0].rstrip() if (self.srclines) else ''
		l = lstripcount(line)[0]

		ctx = self.ctxnode
		minlineno = min((getattr(ctx, i).lineno for i in allslots(ctx) if getattr(getattr(ctx, i), 'lineno', 0) > 0), default=min(ctx.lineno, self.lineno))
		maxlineno = max((getattr(ctx, i).lineno for i in allslots(ctx) if getattr(getattr(ctx, i), 'lineno', 0) > 0), default=max(ctx.lineno, self.lineno))
		minoffset = min((getattr(ctx, i).offset for i in allslots(ctx) if getattr(getattr(ctx, i), 'offset', -1) >= 0 and getattr(getattr(ctx, i), 'lineno') == self.lineno), default=self.node.offset)
		maxoffsetlength, maxoffset = max(((getattr(ctx, i).length, getattr(ctx, i).offset) for i in allslots(ctx) if getattr(getattr(ctx, i), 'offset', -1) >= 0 and getattr(getattr(ctx, i), 'lineno') == self.lineno), default=(self.node.length, self.node.offset))

		loff = min((lstripcount(i)[0] for i in self.srclines[minlineno-1:maxlineno]), default=0)
		srclines = tuple(i[loff:] for i in self.srclines)
		line, srclines = line[loff:].expandtabs(TAB_SIZE), tuple(i.expandtabs(TAB_SIZE) for i in srclines)

		loff = lstripcount(line)[0]

		return (f'\033[2m(in {self.scope})\033[0m ' if (self.scope is not None) else '')+\
			f"{self.__exline__()} {self.at}"+(':\n'+\
			'\033[1m'+('  '+'\n  '.join(srclines[minlineno-1:self.lineno-1])+'\n' if (minlineno < self.lineno) else '')+\
			'  '+line[:minoffset-l]+'\033[91m'*(self.node.offset >= 0)+line[minoffset-l:maxoffset+maxoffsetlength]+'\033[0m'+line[maxoffset+maxoffsetlength:]+'\033[0m\n'+\
			'\033[95m'+' '*(2+loff+minoffset-l)+'~'*(self.node.offset-minoffset)+'^'+'~'*(maxoffset+maxoffsetlength-(2+loff+minoffset-l)-(self.node.offset-minoffset)+1)+\
			('\n\033[0;91m  '+'\n  '.join(srclines[self.lineno:maxlineno]) if (maxlineno > self.lineno and len(srclines) > self.lineno) else '')+\
			'\033[0m' if (srclines) else '')+\
			self.__exsubline__()+\
			(f"\n\n\033[1;95mCaused by:\033[0m\n{self.__cause__ if (isinstance(self.__cause__, (SlSyntaxException, SlNodeException))) else ' '+str().join(traceback.format_exception(type(self.__cause__), self.__cause__, self.__cause__.__traceback__))}" if (self.__cause__ is not None) else '')

	@abc.abstractmethod
	def __exline__(self):
		return ''

	def __exsubline__(self):
		return ''

	@property
	def at(self):
		return f"at line {self.node.lineno}, offset {self.node.offset}"

	@property
	def lineno(self):
		return self.node.lineno

class SlValidationException(SlNodeException): pass

class SlValidationError(SlValidationException):
	desc: ...

	def __init__(self, desc, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.desc = desc

	def __exline__(self):
		return f"Validation error: {self.desc}"

class SlValidationNotDefinedError(SlValidationError):
	def __init__(self, identifier, *args, **kwargs):
		super().__init__(f"`{identifier.identifier}' is not defined", identifier, *args, **kwargs)

class SlValidationRedefinedError(SlValidationError):
	def __init__(self, identifier, definition, *args, **kwargs):
		super().__init__(f"`{identifier}' redefined (defined as `{definition}')", identifier, *args, **kwargs)# at lineno {definition.lineno}

def optimize_ast(ast, ns, level=DEFAULT_OLEVEL): return ast.optimize(ns)

# by Sdore, 2021
