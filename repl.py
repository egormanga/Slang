#!/usr/bin/python3
# Slang REPL

import readline
from .ast import *
from .lexer import *
from utils.nolog import *

def get_node_value(node, ns):
	while (isinstance(node, ASTNode)):
		node = execute_node(node, ns)
	if (isiterablenostr(node)):
		try: node = type(node)(get_node_value(i, ns) for i in node)
		except Exception: pass
	return node

@dispatch
def execute_node(node: ASTCodeNode, ns):
	r = None
	for i in node.nodes:
		if (isinstance(i, ASTElseClauseNode) and r is not None): continue
		r = execute_node(i, ns)
		if (ns.flags.interactive and r not in (None, ...)):
			ns.values['_'] = r
			print(repr(r))
	return r

@dispatch
def execute_node(node: ASTVardefNode, ns):
	if (node.value is not None): ns.values[node.name] = get_node_value(node.value, ns)

@dispatch
def execute_node(node: ASTBlockNode, ns):
	return execute_node(node.code, ns)

@dispatch
def execute_node(node: ASTFuncdefNode, ns):
	ns.values[node.name.identifier] = node

@dispatch
def execute_node(node: ASTAssignmentNode, ns):
	ns.values[node.name] = execute_node(ASTBinaryExprNode(node.name, node.inplace_operator, node.value, lineno=node.value.lineno, offset=node.value.offset), ns) if (node.inplace_operator is not None) else get_node_value(node.value, ns)

@dispatch
def execute_node(node: ASTUnaryOperationNode, ns):
	def _op(): execute_node(ASTAssignmentNode(node.name, node.isattr, ASTSpecialNode('=', lineno=node.unary_operator.lineno, offset=node.unary_operator.offset), ASTOperatorNode(node.unary_operator.operator[0], lineno=node.unary_operator.lineno, offset=node.unary_operator.offset), ASTLiteralNode(1 if (node.unary_operator.operator[0] in '+-') else get_node_value(node.name, ns), lineno=node.unary_operator.lineno, offset=node.unary_operator.offset), lineno=node.lineno, offset=node.offset), ns)
	if (isinstance(node, ASTUnaryPreOperationNode)): _op()
	res = ns.values[node.name]
	if (isinstance(node, ASTUnaryPostOperationNode)): _op()
	return res

@dispatch
def execute_node(node: ASTItemgetNode, ns):
	return get_node_value(node.value, ns)[get_node_value(node.key, ns)]

@dispatch
def execute_node(node: ASTAttrgetNode, ns):
	if (node.optype.special == '.'):
		if (isinstance(node.value.value, ASTIdentifierNode) and node.value.value.identifier == 'stdio'):
			if (node.attr.identifier == 'println'): return stdlib.stdio.println
		elif (node.attr.identifier == 'map'): return stdlib._map
		elif (node.attr.identifier == 'each'): return stdlib._each
	raise NotImplementedError(node)

@dispatch
def execute_node(node: ASTFunccallNode, ns):
	func = execute_node(node.callable, ns)

	if (isinstance(func, type) and issubclass(func, stdlib.Builtin)):
		if (func is stdlib.stdio.println): f = print
		elif (func is stdlib._map): f = lambda l: [execute_node(ASTFunccallNode(node.callable.value.value, ASTCallargsNode([i], [], lineno=node.callargs.lineno, offset=node.callargs.offset), ASTCallkwargsNode([], [], lineno=node.callkwargs.lineno, offset=node.callkwargs.offset), lineno=node.callable.lineno, offset=node.callable.offset), ns) for i in l]
		elif (func is stdlib._each): f = lambda _: [execute_node(ASTFunccallNode(node.callargs.callargs[0].value, ASTCallargsNode([i], [], lineno=node.callargs.lineno, offset=node.callargs.offset), ASTCallkwargsNode([], [], lineno=node.callkwargs.lineno, offset=node.callkwargs.offset), lineno=node.callable.lineno, offset=node.callable.offset), ns) for i in get_node_value(node.callable.value.value, ns)]
		else: raise NotImplementedError(func)

		callarguments = CallArguments.build(node, ns)
		assert (func.compatible_call(callarguments, ns) is not None)
		return f(*(get_node_value(i, ns) for i in node.callargs.callargs),
			 *(get_node_value(j, ns) for i in node.callargs.starargs for j in get_node_value(i, ns)))

	code_ns = ns.derive(str(node.callable), append=False)
	for ii, i in enumerate(node.callargs.callargs):
		code_ns.values[func.argdefs[ii].name] = get_node_value(i, ns)
	return execute_node(func.code, code_ns)

