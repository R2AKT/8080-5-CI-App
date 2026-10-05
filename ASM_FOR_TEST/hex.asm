;;
; L.Leventhal, W.Saville. 8080/8085 assembly language. Subroutines
;
;;

;; bin2hex --
; Convert binary to ASCII HEX
;
; Entry registers
; 		A - binary input
;
; Return registers
; 		HL - ASCII HEX code
;
;		A - value is lost
; 		BC - value is lost
bin2hex::
	MOV		B,A
	ANI		0F0h
	RRC
	RRC
	RRC
	RRC
	CALL	NASCII
	MOV		H,A
	;
	MOV		A,B
	ANI		0F0h
	CALL	NASCII
	MOV		L,A
	RET
;;
NASCII:
	CPI		10
	JC		NAS1
	ADI		7
NAS1:
	ADI		'0'
	RET

;; hex2bin --
; Convert ASCII HEX to binary
;
; Entry registers
; 		HL - ASCII HEX code input
;
; Return registers
; 		A - binary
;
;		HL - value is lost
; 		BC - value is lost
hex2bin::
	MOV		A,L
	CALL	A2HEX
	MOV		B,A
	MOV		A,H
	RLC
	RLC
	RLC
	RLC
	ORA		B
	RET
;;
A2HEX:
	SUI		'0'
	CPI		10
	JC		A2HEX1
	SUI		7
A2HEX1:
	RET

