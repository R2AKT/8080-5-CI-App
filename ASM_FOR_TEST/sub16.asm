;;
; -!!!- WORK -!!!- Checked on https://eliben.org/js8080/
;
; L.Leventhal, W.Saville. 8080/8085 assembly language. Subroutines
;
;;

;; sub16 --
; Subtraction of 16-bit unsigned numbers (HL = HL - DE)
;
; Entry registers
; 		HL - Reduced
; 		DE - Subtractible 
;
; Return registers
;		A - value is lost
; 		BC -
; 		DE - value is lost
; 		HL - Difference
SUB16::
	MOV		A,L
	SUB		E
	MOV		L,A
	MOV		A,H
	SBB		D
	MOV		H,A
	RET
