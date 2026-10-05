#target rom
#charset ascii
.asm8080

#include "main_boot.inc"

;; Internal interrupt vector table
; 
#code RST, 		0x0,0x40
	JMP 	RST0
	DS 		5					; Allign byte
	JMP 	RST1
	DS 		5					; Allign byte
	JMP 	RST2
	DS 		5					; Allign byte
	JMP 	RST3
	DS 		5					; Allign byte
	JMP 	RST4
	DS 		5					; Allign byte
	JMP 	RST5
	DS 		5					; Allign byte
	JMP 	RST5
	DS 		5					; Allign byte
	JMP 	RST7
	DS 		5					; Allign byte

;;
;
#code _BLANK0, 	RST_end, BOOT - RST_end

;;
;
#code BOOT, 	BootStart,*
RST0:
	DI							; Disable interrupt
	LXI 	SP,SP_TOP        	; Set Stack Pointer

;; Fill RAM to 0x00
;
	LXI 	H,RAM0					; HL (Destination) = RAM0
	LXI 	B,RAM0_Size+RAM1_Size	; BC (Size) = RAM0+RAM1
	MVI		D,00h					; D (Fill value) = 00h
;
memfill_loop:
	MOV 	M,D					; Store D into the address pointed by HL
	INX 	H           		; Increment HL
	DCX 	B           		; Decrement BC (does not affect Flags)
	MOV 	A,B         		; Copy B to A (so as to compare BC with zero)
	ORA 	C           		; A = A | C (are both B and C zero?)
	JNZ 	memfill_loop       	; Jump to 'loop:' if the zero-flag is not set.  

;; CALL User programm
;
UserApp:
	CALL 	MainStart			; User code
;
	JMP		UserApp				; Loop cycle user application

;;
;
#code _BLANK1, 	BOOT_end, IVT - BOOT_end

;;
;
#code IVT, 		IVTStart,*
;; RST1-RST7 ISR Code
;
RST1:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;
	;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	POP		PSW					; Restore PSW
	RET                 		; Return
RST2:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;
	;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	POP		PSW					; Restore PSW
	RET                 		; Return
RST3:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;
	;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	POP		PSW					; Restore PSW
	RET                 		; Return
RST4:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;
	;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	POP		PSW					; Restore PSW
	RET                 		; Return
RST5:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;
	;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	POP		PSW					; Restore PSW
	RET                 		; Return
RST6:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;
	;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	POP		PSW					; Restore PSW
	RET                 		; Return
RST7:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;
	;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	POP		PSW					; Restore PSW
	RET                 		; Return
;;
;
#code _BLANK2, 	IVT_end, LIB - IVT_end

;;
;
#code LIB, 		LibCode,*
#include "memlib.asm"
PostCode:
	OUT 	0					; Send A to port 0
	RET

;;
;
#code _BLANK3, 	LIB_end, MESSAGE - LIB_end

;;
;
#code MESSAGE,	MessageBlock,*

;;
; Constant data
Start_Messages  DM	0xFF				; 'Start' byte messages section
GREETING		DM	"HW&SW test programm.",0
HW_Name:		DM	"MEGA-80 (MEGA-580) by R2AKT",0
HW_CopyRight:	DM	"Copyright (C) 2024-2026 R2AKT",0
SW_License:		DM	"Software licensed under MIT",0
SW_Version		DM	"Software version 0.0.1 BETA",0
SW_Date			DM	"Creation date & time: ", __date__ , ", ", __TIME__, 0
;
Msg_NoMsg		DM	"No message!",0xFF	; -!!!- MUST BE LAST IN ARRAY -!!!-
