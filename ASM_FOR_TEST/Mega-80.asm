#target ram
#charset ascii
.asm8080

;;
;
#include "definition.inc"
#include "MemMap.inc"
#include "APU.inc"

;;
;
;#data VARIABLES, RAM_0, 01DFh
;RTC_Hour 		DS 1
;RTC_Minute  	DS 1
;RTC_Seconds  	DS 1
;RTC_Week 		DS 1
;RTC_Day 		DS 1
;RTC_Month 		DS 1
;RTC_Year 		DS 2
;RTC_UnixTime 	DS 4

;; Internal interrupt vector table
; 
#code RST, 		0x0,0x40
	JMP 	MainStart
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
;; External interrupt vector table
;

; IRQ0 - 6
#code Ext_INT0,	ExtVecTable0,0x20
	JMP 	IRQ0ISP				; IRQ0 ISP (PIT)
	DS 		1					; Allign byte
	JMP 	IRQ1ISP				; IRQ1 ISP (KBD)
	DS 		1					; Allign byte
	JMP 	IRQ2ISP				; IRQ2 ISP
	DS 		1					; Allign byte
	JMP 	IRQ3ISP				; IRQ3 ISP
	DS 		1					; Allign byte
	JMP 	IRQ4ISP				; IRQ4 ISP
	DS 		1					; Allign byte
	JMP 	IRQ5ISP				; IRQ5 ISP
	DS 		1					; Allign byte
	JMP 	IRQ6ISP				; IRQ6 ISP
	DS 		1					; Allign byte
; IRQ7 - 14
#code Ext_INT1, ExtVecTable1,0x20
	JMP 	IRQ8ISP				; IRQ8 ISP (IPP0)
	DS 		1					; Allign byte
	JMP 	IRQ9ISP				; IRQ9 ISP (IPP1)
	DS 		1					; Allign byte
	JMP 	IRQ10ISP			; IRQ10 ISP (IPP2)
	DS 		1					; Allign byte
	JMP 	IRQ11ISP			; IRQ11 ISP (IPP3)
	DS 		1					; Allign byte
	JMP 	IRQ13ISP			; IRQ12 ISP (IPP4)
	DS 		1					; Allign byte
	JMP 	IRQ13ISP			; IRQ13 ISP (IPP5)
	DS 		1					; Allign byte
	JMP 	IRQ14ISP			; IRQ14 ISP (IPP6)
	DS 		1					; Allign byte
	JMP 	IRQ15ISP			; IRQ15 ISP (IPP7)
	DS 		1					; Allign byte
;;
;
;;#code _BLANK, 	Ext_INT1_end, BOOT - Ext_INT1_end; - Ext_INT1_end

;; Boot
;
#code BOOT, 	ROM0,*
	DI							; Disable Interrupts
	LXI 	SP,SP_TOP        	; Set Stack Pointer
	
; Clean stdout, Send PostCode = 0h
	MVI 	A,00h
	CALL 	PostCode

;; Restore relocated interrupt vector table to address 0000h (RAM!)
;
	;; -!!!- FULL COPY IVT+IRQ -!!!-
	;LXI 	H,0000h				; Destination - Interrupt vector table (RAM)
	;LXI 	D,RST0Addr			; Source - relocated interrupt vector table (ROM 0x0)
	;LXI 	B,0080h				; 128 byte Int+Ext interrupt vector table
	;CALL 	memcpy
	;; Single copy
	; RST0-RST7
	LXI 	H,0000h				; Destination - Interrupt vector table (RAM 0x0)
	;LXI 	D,RST0Addr			; Source - relocated interrupt vector table (ROM)
	LXI 	D,ROM0				; Source - relocated interrupt vector table (ROM)
	LXI 	B,0040h				; Software interrupt vector table (RST0-7)
	CALL 	memcpy
	;; Single PIC
	;LXI 	H,0040h				; Destination - Interrupt vector table (RAM 0x40)
	;LXI 	D,ExtVecTable0		; Source - relocated interrupt vector table (ROM 0x40)
	;LXI 	B,0020h				; Software interrupt vector table (IRQ0-7)
	;CALL 	memcpy
	;; Dual PIC
	; PIC1
	LXI 	H,0040h				; Destination - Interrupt vector table (RAM 0x40)
	LXI 	D,ExtVecTable0		; Source - relocated interrupt vector table (ROM 0x40)
	LXI 	B,001Bh				; Software interrupt vector table (IRQ0-6)
	CALL 	memcpy
	; PIC2
	LXI 	H,RAM_TOP			; Destination - Interrupt vector table (RAM 0x8000)
	LXI 	D,ExtVecTable1		; Source - relocated interrupt vector table (ROM 0x60)
	LXI 	B,0020h				; Software interrupt vector table (IRQ0-7)
	CALL 	memcpy	

