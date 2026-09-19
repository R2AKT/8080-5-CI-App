;; Tone --
; Generate tone signal by INTE pin
;
; Entry registers
; 		BC -
; 		DE - Tone
; 		HL - Duration
;
; Return registers
; 		BC - value is lost
; 		DE - value is lost
; 		HL - value is lost
;
TONE::
;; Zero Tone ?
	MOV		A,D					; Copy D to A
	ORA		E					; A = A | E (are both A and E zero?)
	RZ							; Return if the zero-flag is set.
;; Zero Duration ?
	MOV		A,H					; Copy H to A
	ORA		L					; A = A | L (are both A and L zero?)
	RZ							; Return if the zero-flag is set.
;;
	PUSH	D					; Store DE in stack (tone)
	PUSH	D					; Store DE in stack (tone)
	; HL = duration
	LXI		D,0010
	CALL	DIV16				; HL = HL (duration) / DE (10)
	; HL = duration/10
	PUSH	H					; Store HL in stack (duration/10)
	POP		H					; Restore HL from stack (tone)
	; HL = tone
	LXI		D,0010
	CALL	DIV16				; HL = HL (tone) / DE  (10)
	POP		D					; Restore DE from stack (duration/10)
	; DE = duration/10
	; HL = tone/10
	CALL	MUL16				; Multiply HL = DE (duration/10) to HL (tone/10)
	; HL = (duration/10)*(tone/10)
	LXI		D,0020
	CALL	DIV16				; HL = HL ((duration/10)*(tone/10)) to DE (20)
	POP		D					; Restore DE from stack (tone)
	; DE = tone
	; HL = loop counter
	PUSH	H					; Store HL in stack (loop counter)
;
#if CPU_Freq_kHz = 3000
	LXI		H,62400				; Calculate tone counter value (62400/tone) F_CPU = 3.0MHz
#elif CPU_Freq_kHz = 2000
	LXI		H,41600				; Calculate tone counter value (41600/tone) F_CPU = 2.0MHz
#elif CPU_Freq_kHz = 1778
	LXI		H,36900				; Calculate tone counter value (36900/tone) F_CPU = 1.778MHz
#else ; 2.5 MHz
	LXI		H,52000				; Calculate tone counter value (52000/tone) F_CPU = 2.5MHz
#endif
	CALL	DIV16				; HL = HL (52000) divide to DE (tone)
	; HL = tone counter
;
	POP		D					; Restore DE from stack (loop counter)
	; HL = tone counter
	; DE = loop counter
;;	
;	LXI		H,2608				; -!!!- HL = tone counter (2608 -> 20 Hz) -!!!-
;	LXI		D,0008				; -!!!- DE = loop counter -!!!-
;;
;; Zero loop counter ?
	MOV		A,D					; Copy D to A
	ORA		E					; A = A | E (are both A and E zero?)
	RZ							; Return if the zero-flag is set.
;; Zero tone counter ?
	MOV		A,H					; Copy H to A
	ORA		L					; A = A | L (are both A and L zero?)
	RZ							; Return if the zero-flag is set.
;;
ToneLoop:
	EI
	PUSH	H					; Store HL in stack (Tone counter)
ToneLoop1:
	DCX 	H					; Decrement HL (Tone counter)
	MOV 	A,H					; Copy H to A
	ORA 	L					; A = A | L (are both A and L zero?)
	JNZ		ToneLoop1			; Jump to 'ToneLoop1' if the zero-flag is not set.
	POP		H					; Restore HL from stack (Tone counter)
	PUSH	H					; Store HL in stack (Tone counter)		
	DI
ToneLoop0:
	DCX 	H					; Decrement HL (Tone counter)
	MOV 	A,H					; Copy H to A
	ORA 	L					; A = A | L (are both A and L zero?)
	JNZ 	ToneLoop0			; Jump to 'ToneLoop0' if the zero-flag is not set.
;
	POP		H					; Restore HL from stack (Tone counter)
	DCX		D					; Decrement DE (Loop counter)
	MOV 	A,D					; Copy D to A
	ORA 	E					; A = A | E (are both A and L zero?)
	JNZ		ToneLoop			; Jump to 'ToneLoop' if the zero-flag is not set.
	RET
