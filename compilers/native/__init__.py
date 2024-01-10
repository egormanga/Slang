#!/usr/bin/python3
# Slang Native (ASM) compiler target

from .. import *
from ...ast import *
from utils import *

class NativeCompiler(Compiler): pass

try: compiler = importlib.import_module(f".{platform.machine()}", __package__).compiler
except ModuleNotFoundError: compiler = NativeCompiler

# by Sdore, 2021
