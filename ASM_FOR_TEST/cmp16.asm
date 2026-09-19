;;
; -!!!- WORK -!!!- Checked on https://eliben.org/js8080/
;
; L.Leventhal, W.Saville. 8080/8085 assembly language. Subroutines
;
;;

;; cmp16 --
; Compare of 16-bit unsigned numbers (HL - DE)
;
; Entry registers
; 		HL - Reduced
; 		DE - Subtractible 
;
; Return registers
;	Flags:
;	- Z
;	- C
;	- S
;
; HL = DE - Z=1; S=0; C=0
; HL > DE - Z=0; S=0; C=0
; HL < DE - Z=0; S=1; C=1
;
;		A - value is lost
; 		BC -
; 		DE - value is lost
; 		HL - value is lost
CMP16::
	MOV		A,D
	XRA		H
	JM		DIFF
	MOV		A,L
	SUB		E
	JZ		EQUAL
	MOV		A,H
	SBB		D
	JC		CYSET
	JNC		CYCLR
EQUAL:
	MOV		A,H
	SBB		D
	RET
DIFF:
	MOV		A,L
	SUB		E
	MOV		A,H
	SBB		D
	MOV		A,H
	JNC		CYCLR
CYSET:
	ORI		1
	STC
	RET
CYCLR:
	ORI		1
	RET
