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
	else: raise SlSyntaxError("Invalid token", line, lineno=lineno, offset=offset+lineoff, length=length+l)

def parse_expr(src, *, lineno=1, lineoff=0):
	r = list()
	lines = src.count('\n')
	offset = int()
	continueln = False
	while (True):
		offset, tok = read_token(src, lineno=lines-src[offset:].count('\n')+lineno, offset=offset, lineoff=lineoff)
		if (tok is None):
			if (not continueln): break
			continueln = False
			offset += 1
			lineoff = -offset
			continue
		elif (continueln and tok.token[0] != '#'): raise SlSyntaxError("Expected newline or comment after line continuation", src, lineno=lines-src[offset:].count('\n')+lineno, offset=tok.offset, length=tok.length)
		r.append(tok)
		if (tok.token[0] != '#'): continueln = (tok.token == '\\' and tok.offset)
	return offset, r

def parse_string(src, lnooff=0):
	src = src.rstrip()
	tl = list()
	lines = src.count('\n')+lnooff
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

# by Sdore, 2020
