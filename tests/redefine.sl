#| Slang `redefine' test. |#

main {
	int a
	a = 3
	a, b := (int a, char 'b')
	stdio.println(a, b)
}