@dispatch
def execute_node(node: ASTValueNode, ns):
	return execute_node(node.value, ns)

@dispatch
def execute_node(node: ASTIdentifierNode, ns):
	if (ns.values.get(node) is None): raise SlValidationError(f"{node} is not initialized", node, scope=ns.scope)
	return ns.values[node]

@dispatch
def execute_node(node: ASTLiteralNode, ns):
	if (isinstance(node.literal, str)):
		try: return eval(node.literal)
		except Exception as ex: raise SlReplError(ex, node, scope=ns.scope)
	else: return node.literal

@dispatch
def execute_node(node: ASTListNode, ns):
	return list(node.values)

@dispatch
def execute_node(node: ASTTupleNode, ns):
	return tuple(node.values)

@dispatch
def execute_node(node: ASTKeywordExprNode, ns):
	if (node.keyword.keyword == 'return'): return execute_node(node.value, ns)
	elif (node.keyword.keyword == 'delete'): ns.delete(node.value)
	else: raise NotImplementedError(node.keyword)

@dispatch
def execute_node(node: ASTKeywordDefNode, ns):
	if (node.keyword.keyword == 'main'):
		execute_node(node.code, ns)

@dispatch
def execute_node(node: ASTConditionalNode, ns):
	if (execute_node(node.condition, ns)):
		execute_node(node.code, ns)
	else: return
	return ...

@dispatch
def execute_node(node: ASTForLoopNode, ns):
	ns.define(node.name, Signature.build(node.iterable, ns).valtype)
	ns.weaken(node.name)
	for i in execute_node(node.iterable, ns):
		ns.values[node.name] = get_node_value(i, ns)
		execute_node(node.code, ns)
	else: return
	return ...

@dispatch
def execute_node(node: ASTWhileLoopNode, ns):
	while (get_node_value(execute_node(node.condition, ns), ns)):
		execute_node(node.code, ns)
	else: return
	return ...

@dispatch
def execute_node(node: ASTElseClauseNode, ns):
	execute_node(node.code, ns)

@dispatch
def execute_node(node: ASTUnaryExprNode, ns):
	value = get_node_value(node.value, ns)
	try: return eval(f"{node.operator.operator} value")
	except Exception as ex: raise SlReplError(ex, node, scope=ns.scope)

@dispatch
def execute_node(node: ASTBinaryExprNode, ns):
	lvalue = get_node_value(node.lvalue, ns)
	rvalue = get_node_value(node.rvalue, ns)
	if (node.operator.operator == 'xor'):
		try: return eval("(lvalue and not rvalue) or (rvalue and not lvalue)")
		except Exception as ex: raise SlReplError(ex, node, scope=ns.scope)
	elif (node.operator.operator == 'to'):
		try: return range(lvalue, rvalue)
		except Exception as ex: raise SlReplError(ex, node, scope=ns.scope)
	else:
		try: return eval(f"lvalue {node.operator.operator} rvalue")
		except Exception as ex: raise SlReplError(ex, node, scope=ns.scope)

