# Slang lexer

import tokens:*

tuple read_token(str src, int lineno, int offset, int lineoff) {
	tuple c = lstripcount(src[offset:], whitespace)

	int l = c[0]
	src = c[1]
	str line = src
	offset += l
	if not src or src[0] in '\n;' {
		return (offset, None)
	}

	int length = 0, ii = -1

	for i in Token.types {
		ii += 1
		auto r = globals['find_'+i.casefold()](src) or 0

		if r isof int and r <= 0 {
			length = max(length, -r)
			continue
		}

		tuple c

		if r isof tuple: c = r
		else: c = (r, src[:r])

		int n = c[0]
		str s = c[1]

		return (offset+n, Token(ii, s, lineno=lineno, offset=offset+lineoff))
	} else: raise SlSyntaxError("Invalid token", line, lineno=lineno, offset=offset+lineoff, length=length)

	return (0, Token())
}

tuple parse_expr(str src, int lineno = 1, int lineoff = 0) {
	list r = [Token]
	int offset

	while true {
		offset, tok = read_token(src, lineno=lineno, offset=offset, lineoff=lineoff)
		if tok is None: break
		r.append(tok)
	}

	return (offset, r)
}

list parse_string(str src) {
	src = src.rstrip()
	list tl = [Token]
	int lines = src.count('\n')
	int lineoff = 0

	while src {
		tuple c = parse_expr(src, lineno=lines-src.count('\n')+1, lineoff=lineoff)
		int offset = c[0]
		list r = c[1]

		lineoff += offset

		if offset < src.len {
			if src[offset] == '\n': lineoff = 0
			else: lineoff += 1
		}

		src = src[offset+1:]
		tl.append(r)
	}

	return tl
}

# by Sdore, 2021
# slang.sdore.me
