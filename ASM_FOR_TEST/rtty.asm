#target bin
#charset ascii
.asm8080

;#define CPU_Freq_kHz 3000		; Set CPU frequency to 3.0MHz for time constant's
#define CPU_Freq_kHz 2500		; Set CPU frequency to 2.5MHz for time constant's
;#define CPU_Freq_kHz 2000		; Set CPU frequency to 2.0MHz for time constant's
;#define CPU_Freq_kHz 1778		; Set CPU frequency to 1.778MHz for time constant's

CR				EQU		27
LF 				EQU		28
NUMBERS 		EQU		29
ENG_LET 		EQU		30
RUS_LET			EQU		31

TxModeNone		EQU		0
TxModeFigure	EQU		1
TxModeLat		EQU		2
TxModeRus		EQU		3

#define RTTY_45 45
#define RTTY_50 50
#define RTTY_75 75
#define RTTY_100 100

#define NATO75 0
#define NATO100 1
#define Commercial425 2
#define Commercial450 3
#define HAM45 4
#define HAM50 5
#define HAM75N 6
#define HAM75W 7
#define NBDP 8
#define NBDP_Telex 9

#define StopBitLen 2 ; 1 = 1, 2 = 1.5, 3 = 2

#define SetRTTYMode Commercial450 ; NATO75, NATO100, Commercial425, Commercial450, HAM45, HAM50, HAM75N, HAM75W, NBDP, NBDP_Telex

#if SetRTTYMode = NATO75 ; CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 2210; // CF 2210
#define shiftFreqHz 850; // Frequency shift 850 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_75);
#define symbolLen 5;

#elif SetRTTYMode = NATO100 ; CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 2210; // CF 2210
#define shiftFreqHz 850; // Frequency shift 850 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_100);
#define symbolLen 5;

#elif SetRTTYMode = Commercial425 ; CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 2210; // CF 2210
#define shiftFreqHz 425; // Frequency shift 425 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_50);
#define symbolLen 5;

#elif SetRTTYMode = Commercial450 ; CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 2000;2210; // CF 2210
#define shiftFreqHz 450; // Frequency shift 450 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_50);
#define symbolLen 5;

#elif SetRTTYMode = HAM45 ; CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 2210; //2210; // CF 2210
#define shiftFreqHz 170; // Frequency shift 170 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_45);
#define symbolLen 5;

#elif SetRTTYMode = HAM50 ; CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 2210; // CF 2210
#define shiftFreqHz 170; // Frequency shift 170 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_50);
#define symbolLen 5;

#elif SetRTTYMode = HAM75N ; CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 2210; // CF 2210
#define shiftFreqHz 170; // Frequency shift 170 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_75);
#define symbolLen 5;

#elif SetRTTYMode = HAM75W ; CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 2210; // CF 2210
#define shiftFreqHz 850; // Frequency shift 850 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_75);
#define symbolLen 5;

#elif SetRTTYMode = NBDP ; CF, TONES 'MARK' and 'SPACE' (Reverse tone?)
#define centralFreqHz 1700; // CF 2210
#define shiftFreqHz 170; // Frequency shift 170 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_100);
#define symbolLen 7;

#elif SetRTTYMode = NBDP_Telex ; CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 1700; // CF 2210
#define shiftFreqHz 170; // Frequency shift 170 Hz
#define markFreqHz centralFreqHz + (shiftFreqHz/2);
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2);
#define toneDurationMs (1000/RTTY_50);
#define symbolLen 7;

#else ; Manual. CF, TONES 'MARK' and 'SPACE'
#define centralFreqHz 2210; // CF 2210
#define shiftFreqHz 170; // Frequency shift 85/170 Hz NARROW / (425/850)) HzWIDE
#define markFreqHz centralFreqHz + (shiftFreqHz/2); // 'Mark' frequency  2125 Hz
#define spaceFreqHz centralFreqHz - (shiftFreqHz/2); // 'Space' frequency 2295 Hz
#define toneDurationMs (1000/RTTY_45); // 'Mark'/'Space' tone duration
#define symbolLen 5;
#endif

;;
; Start bit duration
StartBitDuration = toneDurationMs

;;
; Stop bit duration
#if StopBitLen = 1
StopBitDuration = toneDurationMs
#elif StopBitLen = 2
StopBitDuration = ((toneDurationMs*3)/2)
#elif StopBitLen = 3
StopBitDuration = (toneDurationMs*2)
#endif

