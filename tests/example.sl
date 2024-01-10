# this is a comment
#| and that is a
	multiline one. |#

const u32 n = 123123   # n: const u32 (unsigned 32 bit)
const i64 m = 10**18   # m: const i64 (signed 64 bit)
const int z = 2**128   # z: const int (signed unsized)
const auto q = 2**256  # q: const int (signed unsized)

char f(str x) {        # f(): char, x: str
	auto c = x[1]  # c: char
	return c       # char
}

auto g(str x) {        # g(): char, x: str
	return x[0]    # char
}

int h(int x) = x+1     # h(): int, x: int

main {
	stdio.println(h(n), \  # comment here too
		f('123asd') + g('32') + 1)  #--> «123124 f»
	stdio.println(q/z/2**96)            #--> «4294967296.0»
}
