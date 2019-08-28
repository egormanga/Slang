#!/usr/bin/python3
# Slang lexer

from .tokens import *

def read_token(src, *, lineno, offset, lineoff):
	(l, src), line = lstripcount(src[offset:], whitespace), src
	offset += l
	if (src[:1] in '\n;'): return (offset, None)
	length = int()
	for ii, i in enumerate(Token.types):
		r = globals()['find_'+i.casefold()](src) or 0
		if (isinstance(r, int) and r <= 0): length = max(length, -r); continue
		n, s = r if (isinstance(r, tuple)) else (r, src[:r])
		return (offset+n, Token(ii, s, lineno=lineno, offset=offset+lineoff))
	else: raise SlSyntaxError("Invalid token", line, lineno=lineno, offset=offset+lineoff, length=length)

def parse_expr(src, *, lineno=1, lineoff=0):
	r = list()
	offset = int()
	while (True):
		offset, tok = read_token(src, lineno=lineno, offset=offset, lineoff=lineoff)
		if (tok is None): break
		r.append(tok)
	return offset, r

def parse_string(src):
	src = src.rstrip()
	tl = list()
	lines = src.count('\n')
	lineoff = int()
	while (src):
		offset, r = parse_expr(src, lineno=lines-src.count('\n')+1, lineoff=lineoff)
		lineoff += offset
		if (offset < len(src)):
			if (src[offset] == '\n'): lineoff = int()
			else: lineoff += 1
		src = src[offset+1:]
		tl.append(r)
	return tl

# by Sdore, 2019