;; Initialize hardware
;
; Send PostCode = 10h
	MVI 	A,10h
	CALL 	PostCode

	CALL 	INIT8253			; Setup PIT

; Send PostCode = 11h
	MVI 	A,11h
	CALL 	PostCode
	
	CALL 	INIT8259_0			; Setup IRQ controller (0)

; Send PostCode = 12h
	MVI 	A,12h
	CALL 	PostCode

	CALL 	INIT8259_1			; Setup IRQ	controller (1)

; Send PostCode = 13h
	MVI 	A,13h
	CALL 	PostCode

	CALL 	INITUSART			; Setup USART
	
; Send PostCode = 14h
	MVI 	A,14h
	CALL 	PostCode

	CALL 	INIT8237			; Setup DMA 16k
	
; Send PostCode = 15h
	MVI 	A,15h
	CALL 	PostCode

	CALL 	INIT8257			; Setup DMA 64k
	
; Send PostCode = 16h
	MVI 	A,16h
	CALL 	PostCode

	CALL 	INIT8255			; Setup PPI

; Send PostCode = 17h
	MVI 	A,17h
	CALL 	PostCode

	CALL 	INIT8279			; Setup KBD

; Send PostCode = 18h
	MVI 	A,18h
	CALL 	PostCode

	CALL 	INITRTC				; Setup RTC

; Send PostCode = 18h
	MVI 	A,18h
	CALL 	PostCode
;;
; Make FIFO
	; USART RX
	LXI 	H,USART_RX_FIFO_Addr; Load FIFO address pointer to HL
	XCHG						; HL<->DE
	LXI 	B,USART_RX_FIFO_Size; Load FIFO size
	CALL 	fifo_make			; Make FIFO
; Send PostCode = 20h
	MVI 	A,20h
	CALL 	PostCode
	; USART TX
	LXI 	H,USART_TX_FIFO_Addr; Load FIFO address pointer to HL
	XCHG						; HL<->DE
	LXI 	B,USART_TX_FIFO_Size; Load FIFO size
	CALL 	fifo_make			; Make FIFO
; Send PostCode = 21h
	MVI 	A,21h
	CALL 	PostCode
	; LPT
	LXI 	H,LPT_FIFO_Addr		; Load FIFO address pointer to HL
	XCHG						; HL<->DE
	LXI 	B,LPT_FIFO_Size		; Load FIFO size
	CALL 	fifo_make			; Make FIFO
; Send PostCode = 22h
	MVI 	A,22h
	CALL 	PostCode
;		; KBD
	LXI 	H,KBD_FIFO_Addr		; Load FIFO address pointer to HL
	XCHG						; HL<->DE
	LXI 	B,KBD_FIFO_Size		; Load FIFO size
	CALL 	fifo_make			; Make FIFO
; Send PostCode = 23h
	MVI 	A,23h
	CALL 	PostCode
	; LED
	LXI 	H,LED_FIFO_Addr		; Load FIFO address pointer to HL
	XCHG						; HL<->DE
	LXI 	B,LED_FIFO_Size		; Load FIFO size
	CALL 	fifo_make			; Make FIFO
; Send PostCode = 24h
	MVI 	A,24h
	CALL 	PostCode
;;;
;		; ; APU
;		; LXI H,APU_FIFO_Addr		; Load FIFO address pointer to HL
;		; XCHG						; HL<->DE
;		; LXI B,APU_FIFO_Size		; Load FIFO size
;		; CALL fifo_make			; Make FIFO
; ; Send PostCode = 25h
;		; MVI A,25h
;		; CALL PostCode
;		; ; LCD (LCD2004)
;		; LXI H,LCD_FIFO_Addr		; Load FIFO address pointer to HL
;		; XCHG						; HL<->DE
;		; LXI B,LCD_FIFO_Size		; Load FIFO size
;		; CALL fifo_make			; Make FIFO
; ; Send PostCode = 26h
;		; MVI A,26h
;		; CALL PostCode
;;;

