;;
; -!!!- WORK -!!!- Checked on https://eliben.org/js8080/
;;

;; div8 --
; Division of 16-bit positive numbers (H = E / D, C = E % D)
;
; Entry registers
; 		E - Divisible
; 		D - Divisor
;
; Return registers
;		A - value is lost
; 		B - value is lost
; 		D - value is lost
; 		E - value is lost
; 		L - value is lost
; 		H - Quotient
; 		C - Remainder
;
DIV8::
	LXI 	H,0008
	MVI 	C,00
M1:
	MOV 	A,E
	RAL
	MOV 	E,A
	MOV 	A,C
	RAL
	SUB 	D
	JNC 	M2
	ADD 	D
M2:
	MOV 	C,A
	CMC
	MOV 	A,H
	RAL
	MOV 	H,A
	DCR 	L
	JNZ 	M1
	RET
