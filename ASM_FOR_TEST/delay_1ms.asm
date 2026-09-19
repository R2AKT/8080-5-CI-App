;; delay_1ms --
; Delay to 1 ms
;
; Entry registers
;       -
;
; Return registers
;		A - value is lost
;		DE - value is lost
;
DELAY_1ms::
#if CPU_Freq_kHz = 3000
	LXI		D,0330				; 330 - 3.0MHz, 282 - 2.5MHz, 222 - 2.0MHz, 197 - 1.778MHz -!!!- CHECK -!!!-
#elif CPU_Freq_kHz = 2000
	LXI		D,0222				; 330 - 3.0MHz, 282 - 2.5MHz, 222 - 2.0MHz, 197 - 1.778MHz -!!!- CHECK -!!!-
#elif CPU_Freq_kHz = 1778
	LXI		D,0197				; 330 - 3.0MHz, 282 - 2.5MHz, 222 - 2.0MHz, 197 - 1.778MHz -!!!- CHECK -!!!-
#else ; 2.5 MHz
	LXI		D,0282				; 330 - 3.0MHz, 282 - 2.5MHz, 222 - 2.0MHz, 197 - 1.778MHz -!!!- CHECK -!!!-
#endif
delay_1ms_loop:
	DCX 	D					; Decrement DE
	MOV 	A,D					; Copy D to A
	ORA 	E					; A = A | L (are both A and L zero?)
	JNZ 	delay_1ms_loop		; Jump to 'delay_1ms_loop' if the zero-flag is not set.
	RET
