#!/usr/bin/python3
# Slang REPL

import readline
from .ast import *
from .lexer import *
from utils import *

@dispatch
def execute_node(node: ASTCodeNode, ns):
	for i in node.nodes:
		r = execute_node(i, ns)
		if (r is not None):
			ns.values['_'] = r
			print(repr(r))
	else: return
	return r

@dispatch
def execute_node(node: ASTVardefNode, ns):
	ns.values[node.name] = node.value

@dispatch
def execute_node(node: ASTFuncdefNode, ns):
	ns.values[node.name.identifier] = (node.argdefs, node.code)

@dispatch
def execute_node(node: ASTAssignmentNode, ns):
	ns.values[node.name] = node.value

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
	return ns.values[node]

@dispatch
def execute_node(node: ASTLiteralNode, ns):
	return eval(str(node.literal))

@dispatch
def execute_node(node: ASTKeywordExprNode, ns):
	if (node.keyword.keyword == 'return'): return execute_node(node.value, ns)
	raise NotImplementedError(node.keyword)

@dispatch
def execute_node(node: ASTUnaryExprNode, ns):
	return eval(f"{node.operator.operator} {execute_node(node.value, ns)}")

@dispatch
def execute_node(node: ASTBinaryExprNode, ns):
	return eval(f"{execute_node(node.lvalue, ns)} {node.operator.operator} {execute_node(node.rvalue, ns)}")

def repl():
	ns = Namespace('<repl>')
	#ns.values['print'] = print
	l = list()
	tl = list()
	while (True):
		try:
			l.append(input(f"\1\033[1;93m\2{'...' if (tl) else '>>>'}\1\033[0m\2 "))
			tll = parse_string(l[-1])
			if (not tll): continue
			tl += tll
			if (tl[-1][-1].token == '\\'): continue
			if (len(tl) >= 2 and tl[-2][-1].token == '\\'): tl[-1] = tl[-2][:-1]+tl.pop()
			if (tl[0][-1].token == '{' and tl[-1][-1].token != '}'): continue
			ast = build_ast(tl, interactive=True)
			validate_ast(ast, ns)
			optimize_ast(ast, ns)
			execute_node(ast.code, ns)
		except (EOFError, KeyboardInterrupt): break
		except (SlSyntaxError, SlValidationError) as ex:
			ex.line = l[ex.lineno-1]
			print(ex)
		tl.clear()
		l.clear()

# by Sdore, 2019
