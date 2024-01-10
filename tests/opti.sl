#| Slang `opti' test. |#

int a = 3

void f() {a = 5}
void g() {a += 2+2}

main {
	stdio.println(a)
	a = 4
	stdio.println(a)
	f()
	stdio.println(a)
	g()
	stdio.println(a)
}