class Completer:
	def __init__(self, namespace):
		self.namespace = namespace

	def complete(self, text, state):
		if (state == 0):
			if ('.' in text): self.matches = self.attr_matches(text)
			else: self.matches = self.global_matches(text)
		try: return self.matches[state]
		except IndexError: return None

	def _callable_postfix(self, val, word):
		if (isinstance(val, ASTCallableNode)): word += '('
		return word

	def global_matches(self, text):
		matches = list()
		seen = set()
		n = len(text)

		for word in keywords:
			if (word[:n] != text): continue
			seen.add(word)
			matches.append(word+' ')

		for word, val in self.namespace.values.items():
			if (word[:n] != text or word in seen): continue
			seen.add(word)
			matches.append(self._callable_postfix(val, word))

		return matches

	def attr_matches(self, text):
		m = re.match(r"(\w+(\.\w+)*)\.(\w*)", text)
		if (m is None): return ()
		expr, attr = m.group(1, 3)
		try: obj = self.namespace.values[expr] # TODO FIXME
		except KeyError: return ()

		words = set() # TODO FIXME attrs

		matches = list()
		n = len(attr)
		if (attr == ''): noprefix = '_'
		elif (attr == '_'): noprefix = '__'
		else: noprefix = None

		while (True):
			for word in words:
				if (word[:n] != attr or (noprefix and word[:n+1] == noprefix)): continue
				match = f"{expr}.{word}"
				try: val = getattr(obj, word)
				except Exception: pass  # Include even if attribute not set
				else: match = self._callable_postfix(val, match)
				matches.append(match)
			if (matches or not noprefix): break
			if (noprefix == '_'): noprefix = '__'
			else: noprefix = None

		matches.sort()
		return matches

class SlReplError(SlNodeException):
	ex: ...

	def __init__(self, ex, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.ex = ex

	def __exline__(self):
		return "Repl error"

	def __exsubline__(self):
		return f"\n\033[1;91mException\033[0m:\n "+'\n '.join(traceback.format_exception_only(type(self.ex), self.ex))

def repl(*, optimize=0):
	ns = Namespace('<repl>')
	ns.define(ASTIdentifierNode('_', lineno=None, offset=None), stdlib.Any)
	ns.flags.interactive = True

	completer = Completer(ns)
	histfile = os.path.expanduser('~/.sli_history')
	try: readline.read_history_file(histfile)
	except FileNotFoundError: pass
	for i in (
		'set colored-completion-prefix on',
		'set enable-bracketed-paste on',
		#'set horizontal-scroll-mode on',
		'set skip-completed-text on',
		'tab: complete',
	): readline.parse_and_bind(i)
	readline.set_completer(completer.complete)
	#readline.set_completion_display_matches_hook(completer.display) # TODO

	l = list()
	tl = list()

	try:
		while (True):
			try:
				l.append(input(f"\1\033[1;93m\2{'...' if (tl) else '>>>'}\1\033[0m\2 "))
				tll = parse_string(l[-1], lnooff=len(l)-1)
				if (not tll): l.pop(); continue
				tl += tll
				if (tl[-1][-1].token == '\\'): continue
				#if (len(tl) >= 2 and tl[-2][-1].token == '\\'): tl[-1] = tl[-2][:-1]+tl.pop() # TODO FIXME?: [['a', '+', '\\'], 'b'] --> [['a', '+', 'b']]
				if (tl[0][-1].token == '{' and tl[-1][-1].token != '}'): continue
				ast = build_ast(tl, interactive=True)
				if (optimize): optimize_ast(ast, validate_ast(ast), optimize)
				validate_ast(ast, ns)
				execute_node(ast.code, ns)
			except KeyboardInterrupt:
				buf = readline.get_line_buffer()
				print(f"\r\033[2m^C{'> '+buf if (buf) else ' '}\033[0m")
			except EOFError:
				print(end='\r\033[K')
				break
			except (SlSyntaxException, SlNodeException) as ex:
				if (not ex.srclines): ex.srclines = l
				print(ex)
			tl.clear()
			l.clear()
	finally: readline.write_history_file(histfile)

def run_file(file, *, optimize=0):
	src = file.read()

	try:
		tl = parse_string(src)
		ast = build_ast(tl, file.name.join('""'))
		if (optimize): optimize_ast(ast, validate_ast(ast), optimize)
		ns = validate_ast(ast)
		execute_node(ast.code, ns)
	except (SlSyntaxException, SlNodeException) as ex:
		if (not ex.srclines): ex.srclines = src.split('\n')
		sys.exit(str(ex))

@apmain
@aparg('file', metavar='file.sl', nargs='?', type=argparse.FileType('r'))
@aparg('-O', metavar='level', help='Code optimization level', type=int, default=DEFAULT_OLEVEL)
def main(cargs):
	if (cargs.file is not None): run_file(cargs.file, optimize=cargs.O)
	else: repl(optimize=cargs.O)

if (__name__ == '__main__'): main(nolog=True)

# by Sdore, 2020
