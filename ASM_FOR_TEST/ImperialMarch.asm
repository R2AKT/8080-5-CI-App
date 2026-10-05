#target bin
#charset ascii
.asm8080

;#define CPU_Freq_kHz 3000		; Set CPU frequency to 3.0MHz for time constant's
#define CPU_Freq_kHz 2500		; Set CPU frequency to 2.5MHz for time constant's
;#define CPU_Freq_kHz 2000		; Set CPU frequency to 2.0MHz for time constant's
;#define CPU_Freq_kHz 1778		; Set CPU frequency to 1.778MHz for time constant's

#code MAIN, 	0800h,*
MainStart:
	LXI 	D,Notes				; Load to DE note's address pointer
	LXI 	B,Times				; Load to BC time's address pointer
MainLoop:
	LDAX 	D					; Load A (Note's) from the address pointed by DE
	MOV 	L,A					; Copy A to L (LSB)
	INX 	D					; Increment DE
	LDAX 	D					; Load A from the address pointed by DE
	MOV 	H,A					; Copy A to H (MSB)
	; HL = Tone
	PUSH	H					; Store HL (Note's) in stack
;
	LDAX 	B					; Load A (Time's) from the address pointed by BC
	MOV 	L,A					; Copy A to L (LSB)
	INX 	B					; Increment BC
	LDAX 	B					; Load A from the address pointed by BC
	MOV 	H,A					; Copy A to H (MSB)
	ORA 	L					; A = A | L (are both A and L zero?)
	JZ 		TimesEnd			; Jump to 'TimesEnd' if the zero-flag is set.
	; HL = Duration
	XCHG						; DE <-> HL
	; HL = Note's pointer
	; DE = Duration
	; ST = Tone
	XTHL
	; HL = Tone
	; DE = Duration
	; ST = Note's pointer
	PUSH	B					; Store BC (Time's pointer) in stack
	XCHG						; DE <-> HL
	; HL = Duration
	; DE = Tone
	PUSH	H					; Store HL (duration (time's)) to stack
;
	CALL	TONE				; HL - Duration, DE - Tone
	POP		H					; Restore HL from stack (HL = pause duration)
	;DAD		H					; Double duration (pause)
	CALL	Delay_ms			; Delay (pause)
;
	POP		B					; Restore BC (Time's pointer) from stack
	POP		D					; Restore DE (Note's pointer) from stack
;
	INX 	B					; Increment BC
	INX 	D					; Increment DE
;
	JMP		MainLoop
;		
;;
TimesEnd:
	INX		SP					; Unload B from stack
	INX		SP					; Unload C from stack
	JMP		Stop				; Jump to exit
Stop:
	DI							; Disable Interrupts
StopLoop:
	HLT							; Halt
	JMP 	StopLoop			; Loop

;;
;
#include "delay.asm"
#include "mul16.asm"
#include "div16.asm"
#include "tone.asm"

;;
;
#code PlayStream, *
;_START	DW		0xFFFF
Notes:
;; Imperial March
;	DW	392, 392, 392, 311, 466, 392, 311, 466, 392
;	DW	587, 587, 587, 622, 466, 369, 311, 466, 392
;	DW	784, 392, 392, 784, 739, 698, 659, 622, 659
;	DW	415, 554, 523, 493, 466, 440, 466, 311, 369
;	DW	311, 466, 392, 0
;; Pirates of the Caribbean
	DW	146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,293,220,261,293
	DW	293,293,329,349,349,349,391,329,329,293,261,261,293,220,261,293,293,293,329,349,349,349
	DW	391,329,329,293,261,293,220,261,293,293,293,349,391,391,391,440,466,466,440,391,440,293
	DW	293,329,349,349,391,440,293,293,349,329,329,349,293,329,220,261,293,293,293,329,349,349
	DW	349,391,329,329,293,261,261,293,220,261,293,293,293,329,349,349,349,391,329,329,293,261
	DW	293,220,261,293,293,293,349,391,391,391,440,466,466,440,391,440,293,293,329,349,349,391
	DW	440,293,293,349,329,329,293,261,293,293,329,329,349,349,391,440,349,293,220,466,349,293
	DW	220,293,349,349,440,349,349,440,391,329,391,329,440,349,440,349,349,440,391,349,329,293
	DW	293,329,349,391,440,391,349,329,349,391,440,391,349,391,440,391,349,329,349,329,293,329
	DW	261,293,293,329,349,329,349,391,349,391,440,391,349,293,293,329,349,391,440,466,293,391
	DW	349,391,329,293,329,261,440,440,440,440,440,440,391,391,349,329,349,329,293,440,466,440
	DW	440,440,440,391,391,349,329,349,329,293,220,293,349,440,220,293,349,466,220,293,349,440
	DW	440,523,440,391,391,349,329,349,329,293,220,293,349,440,220,293,349,466,220,293,349,440
	DW	440,523,440,391,391,349,329,349,329,293,0
;;;
Times:
;; Imperial March
;	DW	350, 350, 350, 250, 100, 350, 250, 100, 700
;	DW	350, 350, 350, 250, 100, 350, 250, 100, 700
;	DW	350, 250, 100, 350, 250, 100, 100, 100, 450
;	DW	150, 350, 250, 100, 100, 100, 450, 150, 350
;	DW	250, 100, 750, 0
;; Pirates of the Caribbean
	DW	205,102,205,102,205,102,102,102,102,205,102,205,102,205,102,102,102,102,307,102,102,205
	DW	205,102,102,205,205,102,102,205,205,102,102,102,205,102,102,205,205,102,102,205,205,102
	DW	102,205,205,102,102,307,102,102,205,205,102,102,205,205,102,102,205,205,102,102,102,205
	DW	102,102,205,205,205,102,205,102,102,205,205,102,102,307,102,102,205,205,102,102,205,205
	DW	102,102,205,205,102,102,102,205,102,102,205,205,102,102,205,205,102,102,205,205,102,102
	DW	307,102,102,205,205,102,102,205,205,102,102,205,205,102,102,102,205,102,102,205,205,205
;;DW    102,205,102,102,307,102,102,102,205,179,26,205,205,205,205,409,102,102,409,409,205,614
	DW  102,205,102,102,307,102,102,102,205,179,205,205,205,205,205,409,102,102,409,409,205,614
	DW 	307,307,307,205,205,205,102,102,205,205,205,102,102,205,205,205,102,102,205,205,205,307
	DW	102,102,307,102,205,205,205,205,205,205,205,409,102,102,307,102,205,205,205,205,307,102
	DW	205,205,102,102,307,102,205,205,205,205,205,205,205,205,102,102,205,205,205,205,205,205
	DW	307,102,205,307,102,205,205,205,205,205,205,102,102,205,205,205,205,205,409,205,205,205
	DW	205,205,102,102,205,205,205,205,205,205,102,102,102,205,102,102,102,307,102,102,102,205
	DW	205,205,102,102,205,205,205,205,205,205,102,102,102,205,102,102,102,307,102,102,102,205
	DW	205,205,102,102,205,205,205,205,205,409,0
;;
;
SW_Name:		DM	"8080TonePlayer",0
SW_CopyRight:	DM	"Software copyright (C) 2025 R2AKT",0
SW_License:		DM	"Software licensed under MIT",0
SW_Version		DM	"v.0.0.1 BETA",0
SW_Date			DM	"Creation date & time: ", __date__ , ", ", __TIME__, 0
Song_Name:		DM	"The Imperial March (Darth Vader's Theme), Pirates of the Caribbean",0