;;
; Calculate loop counter
StartBitLoopCount = ((StartBitDuration*spaceFreqHz)/2000)
StopBitLoopCount = ((StopBitDuration*markFreqHz)/2000)
MarkLoopCount = ((toneDurationMs*markFreqHz)/2000)
SpaceLoopCount = ((toneDurationMs*spaceFreqHz)/2000)

;;
; Calculate tone counter
#if CPU_Freq_kHz = 3000
StopBitToneCount = (62400/ markFreqHz); Calculate tone counter value (62400/tone) F_CPU = 3.0MHz
StartBitToneCount = (62400/spaceFreqHz)
MarkToneCount = (62400/markFreqHz)
SpaceToneCount = (62400/spaceFreqHz)
#elif CPU_Freq_kHz = 2000
StopBitToneCount = (41600/ markFreqHz); Calculate tone counter value (41600/tone) F_CPU = 2.0MHz
StartBitToneCount = (41600/spaceFreqHz)
MarkToneCount = (41600/markFreqHz)
SpaceToneCount = (41600/spaceFreqHz)
#elif CPU_Freq_kHz = 1778
StopBitToneCount = (36900/ markFreqHz); Calculate tone counter value (36900/tone) F_CPU = 1.778MHz
StartBitToneCount = (36900/spaceFreqHz)
MarkToneCount = (36900/markFreqHz)
SpaceToneCount = (36900/spaceFreqHz)
#else ; 2.5 MHz
StopBitToneCount = (52000/ markFreqHz); Calculate tone counter value (52000/tone) F_CPU = 2.5MHz
StartBitToneCount = (52000/spaceFreqHz)
MarkToneCount = (52000/markFreqHz)
SpaceToneCount = (52000/spaceFreqHz)
#endif

;;
;
#code MAIN, 	0800h,*
;;
; Main code
	STC							; Set 'C' for generation 'MARK'.
	CALL	Tune				; Tune (Generate 'MARK' tone)
	;
	LXI		B,03				; Set 'Sync' count to 3
	CALL	Sync				; Generate 'Sync'
	;
	MVI		A,CR				; 'CR' char
	CALL	TxChar				; Sent char
	;
	MVI		A,LF				; 'LF' char
	CALL	TxChar				; Sent char
	;
CharLooop:
	MVI		A,04				; 'R'
	CALL	TxChar				; Sent char
	MVI		A,06				; 'Y'
	CALL	TxChar				; Sent char
	JMP 	CharLooop
	;
	LXI		H,TxModeLat			; Set HL to current mode ('TxModeLat')
	;
	LXI		D,Message			; Load to DE Message address pointer
