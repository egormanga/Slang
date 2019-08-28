#!/usr/bin/python3
# Slang

from .ast import *
from .repl import *
from .compilers import *
from .compilers.pyssembly import *
from utils.nolog import *; logstart('Slang')

def debug_compile(src, filename='<string>'):
	try:
		#print(f"Source: {{\n{S(src).indent()}\n}}\n")

		tl = parse_string(src)
		#print(f"Tokens:\n{pformat(tl)}\n")

		ast = build_ast(tl, filename)
		#print(f"Code: {repr(ast.code)}\n")

		#print(f"Nodes: {pformat(list(walk_ast_nodes(ast)))}\n")

		optimize_ast(ast, validate_ast(ast))
		#print(f"Optimized: {repr(ast.code)}\n")

		code = PyssemblyCompiler.compile_ast(ast, validate_ast(ast), filename=filename)
		#print("Compiled.\n")

		#print("Running.\n")
		#exec(code, {})
		#print("\nFinished.\n")
	except (SlSyntaxError, SlValidationError, SlCompilationError) as ex:
		ex.line = src.split('\n')[ex.lineno-1]
		sys.exit(ex)
	except pyssembly.PyssemblyError as ex:
		print('Error:', ex)
		try: code = ex.code.to_code()
		except pyssembly.PyssemblyError: pass
		else:
			print("\nHere is full pyssembly code 'til the errorneous line:\n")
			dis.dis(code)
		sys.exit(1)
	else: return code

def main(cargs):
	if (cargs.o is None and not cargs.file.name.rpartition('.')[0]):
		argparser.add_argument('-o', metavar='<output>', required=True)
		cargs = argparser.parse_args()
	src = cargs.file.read()
	filename = cargs.file.name
	code = debug_compile(src, filename=filename.join('""'))
	open(cargs.o or cargs.file.name.rpartition('.')[0]+'.pyc', 'wb').write(pyssembly.asm(code))

if (__name__ == '__main__'):
	argparser.add_argument('file', metavar='<file>', type=argparse.FileType('r'))
	argparser.add_argument('-o', metavar='<output>')
	cargs = argparser.parse_args()
	logstarted(); exit(main(cargs))
else: logimported()

# by Sdore, 2019
