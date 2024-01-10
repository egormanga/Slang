#| Slang `scope' test. |#

int a = 3

int g() = 5

int f() {
	int a = 4
	int g = g()
	return a+g
}

main {
	int a = f()
	stdio.println(a)
}
