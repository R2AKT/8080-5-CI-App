;; delay_ms --
; Delay from 1 to 65536 ms
;
; Entry registers
;       HL - Delay
;
; Return registers
;		A - value is lost
;       HL - value is lost
;		DE - value is lost
;
DELAY_ms::
	MOV		A,L					; Copy L to A
	ORA		H					; A = A | H (are both A and H zero?)
	RZ							; Return if the zero-flag is set.
#if CPU_Freq_kHz = 3000
	LXI		D,0084				; 84 - 3.0MHz, 72 - 2.5MHz, 54 - 2.0MHz, 49 - 1.778MHz -!!!- CHECK -!!!-
#elif CPU_Freq_kHz = 2000
	LXI		D,0054				; 84 - 3.0MHz, 72 - 2.5MHz, 54 - 2.0MHz, 49 - 1.778MHz -!!!- CHECK -!!!-
#elif CPU_Freq_kHz = 1778
	LXI		D,0049				; 84 - 3.0MHz, 72 - 2.5MHz, 54 - 2.0MHz, 49 - 1.778MHz -!!!- CHECK -!!!-
#else ; 2.5 MHz
	LXI		D,0072				; 84 - 3.0MHz, 72 - 2.5MHz, 54 - 2.0MHz, 49 - 1.778MHz -!!!- CHECK -!!!-
#endif
delay_ms_loop:
	DCX 	D					; Decrement DE
	MOV 	A,D					; Copy D to A
	ORA 	E					; A = A | L (are both A and L zero?)
	JNZ 	delay_ms_loop		; Jump to 'delay_1ms_loop' if the zero-flag is not set.
;
	DCX		H					; Decrement HL
	MOV		A,H					; Copy H to A
	ORA		L					; A = A | L (are both A and L zero?)
	JNZ		DELAY_ms			; Jump to 'delay_ms' if the zero-flag is not set.
	RET
