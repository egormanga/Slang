# Slang tokens

str whitespace = ' \t\r\v\f'

tuple lstripcount(str s, str chars) {
	int ii = -1
	char i
	for i in s {
		ii += 1
		if i not in chars {
			break
		}
	}
	else {
		ii = 0
	}
	return (ii, s#|[ii:]|#)
}

class Token {
	int type
	str token
	int lineno
	int offset

	tuple types# = ('SPECIAL', 'OPERATOR', 'LITERAL', 'KEYWORD', 'IDENTIFIER')  # order is also resolution order

	constr(int type, str token, int lineno, int offset) {
		#.type, .token, .lineno, .offset = type, token, lineno, offset
	}

	#|repr {
		return "<Token {.types[.type]} «{repr(.token)[1:-1]}» at line {.lineno}, offset {.offset}>"
	}|#

	#|eq {
		#return super() == x or .token == x
	}|#

	#|property typename {
		#return .types[.type]
	}

	property length {
		#return .token.length
	}|#
}

# by Sdore, 2020
