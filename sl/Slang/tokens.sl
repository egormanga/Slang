# Slang tokens

const str whitespace = " \t\r\v\f"

tuple lstripcount(str s, str chars) {
	int ii = -1
	char i

	for i in s {
		ii += 1
		if i not in chars: break
	} else: ii = 0

	return (ii, s[ii:])
}

class Token {
	const tuple types = ('SPECIAL', 'OPERATOR', 'LITERAL', 'KEYWORD', 'IDENTIFIER')  # order is also resolution order

	int type, lineno, offset
	str token

	constr (int .type, str .token, int .lineno, int .offset);

	repr = f"<Token {.typename} «{repr(.token)[1:-1]}» at line {.lineno}, offset {.offset}>"

	eq = (super == x or .token == x)

	property typename = .types[.type]

	property length = .token.length
}

# by Sdore, 2021
# slang.sdore.me
