#!/usr/bin/python3
# Slang Tokens

from utils import *

class Keyword(str): pass
class ExprKeyword(Keyword): pass
class Modifier(Keyword): pass
class ReservedKeyword(Keyword): pass

class Operator(str): pass
class UnaryOperator(Operator): pass
class BinaryOperator(Operator): pass

keywords = (
	Keyword('if'),
	Keyword('for'),
	Keyword('in'),
	Keyword('while'),
	Keyword('else'),
	ExprKeyword('return'),
	ExprKeyword('break'),
	ExprKeyword('continue'),
	ExprKeyword('import'),
	Modifier('const'),
	Modifier('volatile'),
	ReservedKeyword('def'),
)

operators = (*(tuple(map(*i)) for i in ( # ordered by priority
	(UnaryOperator, '!$:~'),
	(BinaryOperator, ('**',)),
	(BinaryOperator, ('//', *'*/%')),
	(BinaryOperator, '+-'),
	(BinaryOperator, ('<<', '>>')),
	(BinaryOperator, '&'),
	(BinaryOperator, '^'),
	(BinaryOperator, '|'),
	(BinaryOperator, ('<', '<=', '>', '>=', '==', '!=', 'is not', 'is')),
	(UnaryOperator, ('not',)),
	(BinaryOperator, ('&&', 'and')),
	(BinaryOperator, ('^^', 'xor')),
	(BinaryOperator, ('||', 'or')),
	(BinaryOperator, ('to',)),
)),)
bothoperators = '%&*+-^'
attrops = ('->', '@.', *'@.:')
keyword_operators = ('is not', 'is', 'not', 'and', 'xor', 'or', 'to')

whitespace = ' \t\r\v\f'
specials = ('..', '->', '@.', *'#@.\\,;?=()[]{}')

def find_identifier(s):
	if (not s or not s[0].isidentifier()): return
	i = 1
	for i in range(1, len(s)):
		if (not s[i].isalnum() and s[i] != '_'): break
	else: i += 1
	if (s[:i].isidentifier()): return i

def find_keyword(s):
	if (not s): return
	for i in keywords:
		if (s.startswith(i)):
			l = len(i)
			if (not s[l:l+1] or s[l:l+1].isspace()): return (l, i)

def find_literal(s):
	if (not s): return
	if (s[0] in '"\''):
		esc = bool()
		for i in range(1, len(s)):
			if (esc): esc = False; continue
			if (s[i] == '\\'): esc = True; continue
			if (s[i] == s[0]): return i+1
	if (s[0].isdigit() or s[0] == '.'):
		i = int()
		digits = '0123456789abcdef'
		radix = 10
		digit = True
		dp = s[0] == '.'
		for i in range(1, len(s)):
			if (i == 1 and s[0] == '0'):
				if (s[1] not in 'box'):
					if (s[1].isalnum()): return
					return 1
				else:
					radix = (2, 8, 16)['box'.index(s[1])]
					digit = False
					continue
			if (s[i].casefold() not in digits[:radix]):
				if (s[i] == '_'): continue
				if (s[i] == '.' and not dp): dp = True; continue
				if (not digit or s[i].isalpha()): return
				return i
			digit = True
		if (s[i].casefold() in digits[:radix] or s[i] == '.' and not dp): return i+1

def find_operator(s):
	if (not s): return
	for i in sorted(itertools.chain(*operators), key=len, reverse=True):
		if (s.startswith(i)):
			l = len(i)
			if (not (i[-1].isalpha() and s[l:l+1].isalnum())): return (len(i), i)

def find_special(s):
	if (not s): return
	if (s[0] == '.' and s[1:2].isdigit()): return
	if (s[:2] == '#|'):
		l = s.find('|#', 2)
		if (l == -1): return -2
		return l+2
	if (s[0] == '#'):
		l = s.find('\n', 1)
		if (l == -1): return len(s)
		return l
	if (s[:2] == '\\\n'): return 2
	for i in sorted(specials, key=len, reverse=True):
		if (s[:len(i)] == i):
			if (i == '=' and s[:len(i)+1] == '=='): break
			return len(i)

