# Slang Bytecode


## Standalone

### NOP
0x00
> Does nothing.
### END
0x01
> Closes previously opened block.
### POP
0x02
> Drops `TOS`.
### RET
0x03
> Returns `TOS` to caller.
### BLTIN
0x04
> Reads string from the bytecode until null byte (max 255 bytes) and pushes builtin function with that name.
### CODE
0x05
> Reads code from the bytecode until the corresponding `END` instruction and pushes a reference to it and then its length.
> Opens a block.


## Unary

### POS
0x10
> Pushes `abs(TOS)`.
### NEG
0x11
> Pushes `-TOS`.
### NOT
0x12
> Pushes `!TOS`.
### INV
0x13
> Pushes `~TOS`.
### ATOI
0x14
> Pushes integer of smallest possible width parsed from string `TOS`.
### ITOA
0x15
> Pushes string representation of integer `TOS`.
### ITOF
0x16
> Pushes real of smallest possible width equal to integer `TOS`.
### CEIL
0x17
> Pushes smallest integer of smallest possible width greater or equal to real `TOS`.
### FLR
0x18
> Pushes largest integer of smallest possible width less or equal to real `TOS`.
### RND
0x19
> Pushes integer of smallest possible width equal to rounded `TOS`.
### CTOS
0x1A
> Pushes string consisting of char `TOS` and a null byte.


## Binary

### ADD
0x20
> Pushes `TOS1 + TOS`.
### SUB
0x21
> Pushes `TOS1 - TOS`.
### MUL
0x22
> Pushes `TOS1 * TOS`.
### DIV
0x23
> Pushes `TOS1 / TOS`.
### IDIV
0x24
> Pushes `TOS1 // TOS`.
### MOD
0x25
> Pushes `TOS1 % TOS`.
### POW
0x26
> Pushes `TOS1 ** TOS`.
### LSH
0x27
> Pushes `TOS1 << TOS`.
### RSH
0x28
> Pushes `TOS1 >> TOS`.
### AND
0x29
> Pushes `TOS1 & TOS`.
### OR
0x2A
> Pushes `TOS1 | TOS`.
### XOR
0x2B
> Pushes `TOS1 ^ TOS`.


## Comparisons

### EQ
0x30
> Pushes `TOS1 == TOS`.
### NE
0x31
> Pushes `TOS1 != TOS`.
### LT
0x32
> Pushes `TOS1 < TOS`.
### GT
0x33
> Pushes `TOS1 > TOS`.
### LE
0x34
> Pushes `TOS1 <= TOS`.
### GE
0x35
> Pushes `TOS1 >= TOS`.
### IS
0x36
> Pushes `TOS1 is TOS`.
### ISNOT
0x37
> Pushes `TOS1 is not TOS`.


## Flow control
### IF
0x40
> If `TOS` is false, skips bytecode until corresponding `ELSE` (if exists) or `END`.
> Opens a block.
### ELSE
0x41
> Pops last `IF` result from `IF`-stack, and if it is true, skips bytecode to corresponding `END`.
> Opens a block.
### EXEC
0x42
> Executes code block `TOS1` of length `TOS` and pushes the result.


## With argument

### ALLOC*(bytes)*
0xA0
> Pushes reference to `calloc(1, bytes)`.
### EXTEND*(bytes)*
0xA1
> Extends integer `TOS` width to `bytes` bytes if narrower.
### CONST*(bytes)*
0xA2
> Reads next `bytes` bytes of bytecode and pushes a reference to a copy of them.
### JUMPF*(offset)*
0xA3
> Jumps `offset` bytes of bytecode forward.
### JUMPB*(offset)*
0xA4
> Jumps `offset` bytes of bytecode backward.
### SCPGET*(cell)*
0xA5
> Pushes the value of cell `cell` of local scope variables array.
### SCPSET*(cell)*
0xA6
> Sets the value of cell `cell` of local scope variables array to `TOS`.
### CALL*(nargs)*
0xA7
> Calls `TOS` with `nargs` arguments popped from stack (below the callable).
