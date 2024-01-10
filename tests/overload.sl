#| Slang `overload' test. |#

int f(int x) = x+1
int f(int x, int y) = x+y+1

main {
	stdio.println(f(1))
	stdio.println(f(1, 2))
	f()
}
