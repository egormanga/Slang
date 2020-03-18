// SBC

#define _GNU_SOURCE
#include <ctype.h>
#include <stdio.h>
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "builtins.c"
#include "stack.c"

typedef uint8_t code_t;

enum {
	// Standalone
	NOP	= 0x00,
	END	= 0x01,
	POP	= 0x02,
	RET	= 0x03,
	BLTIN	= 0x04,
	CODE	= 0x05,

	// Unary
	POS	= 0x10,
	NEG	= 0x11,
	NOT	= 0x12,
	INV	= 0x13,
	ATOI	= 0x14,
	ITOA	= 0x15,
	ITOF	= 0x16,
	CEIL	= 0x17,
	FLR	= 0x18,
	RND	= 0x19,
	CTOS	= 0x1A,

	// Binary
	ADD	= 0x20,
	SUB	= 0x21,
	MUL	= 0x22,
	DIV	= 0x23,
	IDIV	= 0x24,
	MOD	= 0x25,
	POW	= 0x26,
	SHL	= 0x27,
	SHR	= 0x28,
	AND	= 0x29,
	OR	= 0x2A,
	XOR	= 0x2B,

	// Comparisons
	EQ	= 0x30,
	NE	= 0x31,
	LT	= 0x32,
	GT	= 0x33,
	LE	= 0x34,
	GE	= 0x35,
	IS	= 0x36,
	ISNOT	= 0x37,

	// Flow control
	IF	= 0x40,
	ELSE	= 0x41,
	EXEC	= 0x42,

	// With argument
	ALLOC	= 0xA0,
	EXTEND	= 0xA1,
	CONST	= 0xA2,
	JUMPF	= 0xA3,
	JUMPB	= 0xA4,
	SCPGET	= 0xA5,
	SCPSET	= 0xA6,
	CALL	= 0xA7,

	HASARG	= 0xA0,
};

atom_t exec(code_t* code, uint32_t codesize) { // TODO: freeing
	stack_t* st = stack();
	atom_t scp[255]; // TODO
	code_t* cb[255]; // TODO
	uint32_t cbi = 0;

	uint32_t cp = 0;
	while (cp < codesize) {
		code_t opcode = code[cp++];
		uint32_t ocp = cp;

		switch (opcode) {
			// Standalone
			case NOP: break;
			case END: break;
			case POP: stack_pop(st); break;
			case RET: return st->top->data;
			case BLTIN: {
				char name[256];
				strncpy(name, (char*)code+cp, 255);
				while (code[cp++] != '\0');
				stack_push(st, (atom_t){.data = get_builtin(name)});
			}; break;
			case CODE: {
				code_t* code_block = malloc(codesize);
				static uint32_t cbp = 0;
				uint32_t blocklvl = 1;
				while (cp < codesize) {
					code_t c = code[cp++];
					if (c == CODE	||
					    c == IF	||
					    c == ELSE) blocklvl++;
					else if (c == END) blocklvl--;
					if (blocklvl <= 0) break;
					code_block[cbp++] = c;
					if (c > HASARG) code_block[cbp++] = code[cp++];
					if (c == CONST)
						for (uint8_t i = code_block[cbp-1]; i > 0; i--)
							code_block[cbp++] = code[cp++];
					else if (c == BLTIN)
						do code_block[cbp++] = code[cp++];
						while (code[cp-1] != '\0');
				}
				cb[cbi++] = realloc(code_block, cbp);
				free(code_block);
				stack_push(st, (atom_t){u32, .u32 = &cbp});
				stack_push(st, (atom_t){.data = &cb[cbi-1]});
			}; break;

			// Unary
			case POS: *st->top->data.i32 = abs(*st->top->data.i32); break;
			case ITOA: {
				char s[12];
				fprintf(stderr, "-- %x\n", *st->top->data.i32);
				snprintf(s, sizeof(s)/sizeof(*s), "%d", *st->top->data.i32);
				st->top->data.data = strdup(s);
			}; break;

			// Binary (TODO)
			case ADD: *st->top->data.i32 += *stack_pop(st).i32; break;
			case SUB: *st->top->data.i32 -= *stack_pop(st).i32; break;

			// Comparisons
			case LT: *st->top->data.b = *stack_pop(st).i32 > *st->top->data.i32; break;

			// Flow control
			case EXEC: {
				uint32_t exec_codesize = *stack_pop(st).u32;
				code_t* exec_code = stack_pop(st).data;
				stack_push(st, exec(exec_code, exec_codesize));
			}; break;

			// With argument
			case CONST: {
				uint8_t len = code[cp++];
				stack_push(st, (atom_t){.data = memcpy(malloc(len), code+cp, len)});
				fprintf(stderr, "-- l=%02x: %x\n", len, *st->top->data.i32);
				cp += len;
			}; break;
			case SCPGET: {
				uint8_t cell = code[cp++];
				stack_push(st, scp[cell]);
			}; break;
			case SCPSET: {
				uint8_t cell = code[cp++];
				scp[cell] = stack_pop(st);
				fprintf(stderr, "-- c%d = %d\n", cell, *scp[cell].i32);
			}; break;
			case CALL: {
				uint8_t nargs = code[cp++];
				fprintf(stderr, "-- nargs=%d\n", nargs);
				builtin_function func = stack_pop(st).data;
				atom_t args[nargs];
				for (uint8_t i = 0; i < nargs; i++)
					args[i] = stack_pop(st);
				stack_push(st, func(nargs, args));
			}; break;

			default: fprintf(stderr, "Not Implemented opcode: 0x%02x\n", opcode); exit(3);
		}

		fprintf(stderr, "[%02x", opcode);
		if (opcode > HASARG) fprintf(stderr, "(%d|0x%02x)", code[ocp], code[ocp++]);
		fputc(':', stderr);
		do fprintf(stderr, " %02x", code[ocp++]);
		while (ocp < cp && ocp < codesize);
		if (st->top != NULL) {
			fprintf(stderr, ", TOS = %u(0x%02x)", *st->top->data.i32, *st->top->data.i32);
			if (isprint(*(char*)st->top->data.data)) {
				fprintf(stderr, " | ");
				for (char* p = st->top->data.data; *p != '\0'; p++)
					fputc(isprint(*p)?*p:'.', stderr);
			}
		}
		fprintf(stderr, "]\n");
	}

	return (atom_t){.data = NULL};
}

int main(int argc, char* argv[]) {
	if (argc != 2) {
		fprintf(stderr, "Usage: %s <file.sbc>\n", basename(argv[0]));
		exit(1);
	}

	FILE* fd = fopen(argv[1], "rb");
	fseek(fd, 0, SEEK_END);
	long fsize = ftell(fd);
	fseek(fd, 0, SEEK_SET);

	code_t code[fsize];
	fread(code, sizeof(*code), fsize, fd);
	fclose(fd);

	exec(code, fsize);
}

// by Sdore, 2020
