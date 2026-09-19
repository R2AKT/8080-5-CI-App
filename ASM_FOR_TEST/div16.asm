;;
; -!!!- WORK -!!!- Checked on https://eliben.org/js8080/
;
; L.Leventhal, W.Saville. 8080/8085 assembly language. Subroutines
; Modified by R2AKT, 26/12/2025 (change bit counter)
;
;;

;; div16 --
; Division of 16-bit unsigned numbers (HL = HL / DE, DE = DE % HL)
;
; Entry registers
; 		HL - Divisible
; 		DE - Divisor
;
; Return registers
;		A - value is lost
; 		BC - value is lost
; 		HL - Quotient
; 		DE - Remainder
; 
DIV16::
	MOV		A,E
	ORA		D
	JNZ		DIVIDE
	LXI		H,0000
	MOV		D,H
	MOV		E,L
	STC
	RET
DIVIDE:
	MOV		C,L
	MOV		B,H
	LXI		H,0000
	MVI		A,16
	ORA		A
DVLOOP:
	PUSH	PSW
	MOV		A,C
	RAL
	MOV		C,A
	MOV		A,B
	RAL
	MOV		B,A
	MOV		A,L
	RAL
	MOV		L,A
	MOV		A,H
	RAL
	MOV		H,A
	PUSH	H
	MOV		A,L
	SUB		E
	MOV		L,A
	MOV		A,H
	SBB		D
	MOV		H,A
	CMC
	JC		DROP
	XTHL
	INX		SP
	INX		SP
	POP		PSW
	ORA		A
	DCR		A
	JNZ		DVLOOP
	JMP		END
DROP:
	INX		SP
	INX		SP
	POP		PSW
	STC
	DCR		A
	JNZ		DVLOOP
END:
	XCHG
	MOV		A,C
	RAL
	MOV		L,A
	MOV		A,B
	RAL
	MOV		H,A
	ORA		A
	RET
