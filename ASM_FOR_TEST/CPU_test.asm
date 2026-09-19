; Based on prelim.z80 - Preliminary Z80 tests. Copyright (C) 1994  Frank D. Cringle
; Adopted for KR850VM80 by R2AKT 2026

#target ram
#charset ascii
.asm8080

LAB0_MSB		EQU		(LAB1/256) AND 0xFF
LAB0_LSB		EQU		(LAB1) AND 0xFF

NFLAG     		EQU  	0x02

#code CODE, 0x0000
		.ORG	0x0000
CPU_Test::
		MVI		A,1					; test simple compares and z/nz jumps
		CPI		2
		JZ		ERROR_HLT
		CPI		1
		JNZ		ERROR_HLT
		JMP		LAB0
		HLT							; emergency exit
		DB		0FFh
	
LAB0:
		CALL	LAB2				; does a simple call work?
LAB1:
		JMP		ERROR_HLT			; fail
	
LAB2:
		POP		H					; check return address
		MOV		A,H
		CPI		LAB0_MSB			; MSB
		JZ		LAB3
		JMP		ERROR_HLT
LAB3:
		MOV		A,L
		CPI		LAB0_LSB			; LSB
		JZ		LAB4
		JMP		ERROR_HLT

; test presence and uniqueness of all machine registers (except ir)
LAB4:
		LXI		SP,REGS1
		POP		PSW
		POP		B
		POP		D
		POP		H
		LXI		SP,REGS2+8
		PUSH	H
		PUSH	D
		PUSH	B
		PUSH	PSW
;
V		DEFL	0
		REPT	8
		LDA		REGS2+V/2
V		DEFL	V+2
		CPI		V
		JNZ		ERROR_HLT
		ENDM

; test access to memory via (hl)
		LXI		H,HLVAL
		MOV		A,M
		CPI		0A5H
		JNZ		ERROR_HLT
		LXI		H,HLVAL+1
		MOV		A,M
		CPI		03Ch
		JNZ		ERROR_HLT

; test unconditional return
		LXI		SP,STACK
		LXI		H,RETA
		PUSH	H
		RET
		JMP		ERROR_HLT

; test instructions needed for hex output
RETA:
		MVI		A,0FFh
		ANI		0Fh
		CPI		0Fh
		JNZ		ERROR_HLT
		MVI		A,05Ah
		ANI		0Fh
		CPI		0Ah
		JNZ		ERROR_HLT
		RRC
		CPI		05h
		JNZ		ERROR_HLT
		RRC
		CPI		82h
		JNZ		ERROR_HLT
		RRC
		CPI		41h
		JNZ		ERROR_HLT
		RRC
		CPI		0A0h
		JNZ		ERROR_HLT
		LXI		H,01234h
		PUSH	H
		POP		B
		MOV		A,B
		CPI		12h
		JNZ		ERROR_HLT
		MOV		A,C
		CPI		34h
		JNZ		ERROR_HLT
	
; from now on we can report errors by displaying an address

; test conditional call, ret, jp, jr
TCOND	MACRO	FLAG,PCOND,NCOND,REL
		LXI		H,&FLAG
		PUSH	H
		POP		PSW
		C&PCOND	LAB1&PCOND
		CALL	ERROR_HLT
LAB1&PCOND:
		POP		H
		LXI		H,0D7h XOR &FLAG
		PUSH	H
		POP		PSW
		C&NCOND	LAB2&PCOND
		CALL	ERROR_HLT
LAB2&PCOND:
		POP		H
		LXI		H,LAB3&PCOND
		PUSH	H
		LXI		H,&FLAG
		PUSH	H
		POP		PSW
		R&PCOND
		CALL	ERROR_HLT
LAB3&PCOND:
		LXI		H,LAB4&PCOND
		PUSH	H
		LXI		H,0D7h XOR &FLAG
		PUSH	H
		POP		PSW
		R&NCOND
		CALL	ERROR_HLT
LAB4&PCOND:
		LXI		H,&FLAG
		PUSH	H
		POP		PSW
		J&PCOND	LAB5&PCOND
		CALL	ERROR_HLT
LAB5&PCOND:
		LXI		H,0D7h XOR &FLAG
		PUSH	H
		POP		PSW
		J&NCOND	LAB6&PCOND
		CALL	ERROR_HLT
LAB6&PCOND:	
		ENDM

		TCOND	1,C,NC,1
		TCOND	4,PE,PO,0
		TCOND	040h,Z,NZ,1
		TCOND	080h,M,P,0

; test indirect jumps
		LXI		H,LAB7
		PCHL
		CALL	ERROR_HLT

; djnz (and (partially) inc a, inc hl)
LAB7:
		MVI		A,0A5h
		MVI		B,4
LAB8:
		RRC
		DCR		B
		JNZ		LAB8
		CPI		05Ah
		CNZ		ERROR_HLT
		MVI		B,16
LAB9:
		INR		A
		DCR		B
		JNZ		LAB9
		CPI		06Ah
		CNZ		ERROR_HLT
		MVI		B,0
		LXI		H,0
LAB10:
		INX		H
		DCR		B
		JNZ		LAB10
		MOV		A,H
		CPI		1
		CNZ		ERROR_HLT
		MOV		A,L
		CPI		0
		CNZ		ERROR_HLT
;;
;;;;;;;
;;
		ANA		A					; Clean 'carry' (No ERROR_HLT)
		;
		MVI  	A,NFLAG
		ORA  	A       			; Clear the N flag (if Z80)
		PUSH 	PSW
		POP  	D
		ANA  	E
		JZ   	ISZ80
		JMP		IS8080
ISZ80:
		NOP
		;HLT
		JMP		ISZ80
IS8080:
		NOP
		NOP
		;HLT
		JMP		IS8080
;;
		;
		;HLT						; Temperly HALT, remove before intagrate!
		;JMP		CPU_Test			; Temperly JUMP, remove before intagrate!
		;RET
;;
;;;;;;;
;;


;;
;
ERROR_HLT:
		HLT

;;
;
V		DEFL	0
REGS1:
		REPT	8
V		DEFL	V+2
		DB		V
		ENDM

REGS2:	DS		8,0

HLVAL:	DB		0A5h,03Ch

;; skip to next page boundary
;
		.ORG	(($+255)/256)*256
		DS	240
STACK	EQU	$
