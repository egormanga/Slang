# Slang

import lexer:*

str src = "main {print('hello');}"

main {
	stdio.println("Source: {"+src+"}\n")

	list tl = parse_string(src)
	stdio.println(tl)
	stdio.println("Tokens:")
	stdio.println(tl)
	stdio.println("\n")
}

# by Sdore, 2020