;;
;
	CALL 	LCD_Init			; Initialize LCD (LCD2004)
	; Send PostCode = 30h
	MVI 	A,30h
	CALL 	PostCode

;; Enable Interrupt
;
	EI							; Enable Interrupts
; Send PostCode = 40h
	MVI 	A,40h
	CALL 	PostCode

;; Ready!
;
; Send PostCode = FFh
	MVI 	A,0FFh
	CALL 	PostCode
;;
;
#code MAIN, 	ROM0,*
;;;
;		LXI D,0000h					; Source 0000h
;		;
;		LXI H,0500h					; Destination 0500h
;		;
;		LXI B,0064h 				; Size 64h
;		;
;		CALL memcpy		
;;;
;		LXI H,0520h					; Destination 0520h
;		;
;		LXI B,0064h					; Size 64h
;		;
;		MVI D,0AAh					; Value AAh
;		;
;		CALL memset
;;;
;		LXI H,0008h					; Destination 0800h
;		;
;		MVI D,0AAh					; Value AAh
;		;
;		MOV M,D						; Store D into the address pointed by HL
;		;
;		INR D						; Increment D
;		INX H						; Increment HL
;		;
;		MOV M,D						; Store E into the address pointed by HL
;		; Mem 0800h = AAABh
;;;
;		MOV A,A
;		MOV B,B
;		MOV C,C
;		MOV D,D
;		MOV E,E
;		MOV H,H
;		MOV L,L
;;;
LOOP:
; Echo port 0
	IN 		0
	OUT 	0
;
	HLT							; Halt!
;
	JMP LOOP
;;
; Check CPU = 8080 or Z80?
	; MVI 	A,2
	; ORA 	A       			; Clear the N flag
	; PUSH 	PSW
	; POP 	D
	; ANA 	E       			; If a=0, this is a Z80, else a=2

#code IVT, 		ROM0,*
;; RST1-RST7 ISR Code
;
RST1:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	MVI 	A,01h
	OUT 	1h
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
	MVI 	A,02h
	OUT 	2h
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
	MVI 	A,03h
	OUT 	3h
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
	MVI 	A,04h
	OUT 	4h
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
	MVI 	A,05h
	OUT 	5h
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
	MVI 	A,06h
	OUT 	6h
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
	MVI 	A,07h
	OUT 	7h
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	POP		PSW					; Restore PSW
	RET                 		; Return

;; IRQ ISR
;
IRQ0ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ1ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ2ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ3ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ4ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ5ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ6ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
;;
;
#code IVT_Local, RAM_TOP,*
IRQ8ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ9ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ10ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ11ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ12ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ13ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ14ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
IRQ15ISP:
	PUSH	PSW					; Save PSW
	PUSH	B					; Save BC
	PUSH	D					; Save DE
	PUSH	H					; Save HL
	;;
	; IRQ programm
	;;
	POP		H					; Restore HL
	POP		D					; Restore DE
	POP		B					; Restore BC
	;
	MVI		A,00100000b			; EOI (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_1CP			; Send OCW2
	;
	POP		PSW					; Restore PSW
	EI							; Enable Interrupts
	RET                 		; Return
;;
;
#code INIT, 	ROM0,*
#include "init_hardware.asm"

;;
;
#code LIB, 		ROM0,*
#include "memlib.asm"
#include "fifo.asm"
#include "LCD.asm"
#include "crc.asm"

;; POST to stdout (port 0)
PostCode:
	PUSH 	PSW            		; Save PSW
	OUT 	0					; Send A to port 0
	POP 	PSW             	; Restore PSW
	RET

;;;
; Constant data
#code MESSAGE, *
Start_Messages  DM	0				; 'Start' byte messages section
GREETING		DM	"It is alive!",0
HW_Name:		DM	"MEGA-580 (MEGA-580) by R2AKT",0
HW_CopyRight:	DM	"Copyright (C) 2024-2025 R2AKT",0
SW_License:		DM	"Software licensed under MIT",0
SW_Version		DM	"Software version 0.0.1 BETA",0
SW_Date			DM	"Creation date & time: ", __date__ , ", ", __TIME__, 0
;
Msg_NoMsg		DM	"No message!",0	; -!!!- MUST BE LAST IN ARRAY -!!!-