#!/usr/bin/python3
# Slang REPL

import readline
from .ast import *
from .lexer import *
from utils.nolog import *

@dispatch
def execute_node(node: ASTCodeNode, ns):
	r = None
	for i in node.nodes:
		if (isinstance(i, ASTElseClauseNode) and r is not None): continue
		r = execute_node(i, ns)
		if (r not in (None, ...)):
			ns.values['_'] = r
			print(repr(r))
	else: return
	return r

@dispatch
def execute_node(node: ASTVardefNode, ns):
	ns.values[node.name] = node.value

@dispatch
def execute_node(node: ASTBlockNode, ns):
	return execute_node(node.code, ns)

@dispatch
def execute_node(node: ASTFuncdefNode, ns):
	ns.values[node.name.identifier] = (node.argdefs, node.code)

@dispatch
def execute_node(node: ASTAssignmentNode, ns):
	ns.values[node.name] = execute_node(ASTBinaryExprNode(node.name, node.inplace_operator, node.value, lineno=node.lineno, offset=node.offset), ns) if (node.inplace_operator is not None) else node.value

@dispatch
def execute_node(node: ASTFunccallNode, ns):
	code_ns = ns.derive(node.callable.value.identifier)
	argdefs, func = ns.values[node.callable]
	for ii, i in enumerate(node.callargs.callargs):
		code_ns.values[argdefs[ii].name] = i
	return execute_node(func, code_ns)

@dispatch
def execute_node(node: ASTValueNode, ns):
	return execute_node(node.value, ns)

@dispatch
def execute_node(node: ASTIdentifierNode, ns):
	try: return ns.values[node]
	except KeyError: raise SlValidationError(f"{node} is not initialized", node, scope=ns.scope)

@dispatch
def execute_node(node: ASTLiteralNode, ns):
	return eval(node.literal) if (isinstance(node.literal, str)) else node.literal

@dispatch
def execute_node(node: ASTListNode, ns):
	return node.values

@dispatch
def execute_node(node: ASTKeywordExprNode, ns):
	#if (node.keyword.keyword == 'return'): return execute_node(node.value, ns) # TODO FIXME???
	#el
	if (node.keyword.keyword == 'delete'): ns.delete(node.value)
	else: raise NotImplementedError(node.keyword)

@dispatch
def execute_node(node: ASTConditionalNode, ns):
	if (execute_node(node.condition, ns)):
		execute_node(node.code, ns)
	else: return
	return ...

@dispatch
def execute_node(node: ASTForLoopNode, ns):
	for i in execute_node(node.iterable, ns):
		execute_node(node.code, ns)
	else: return
	return ...

@dispatch
def execute_node(node: ASTUnaryExprNode, ns):
	value = execute_node(node.value, ns)
	return eval(f"{node.operator.operator} value")

@dispatch
def execute_node(node: ASTBinaryExprNode, ns):
	lvalue = execute_node(node.lvalue, ns)
	rvalue = execute_node(node.rvalue, ns)
	if (node.operator.operator == 'xor'): return eval("(lvalue and not rvalue) or (rvalue and not lvalue)")
	elif (node.operator.operator == 'to'): return range(lvalue, rvalue)
	else: return eval(f"lvalue {node.operator.operator} rvalue")

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

def repl():
	ns = Namespace('<repl>')
	ns.define(ASTIdentifierNode('_', lineno=None, offset=None), stdlib.Any())

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
				validate_ast(ast, ns)
				optimize_ast(ast, ns)
				execute_node(ast.code, ns)
			except KeyboardInterrupt:
				buf = readline.get_line_buffer()
				print(f"\r\033[2m^C{'> '+buf if (buf) else ' '}\033[0m")
			except EOFError:
				print(end='\r\033[K')
				break
			except (SlSyntaxError, SlValidationError) as ex:
				ex.line = l[ex.lineno-1]
				print(ex)
			tl.clear()
			l.clear()
	finally: readline.write_history_file(histfile)

if (__name__ == '__main__'): repl()

# by Sdore, 2020