def operator_precedence(op):
	for ii, i in enumerate(operators):
		if (op in i): return ii
	#else: return len(operators)

class Token:
	__slots__ = ('type', 'token', 'lineno', 'offset')
	types = ('SPECIAL', 'OPERATOR', 'LITERAL', 'KEYWORD', 'IDENTIFIER') # order is also resolution order

	def __init__(self, type, token, *, lineno, offset):
		self.type, self.token, self.lineno, self.offset = type, token, lineno, offset

	def __repr__(self):
		return f"<Token {self.types[self.type]} «{repr(self.token)[1:-1]}» at line {self.lineno}, offset {self.offset}>"

	def __eq__(self, x):
		return super() == x or self.token == x

	@property
	def typename(self):
		return self.types[self.type]

	@property
	def length(self):
		return len(self.token)

def lstripcount(s, chars):
	for ii, i in enumerate(s):
		if (i not in chars): break
	else: ii = 0
	return (ii, s[ii:])

class SlSyntaxException(Exception): pass
class SlSyntaxNoToken(SlSyntaxException): pass
class SlSyntaxEmpty(SlSyntaxNoToken): pass

class SlSyntaxError(SlSyntaxException):
	__slots__ = ('desc', 'line', 'lineno', 'offset', 'length')

	#@dispatch
	def __init__(self, desc='Syntax error', line='', *, lineno, offset, length, scope=None):
		self.desc, self.line, self.lineno, self.offset, self.length = (f'\033[2m(in {scope})\033[0m ' if (scope is not None) else '')+desc, line, lineno, offset, length

	#@dispatch
	#def __init__(self, desc='Syntax error', *, token):
	#	self.desc, self.line, self.lineno, self.offset, self.length = desc, '', token.lineno, token.offset, token.length

	def __str__(self):
		l, line = lstripcount(self.line.partition('\n')[0].replace('\t', ' '), ' \t')
		offset = (self.offset-l) if (self.offset != -1) else len(line)
		return f"{self.desc}{self.at}"+(':\n'+\
			'  \033[1m'+line[:offset]+'\033[91m'+line[offset:]+'\033[0m\n'+\
			'  '+' '*offset+'\033[95m^'+'~'*(self.length-1) if (line) else '')

	@property
	def at(self):
		return f" at line {self.lineno}, offset {self.offset}"

class SlSyntaxExpectedError(SlSyntaxError):
	__slots__ = ('expected', 'found')

	def __init__(self, expected='nothing', found='nothing', *, lineno=None, offset=None, length=0, scope=None):
		assert expected != found
		if (not isinstance(found, str)): lineno, offset, length, found = found.lineno, found.offset, found.length, found.typename if (hasattr(found, 'typename')) else found
		assert lineno is not None and offset is not None
		super().__init__(f"Expected {expected.lower()},\n{' '*(len(scope)+6 if (scope is not None) else 3)}found {found.lower()}", lineno=lineno, offset=offset, length=length, scope=scope)
		self.expected, self.found = expected, found

class SlSyntaxExpectedNothingError(SlSyntaxExpectedError):
	def __init__(self, found='nothing', **kwargs):
		super().__init__(found=found, **kwargs)

class SlSyntaxMultiExpectedError(SlSyntaxExpectedError):
	__slots__ = ('sl',)

	def __init__(self, expected, found, *, scope=None, **kwargs):
		self.sl = len(scope)+6 if (scope is not None) else 0
		super().__init__(S(',\n'+' '*(self.sl+9)).join(Stuple(expected).strip('nothing').uniquize(), last=',\n'+' '*(self.sl+6)+'or ') or 'nothing', S(',\n'+' '*(self.sl+6)).join(Stuple(f"{i.found} at offset {i.offset if (i.offset != -1) else '<end of line>'}" for i in found).strip('nothing').uniquize(), last=',\n'+' '*(self.sl+2)+'and ') or 'nothing', scope=scope, **kwargs)

	@property
	def at(self):
		return f"\n{' '*self.sl}at line {self.lineno}"

# by Sdore, 2019
