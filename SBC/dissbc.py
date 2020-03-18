#!/usr/bin/python3
# SBC Disassembler

from utils.nolog import *

opcodes = {int(m[2], 16): m[1] for m in re.finditer(r'### (\w+).*?\n(\w+)', open(os.path.join(os.path.dirname(sys.argv[0]), 'bytecode.md')).read())}
HASARG = 0xa0

def dissbc(code, no_opnames=False):
	cp = 0
	codesize = len(code)
	blocklvl = 0
	while (cp < codesize):
		opcode = code[cp]; cp += 1
		opname = opcodes.get(opcode)
		if (opname == 'END'): blocklvl -= 1
		print('\t'*blocklvl, end='')
		if (opname is None): print("\033[2mUNKNOWN: %02x\033[0m" % opcode); continue
		print(f"\033[1m0x{opcode:02x}{' '+opname if (not no_opnames) else ''}\033[0m", end='')
		if (opcode > HASARG):
			arg = code[cp]; cp += 1
			print("(%d|0x%02x)" % (arg, arg), end='')

		if (opname == 'CONST'):
			const = code[cp:cp+arg]
			cp += arg
			print(':', '0x'+const.hex(), end='')
			print(' |', str().join(chr(i) if (32 <= i < 128) else '.' for i in const), end='')
		elif (opname == 'BLTIN'):
			name = bytearray()
			while (code[cp] != 0):
				name.append(code[cp]); cp += 1
			else: cp += 1
			print(':', name.decode('ascii'), end='')

		if (opname in ('IF', 'ELSE', 'CODE')):
			print(':', end='')
			blocklvl += 1

		print()

@apmain
@aparg('file', metavar='<file.sbc>')
@aparg('--no-opnames', action='store_true')
def main(cargs):
	dissbc(open(cargs.file, 'rb').read(), no_opnames=cargs.no_opnames)

if (__name__ == '__main__'): exit(main(nolog=True), nolog=True)

# by Sdore, 2020
