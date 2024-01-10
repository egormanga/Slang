#!/usr/bin/python3
# Slang compilers

from ..ast import Slots, lstripcount, SlSyntaxError, SlNodeException, SlValidationError
import abc, traceback

class Compiler(abc.ABC):
	ext = ''

	@abc.abstractclassmethod
	def compile_ast(cls, ast):
		pass

class SlCompilationError(SlNodeException):
	desc: ...

	def __init__(self, desc, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.desc = desc

	def __exline__(self):
		return f"Compilation error: {self.desc}"

# by Sdore, 2021
