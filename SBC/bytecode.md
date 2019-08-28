# Slang Bytecode


## Standalone

### NOP
0x00
> Does nothing.
### RET
0x01
> Returns `TOS` to caller.


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
0x1a
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
### FLRDIV
0x24
> Pushes `TOS1 // TOS`.
### MOD
0x25
> Pushes `TOS1 % TOS`.
### POW
0x26
> Pushes `TOS1 ** TOS`.
### SHL
0x27
> Pushes `TOS1 << TOS`.
### SHR
0x28
> Pushes `TOS1 >> TOS`.
### AND
0x29
> Pushes `TOS1 & TOS`.
### OR
0x2a
> Pushes `TOS1 | TOS`.
### XOR
0x2b
> Pushes `TOS1 ^ TOS`.


## With argument

### ALLOC*(bytes)*
0xa0
> Pushes reference to `calloc(1, bytes)`.
### EXTEND*(bytes)*
0xa1
> Extends integer `TOS` width to `bytes` bytes if narrower.
### CONST*(bytes)*
0xa2
> Reads next `bytes` bytes of bytecode and pushes a reference to a copy of them.
### JUMPF*(offset)*
0xa3
> Jumps `offset` bytes of bytecode forward.
### JUMPB*(offset)*
0xa4
> Jumps `offset` bytes of bytecode backward.
### SCPGET*(cell)*
0xa5
> Pushes the value of cell `cell` of local scope variables array.
### SCPSET*(cell)*
0xa6
> Sets the value of cell `cell` of local scope variables array to `TOS`.
### CALL*(nargs)*
0xa7
> Pops `nargs ^ (1 << 7)` TODO