# this is a comment
#| and that is a
	multiline one. |#

const u32 n = 123123  # n is of type const u32
const i64 m = 10**18  # m is of type const i64
const int z = 2**128  # z is of type const int (unsized)
const auto q = 2**256  # q is of type const int

char f(str x) {  # f() is of type char, x is of type str
	auto c = x[1]  # c is of type char
	return c
}

auto g(str x) {  # g() is of type char, x is of type str
	return x[0]  # retval is of type char
}

int h(int x) = x+1  # h() is of type int, x is of type int

main {
	stdio.println(h(n), \  # comment here too
		f('123asd') + g('32') + 1)  #--> «123124 f»
	stdio.println(q/z/2**96)  #--> «4294967296.0»
}
