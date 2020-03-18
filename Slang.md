# Slang 
<!-- <font size=0>(June, 30 12:04 AM draft)</font> -->

### Example code
<!-- TODO: Slang syntax highlighting -->
```c
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
```

## Tokens

* [Keywords](#Keywords)
* [Identifiers](#Identifiers)
* [Literals](#Literals)
* [Operators](#Operators)
* [Specials](#Specials)

#### Token resolution order

1. Special
2. Operator
3. Literal
4. Keyword
5. Identifier

## Syntax structures

_Note: `*` after syntax unit means any number of them._

### Abstract

* `{[<\n | ;>]* <<expr> <\n | ;>>* [<\n | ;>]*}` — `code`
* `<<expr> | <code>>` — `block`

### Primitive

* `<<literal> | <funccall> | <attrget> | <itemget> | <identifier> | <lambda>>` — `value`
* `<value>\[<value>\]` — `itemget`
* `<(<expr>) | <value> | <operator> <expr> | <expr> <operator> <expr>>` — `expr` (`f(x+3)` is an instance of `expr`, also `f`, `x+3` and `x` are `expr`s too)

### Non-final

* `[modifier]* <type>` — `typedef` (left-hand type definition)
* `[typedef] <identifier> [? | + | * | ** | =<expr>]` — `argdef` (argument definition)
 > `?` — if present then argument value, `none` else.<br>
 > `+` — tuple with at least one argument.<br>
 > `*` — tuple with any number of arguments.<br>
 > `**` — object with keyword arguments.<br>
 > `=` — default value if argument not specified.
* `([<argdef>[, <argdef>]*]) -> <typedef> = <expr>` — `lambda` (lambda function)
* `<<expr>[, <expr>]*[, *<expr>] | *<expr>>` — `callargs`
* `<<identifier>=<expr>[, <identifier>=<expr>]*[, **<expr>] | **<expr>>` — `callkwargs`

### Final (ordered by resolution order)

* `<typedef> <identifier>([<argdef>[, <argdef>]*]) <<code> | = <expr>>` — `funcdef` (function definition)
* `<exprkeyword> [expr]` — `keywordexpr` (keyword expression)
* `<typedef> <identifier> [= <value>]` — `vardef` (variable definition)
* `<identifier> = <value>` — `assignment`
* `<identifier>[, <identifier>]* = <value>` — `unpackassignment`
* `<value>([<callargs> | <callkwargs> | <callargs>, <callkwargs>])` — `funccall` (function call)
* `<expr>` — expr evaluation (only in REPL)
* `if (<expr>) <block>` — `conditional`
* `for (<identifier> in <expr>) <block>` — `forloop`
* `while (<expr>) <block>` — `whileloop`
* `else <block>` — `elseclause`

## Keywords

* `return [expr]` — return from function

### Modifiers

* `const` — immutable/constant variable

### Reserved keywords

* `def`

## Identifiers

Non-empty sequence of alphanumeric characters plus underscore («_»), not starting with a digit character.

Regex: `[_\w][_\w\d]*`

### Data types

* `i8`, `i16`, `i32`, `i64`, `i128` — fixed size integer
* `u8`, `u16`, `u32`, `u64`, `u128` — fixed size unsigned integer
* `f8`, `f16`, `f32`, `f64`, `f128` — fixed size IEEE-754 floating point number
* `uf8`, `uf16`, `uf32`, `uf64`, `uf128` — fixed size unsigned floating point number
* `int` — unsized («big») integer
* `uint` — unsized unsigned integer
* `float` — unsized floating point number
* `ufloat` — unsized unsigned floating point
* `bool` — logical (boolean) value
* `byte` — single byte
* `char` — UTF-8 character
* `str` — UTF-8 string
* `void` — nothing (or anything...)

* `auto` — compile-time type deduction based on value

## Literals

_Note: `*` after syntax unit here means any number of them, `+` means at least one._

* `<<0<b | o | x>><digit+> | <digit+>.<digit*> | <digit*>.<digit+>>` — number
* `<"<character*>" | '<character*>'>` — string

### Literal structures

* `[ <value>[, <value>]* ]` — list
* `( [type] <value>[, [type] <value>]* )` — tuple
* `{ <<key>: <value>>* }` — map

## Operators

* `<operator> <operand>` — unary operators usage
* `<operand> <operator> <operand>` — binary operators usage
* `<operand> <operator>= <operand>` — in-place operator usage

### Character operators

A set of pre-defined character operators:

* `!+-~` — unary charset
* `%&*+-/<=>^|` — binary charset
* `==`, `**`, `//`, `<<`, `>>` — double-char binary operators

### Keyword operators

A set of pre-defined keyword operators:

* `not` — unary keyword operator
* `and`, `or`, `xor`, `is`, `is not`, `to` — binary keyword operators

## Specials

* `#`, `#|`, `|#` — comment specials
* `;` — expr separator special
* `->`, `@.`, `@`, `.`, `:` — attrget optype specials
* `[`, `]` — itemget specials
* `\,?=(){}` — other specials charset

# Footnotes

All character class checks are performed in current locale.

---
_by Sdore, 2020_