MessageLoop:
	PUSH	H					; Store HL (TxMode) in stack
	;
	LDAX 	D					; Load to A (Message char) from the address pointed by DE
	;-!!!-
	CPI		0FFh				; 'Message char' = 0xFF?
	JZ		StopMessage
	;
	PUSH	D					; Store DE (Message address pointer) in stack
	;
	CPI		21h					; 'Message char' < 0x20 (LF,CR)?
	JC		LowChar
	CPI		41h					; 'Message char' < 0x40 ((0x20-0x40)' !"#$%&'()*+,-./0123456789:;<=>?@') ?
	JC		FigureChar
	CPI		5Bh					; 'Message char' < 0x5A ((0x41-0x5A)'ABCDEFGHIJKLMNOPQRSTUVWXYZ') ?
	JC		LatChar
	CPI		7Bh					; 'Message char' < 0x7A ((0x61-0x7A)'abcdefghijklmnopqrstuvwxyz') ?
	JC		LatCharCorr
	;
	MVI		A,09				; Load '*' char (unknow char)
	JMP		FigureChar	
	;
StartTxChar:
	CALL	TxChar				; Send A (Message char)
	POP		D					; Restore DE (Message address pointer) from stack
	POP		H					; Restore HL (TxMode) from stack
	INX		D					; Increment DE (Message address pointer)
	JMP		MessageLoop

;;
;
LatCharCorr:
	SUI		20h					; Correct low case to up case
LatChar:
	PUSH	PSW					; Store A ('Message char') in stack
	MVI		A,TxModeLat			; Required 'TxMode'
	CMP		L					; Current 'TxMode' = Required 'TxMode' ?
	JZ		SkipLatCharSet		; Skip mode change
	;
	POP		D					; Restore DE (Message address pointer) from stack
	POP		H					; Restore HL (TxMode) from stack
	MOV		L,A					; Copy L (New 'TxMode') to A (current 'TxMode')
	PUSH	H					; Store HL (TxMode) in stack
	PUSH	D					; Store DE (Message address pointer) in stack
	;
	CALL	TxMode				; Set 'TxModeLat' mode
SkipLatCharSet:
	POP		PSW					; Restore A ('Message char') from stack
	JMP		StartTxChar

;;
;
FigureChar:
	PUSH	PSW					; Store A ('Message char') in stack
	MVI		A,TxModeFigure
	CMP		L					; Current 'TxMode' = Required 'TxMode' ?
	JZ		SkipGigureCharSet	; Skip mode change
	;
	POP		D					; Restore DE (Message address pointer) from stack
	POP		H					; Restore HL (TxMode) from stack
	MOV		L,A					; Copy L (New 'TxMode') to A (current 'TxMode')
	PUSH	H					; Store HL (TxMode) in stack
	PUSH	D					; Store DE (Message address pointer) in stack
	;
	CALL	TxMode				; Set 'TxModeFigure' mode
SkipGigureCharSet:
	POP		PSW					; Restore A ('Message char') from stack
	JMP		StartTxChar

;;
;
LowChar:
	;PUSH	PSW					; Store A ('Message char') in stack
	MVI		A,TxModeFigure
	CMP		L					; Current 'TxMode' = Required 'TxMode' ?
	JZ		SendLowChar			; Skip mode change
	;
	POP		D					; Restore DE (Message address pointer) from stack
	POP		H					; Restore HL (TxMode) from stack
	MOV		L,A					; Copy L (New 'TxMode') to A (current 'TxMode')
	PUSH	H					; Store HL (TxMode) in stack
	PUSH	D					; Store DE (Message address pointer) in stack
	;
	CALL	TxMode				; Set 'TxModeFigure' mode
SendLowChar:
	;POP		PSW					; Restore A ('Message char') from stack	
	MVI		A,09				; Load '*' char (unknow char)
	JMP		StartTxChar

;;
; Set Tx mode.
TxMode:
	CPI		TxModeNone
	JZ		SetModeNone			; Mode 'None'
	CPI		TxModeFigure
	JZ		SetModeFigure		; Mode 'Figure'
	CPI		TxModeLat
	JZ		SetModeLat			; Mode 'Lat'
	CPI		TxModeRus
	JZ		SetModeRus			; Mode 'Rus'
	;JMP		TxModeNone
SetModeNone:
	MVI		A,ENG_LET			; 'Sync' char (ENG LETTERS)
	CALL	TxChar				; Sent char	
	RET
SetModeFigure:
	MVI		A,NUMBERS			; 'Sync' char (FIGURE (NUMBERS))
	CALL	TxChar				; Sent char
	RET
SetModeLat:
	MVI		A,ENG_LET			; 'Sync' char (ENG LETTERS)
	CALL	TxChar				; Sent char
	RET
SetModeRus:
	MVI		A,RUS_LET			; 'Sync' char (ENG LETTERS)
	CALL	TxChar				; Sent char
	RET
;;
;
StopMessage:
	POP		H					; Restore HL (TxMode) from stack (DUMMY)
	;
	;MVI	A,TxModeLat			; 'Sync' char (ENG LETTERS)
	;CALL	TxMode				; Set 'TxModeLat' mode
	;
	LXI		B,03				; Set 'Sync' count to 3
	CALL	Sync				; Generate 'Sync'
	;
	MVI		A,CR				; 'CR' char
	CALL	TxChar				; Sent char
	;
	MVI		A,LF				; 'LF' char
	CALL	TxChar				; Sent char
	;
	HLT
	JMP		StopMessage
;;
; Send char from A. Value of A, BC, DE, HL lost !!!
TxChar:
	ADD		A					; Double char address!
#if symbolLen = 7
	ADI		01					; Shift to 1 byte on table for NBDP!
#endif
	MVI		B,00				; B = 0
	MOV		C,A					; Copy A to C
	LXI		H,MTK2Table			; Load to HL MTK2Table address pointer
	DAD		B					; HL = HL + BC
	MOV		B,H					; Copy H to B
	MOV		C,L					; Copy L to C
	LDAX	B					; Load to A (MTK2 sequency) from the address pointed by BC
	MVI		B,00				; B = 0
	MVI		C,symbolLen			; Load symbol bit len to C
	PUSH	PSW					; Store A (Symbol) in stack
	PUSH	B					; Store BC (Symbol bit len) in stack
	; Generate 'Start' bit
	LXI		H,StartBitToneCount	; HL = 'Start bit' tone counter
	LXI		D,StartBitLoopCount	; DE = 'Start bit' loop counter
	CALL	ToneGen
	;
	POP		B					; Restore BC (Symbol bit len) from stack
	POP		PSW					; Restore A (Symbol) from stack
	;
BitLoop:
	RLC							; Shift char to left
	PUSH	PSW					; Store A in stack (letter char)
	PUSH	B					; Store BC in stack (bit counter)
	; Modulation
	JC		MarkToneGen			; Generate 'MARK' if C = 1
	; else Generate 'SPACE'
	LXI		H,SpaceToneCount	; HL = Space tone counter
	LXI		D,SpaceLoopCount	; DE = Space loop counter
	;
	CALL	ToneGen				; Generate 'SPACE'
	JMP		EndModulation
	;
MarkToneGen:
	LXI		H,MarkToneCount		; HL = Mark tone counter
	LXI		D,MarkLoopCount		; DE = Mark loop counter
	;
	CALL	ToneGen				; Generate 'MARK'
	JMP		EndModulation
	;
EndModulation:
	POP		B					; Restore BC from stack (bit counter)
	DCX		B					; Decrement BC (bit counter)
	MOV		A,B					; Copy B to A
	ORA		C					; A = A | C (are both A and C not zero?)
	JZ		EndTxChar			; Jump end, Bit counter = 0
	POP		PSW					; Restore A from stack (letter char)
	JMP		BitLoop
	;
EndTxChar:
	; Generate 'Stop' bit
	LXI		H,StopBitToneCount	; HL = 'Stop bit' tone counter
	LXI		D,StopBitLoopCount	; DE = 'Stop bit' loop counter
	;
	CALL	ToneGen
	;
	POP		PSW					; Restore A from stack (DUMMY)
	RET	

;;
; Send 'Sync' sequency. BC = 'Sync' loop counter. A, BC, DE, HL lost !!!
Sync:
	MOV		A,B					; Copy B to A
	ORA		C					; A = A | C (are both A and C not zero?)
	JNZ		SyncLoop
	LXI		B,03				; Set 'Sync' counter = 3
SyncLoop:
	PUSH	B					; Store BC (Sync counter) in stack
	;
	MVI		A,TxModeLat			; Load to A 'Sync' char (ENG LETTERS)
	CALL	TxMode				; Set 'TxModeLat' mode
	;
	POP		B					; Restore BC (Sync counter) from stack
	DCX		B					; Decrement BC
	MOV		A,B					; Copy B to A
	ORA		C					; A = A | C (are both A and C not zero?)
	JNZ		SyncLoop
	RET

;;
;
Tune:
	JC		TuneMarkToneGen		; Generate 'MARK' if C = 1
	; else Generate 'SPACE'
	LXI		H,SpaceToneCount	; HL = Space tone counter
	LXI		D,SpaceToneCount*40	; DE = Space loop counter
	CALL	ToneGen
	RET
TuneMarkToneGen:
	; Generate 'MARK'
	LXI		H,MarkToneCount		; HL = Mark tone counter
	LXI		D,MarkLoopCount*40	; DE = Mark loop counter
	CALL	ToneGen
	RET	

;;
; Tone generator. A, DE, HL lost !!!
ToneGen:
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
	JNZ		ToneGen				; Jump to 'ToneGen' if the zero-flag is not set.
	RET
	
;;
;
#code PlayStream, *
Message:
	;DB	00, 255, 00, 255, 55h, 55h
	DB	0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,0xFF
	;DB	00, 255, 00, 255, 55h, 55h
	;DB	' !',22h,'#$%&',27h,'()*+,-./0123456789',3Ah, 3Bh, 3Ch, 3Dh, 3Eh, 3Fh, 40h,'ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_',60h ,'abcdefghijklmnopqrstuvwxyz', 0
	;DB	'-?:$3!@#8*().,9014"57=2/6+ ',0
	;DB	00, 255, 00, 255, 55h, 55h
	;DB	'Test text by 580VM80a',0xFF

;;
;
#code MTK2Table, *
#include "rtty_nbdp.inc"

;;
;
#code AppInfo, *
SW_Name:		DM	"RTTY/NBDP modulator",0xFF
SW_CopyRight:	DM	"Software copyright (C) 2025-2026 R2AKT",0
SW_License:		DM	"Software licensed under MIT",0
SW_Version		DM	"v.0.0.1",0
SW_Date			DM	"Creation date & time: ", __date__ , ", ", __TIME__, 0
