;;
; Get PC (programm counter) value
;	Retunn  value:
;		- HL - PC value
GetPC::
;GetPC_LAND		EQU		0x0000		; Memory landing address
;	LHLD		GetPC_LAND
;	PUSH		H
;	LDA			GetPC_LAND+2
;	PUSH		PSW
;	LXI			H,0E5E1h
;	SHLD		GetPC_LAND			; (0xE1) POP H
;	MVI			A,0C9h				; (0xE5) PUSH H
;	STA			GetPC_LAND+2		; (0xC9) RET
;	;
;	CALL		GetPC_LAND
;	;
;	RET
;;
;
;	POP			H
;	PUSH		H
;	RET
;;;

