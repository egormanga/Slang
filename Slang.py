#!/usr/bin/python3
# Slang

from .ast import *
from .compilers import *
from utils.nolog import *; logstart('Slang')

def compile(src, filename='<string>', *, compiler):
	try:
		#print(f"Source: {{\n{S(src).indent()}\n}}\n")

		tl = parse_string(src)
		#print(f"Tokens:\n{pformat(tl)}\n")

		ast = build_ast(tl, filename)
		#print(f"Code: {ast.code}\n")

		#print(f"Nodes: {pformat(list(walk_ast_nodes(ast)))}\n")

		optimize_ast(ast, validate_ast(ast))
		#print(f"Optimized: {ast.code}\n")

		code = compiler.compile_ast(ast, validate_ast(ast), filename=filename)
		#print("Compiled.\n")
	except (SlSyntaxError, SlValidationError, SlCompilationError) as ex:
		if (not ex.line): ex.line = src.split('\n')[ex.lineno-1]
		sys.exit(ex)
	return code

@apmain
@aparg('file', metavar='<file>', type=argparse.FileType('r'))
@aparg('-o', dest='output')
@aparg('-f', dest='compiler', required=True)
def main(cargs):
	if (cargs.output is None and not cargs.file.name.rpartition('.')[0]):
		argparser.add_argument('-o', dest='output', required=True)
		cargs = argparser.parse_args()
	src = cargs.file.read()
	filename = cargs.file.name
	_cns = importlib.import_module('.compilers.'+cargs.compiler, package=__package__).__dict__.values()
	compiler = first(i for i in allsubclasses(Compiler) if i in _cns)
	code = compile(src, filename=filename.join('""'), compiler=compiler)
	open(cargs.output or cargs.file.name.rpartition('.')[0]+compiler.ext, 'wb').write(code)

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2020
