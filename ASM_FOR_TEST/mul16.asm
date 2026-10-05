;;
; -!!!- WORK -!!!- Checked on https://eliben.org/js8080/
;
; L.Leventhal, W.Saville. 8080/8085 assembly language. Subroutines
;
;;


;; mul16 --
; Multiple of 16-bit positive numbers (HL = HL * DE)
;
; Entry registers
; 		HL - Multipliable
; 		DE - Multiplier
;
; Return registers
;		A - value is lost
; 		BC - value is lost
; 		DE - value is lost
; 		HL - Product
;
MUL16::
	MOV		C,L
	MOV		B,H
	LXI		H,0000
	MVI		A,15
MLP:
	PUSH	PSW
	ORA		D
	JP		MLP1
	DAD		B
MLP1:
	DAD		H
	XCHG
	DAD		H
	XCHG
	POP		PSW
	DCR		A
	JNZ		MLP
	ORA		D
	RP
	DAD		B
	RET
