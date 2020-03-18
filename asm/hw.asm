bits 64

;section	.rodata
hw: db "hw", 0

.text
global _start
extern puts
_start:
	push	rbp
	mov	rbp, rsp
	lea	rdi, [hw+rip]
	call	puts
	mov	rax, 0
	pop	rbp
	ret
