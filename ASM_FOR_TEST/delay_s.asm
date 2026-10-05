;; delay_s --
; Delay from 1 to 65536 seconds
;
; Entry registers
;       HL - Delay
;
; Return registers
;		A - value is lost
;       HL - value is lost
;		DE - value is lost
;
DELAY_s::
	MOV		A,L					; Copy L to A
	ORA		H					; A = A | H (are both A and H zero?)
	RZ							; Return if the zero-flag is set.
;
	PUSH	H					; Store delay counter in stack (seconds)
	LXI		H,0995				; Set delay to 995 ms (-!!!-Check value-!!!-)
	CALL	DELAY_ms			; Call delay in ms
	POP		H					; Restore delay counter from stack (seconds)
	DCX		H					; Decrement delay counter
	MOV		A,H					; Copy H to A
	ORA		L					; A = A | L (are both A and L zero?)
	JNZ		DELAY_s				; Jump to 'delay_s' if the zero-flag is not set.
	RET
