;;
; L.Leventhal, W.Saville. 8080/8085 assembly language. Subroutines
;
;;

;; bin2bcd --
; Convert binary to BCD
;
; Entry registers
; 		A - binary input
;
; Return registers
; 		HL - BCD code
;
;		A - value is lost
; 		BC - value is lost
bin2bcd::
	MVI		H,0FFh
D100LP:
	INR		H
	SUI		100
	JNC		D100LP
	ADI		100
	;
	MVI		L,0FFh
D10LP:
	INR		L
	SUI		10
	JNC		D10LP
	ADI		10
	;
	MOV		C,A
	MOV		A,L
	RLC
	RLC
	RLC
	RLC
	ORA		C
	;
	MOV		L,A
	RET

;; bcd2bin --
; Convert BCD to binary
;
; Entry registers
; 		A - BCD code input
;
; Return registers
; 		A - binary
;
; 		BC - value is lost
bcd2bin::
	MOV		B,A
	ANI		0F0h
	RRC
	MOV		C,A
	RRC
	RRC
	ADD		C
	MOV		C,A
	;
	MOV		A,B
	ANI		0F0h
	ADD		C
	RET
