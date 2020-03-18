#!/usr/bin/python3
# Slang compilers

from ..ast import SlSyntaxError, SlValidationError
import abc, traceback

class Compiler(abc.ABC):
	@abc.abstractclassmethod
	def compile_ast(cls, ast):
		pass

def lstripcount(s, chars): # TODO: commonize
	for ii, i in enumerate(s):
		if (i not in chars): break
	else: ii = 0
	return (ii, s[ii:])

class SlCompilationError(Exception):
	__slots__ = ('desc', 'node', 'line', 'scope')

	def __init__(self, desc, node, line='', *, scope=None):
		self.desc, self.node, self.line, self.scope = desc, node, line, scope

	def __str__(self):
		l, line = lstripcount(self.line.partition('\n')[0].replace('\t', ' '), ' \t')
		offset = (self.node.offset-l) if (self.node.offset != -1) else len(line)
		return (f'\033[2m(in {self.scope})\033[0m ' if (self.scope is not None) else '') + f"Compilation error: {self.desc}{self.at}"+(':\n' + \
			'  \033[1m'+line[:offset]+'\033[91m'+line[offset:]+'\033[0m\n' + \
			'  '+' '*offset+'\033[95m^'+'~'*(self.node.length-1)+'\033[0m' if (line) else '') + \
			(f"\n\n\033[1;95mCaused by:\033[0m\n{self.__cause__ if (isinstance(self.__cause__, (SlSyntaxError, SlValidationError, SlCompilationError))) else ' '+str().join(traceback.format_exception(type(self.__cause__), self.__cause__, self.__cause__.__traceback__))}" if (self.__cause__ is not None) else '')

	@property
	def at(self):
		return f" at line {self.node.lineno}, offset {self.node.offset}"

	@property
	def lineno(self):
		return self.node.lineno

# by Sdore, 2019
