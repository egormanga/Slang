#!/usr/bin/python3
# Slang

from .ast import *
from .compilers import *
from utils.nolog import *; logstart('Slang')

def compile(src, filename='<string>', *, compiler, optimize=0):
	try:
		#print(f"Source: {{\n{S(src).indent()}\n}}\n")

		tl = parse_string(src)
		#print(f"Tokens:\n{pformat(tl)}\n")

		ast = build_ast(tl, filename.join('""'))
		print(f"Code: {ast.code}\n")

		#print(f"Nodes: {pformat(list(walk_ast_nodes(ast)))}\n")

		if (optimize):
			optimize_ast(ast, validate_ast(ast), optimize)
			print(f"Optimized: {ast.code}\n")
			#print(f"Optimized Nodes: {pformat(list(walk_ast_nodes(ast)))}\n")

		ns = validate_ast(ast)

		code = compiler.compile_ast(ast, ns, filename=filename)
		#print("Compiled.\n")
	except (SlSyntaxException, SlNodeException) as ex:
		if (not ex.srclines): ex.srclines = src.split('\n')
		sys.exit(str(ex))
	return code

@apmain
@aparg('file', metavar='<file.sl>', type=argparse.FileType('r'))
@aparg('-o', metavar='output', dest='output')
@aparg('-f', metavar='compiler', dest='compiler', default='pyssembly')#required=True)
@aparg('-O', metavar='level', help='Code optimization level', type=int, default=DEFAULT_OLEVEL)
def main(cargs):
	if (cargs.output is None and not cargs.file.name.rpartition('.')[0]):
		argparser.add_argument('-o', dest='output', required=True)
		cargs = argparser.parse_args()
	src = cargs.file.read()
	filename = cargs.file.name
	compiler = importlib.import_module('.compilers.'+cargs.compiler, package=__package__).__dict__['compiler']
	code = compile(src, filename=filename, compiler=compiler, optimize=cargs.O)
	open(cargs.output or cargs.file.name.rpartition('.')[0]+compiler.ext, 'wb').write(code)

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2020
