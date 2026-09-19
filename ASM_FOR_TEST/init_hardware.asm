;
; Subroutine to Initialize 8237 DMA Controller 16k
;
INIT8237::
	PUSH 	PSW            		; Save PSW
	NOP
	POP 	PSW            		; Restore PSW
	;
	RET
;
; Subroutine to Initialize 8253 PIT
;
INIT8253::							; -!!!- CHECK -!!!-
	; CH0 - IRQ0 timer
	MVI 	A,00110100b     	; Load Command Ch.0, mode2 (Rate Generator), int16
	OUT 	PIT8253MOD			; Write to MODE Reg. Ch.0
	MVI 	A,0FFh				; Load Counter Ch.0 prescaller, LSB
	OUT 	PIT8253CNT0			; Write LSB prescaller
	MVI 	A,0FFh				; Load Counter Ch.0 prescaller, MSB
	OUT 	PIT8253CNT0			; Write LSB prescaller
	; Ch1
	MVI 	A,01110110b     	; Load Command Ch.1, mode3 (Square Wave Rate Generator), int16
	OUT 	PIT8253MOD			; Write to MODE Reg. Ch.1
	MVI 	A,0B7h				; Load Counter Ch.1 prescaller, LSB
	OUT 	PIT8253CNT1			; Write LSB prescaller
	MVI 	A,0Ch				; Load Counter Ch.1 prescaller, MSB
	OUT 	PIT8253CNT1			; Write LSB prescaller
	; Ch2
	MVI 	A,10110110b     	; Load Command Ch.2, mode3 (Square Wave Rate Generator), int16
	OUT 	PIT8253MOD			; Write to MODE Reg. Ch.2
	MVI 	A,0D0h				; Load Counter Ch.2 prescaller, LSB
	OUT 	PIT8253CNT2			; Write LSB prescaller
	MVI 	A,07h				; Load Counter Ch.2 prescaller, MSB
	OUT 	PIT8253CNT2			; Write LSB prescaller
	;
	RET
;
; Subroutine to Initialize 8255 PPI
;
INIT8255::
	MVI 	A,10100110b			; Port A mode 1, output, Port C (upper) output (Control). Port B mode 1, input.
	OUT 	PPI8255CMD			; Write MODE Reg.
	MVI 	A,00000001b			; Set bit INTE PC0 on C port
	OUT 	PPI8255CMD			; Write MODE Reg.
	;
	MVI 	A,00001001b			; Set PC4 (Init)
	OUT 	PPI8255CMD			; Write MODE Reg.
	;
	MVI 	A,00001000b			; Clean PC4 (Init)
	OUT 	PPI8255CMD			; Write MODE Reg.
	;
	RET
;
; Subroutine to Initialize 8257 DMA Controller 64k
;
INIT8257::
	XRA 	A               	; Clean Acc.
	OUT 	DMA8257CLR      	; 8257 MASTER Clean
	MVI 	A,00100000b     	; Load Command WORD
	OUT 	DMA8257CMD      	; Write to COMMAND Reg.
	MVI 	A,10111010b     	; Load Ch.2 mode WORD
	OUT 	DMA8257MOD      	; Init Ch.2 mode
	MVI 	A,10010111b     	; Load Ch.3 mode WORD
	OUT 	DMA8257MOD      	; Init Ch.3 mode
	MVI 	A,8             	; Load Ch.2 byte COUNT
	OUT 	DMA8257CH2CNT   	; Init Ch.2 LOW byte COUNT
	XRA 	A               	; Clean Acc.
	OUT 	DMA8257CH2CNT   	; Init Ch.2 HIGH byte COUNT
	MVI 	A,4             	; Load Ch.3 byte COUNT
	OUT 	DMA8257CH3CNT   	; Init Ch.3 LOW byte COUNT
	XRA 	A               	; Clean Acc.
	OUT 	DMA8257CH3CNT   	; Init Ch.3 HIGH byte COUNT
	MVI 	A,00000011b     	; Load MASK register
	OUT 	DMA8257MSK      	; Init MASK Reg.
	;
	RET                 		; Return

;
; Subroutine to Initialize 8259 IRQ Controller (Master (0))
;
INIT8259_0::
	MVI		A,01010001b			; Init (ICW1): A7-A5 = 010b (0x40), Init, Cascade mode, Edge triger, Call interval 4 byte, ICW4 enable
	OUT		PIC8259_0CP			; Send ICW1 (A0=0)
	MVI		A,00000000b			; Init (ICW2): A15-A8 = 00000000b
	OUT		PIC8259_0SP			; Send ICW2 (A0=1)
	MVI		A,00000000b			; Init (ICW3): No slave = 00000000b
	;MVI	A,10000000b			; Init (ICW3): IRQ7 Slave = 10000000b
	OUT		PIC8259_0SP			; Send ICW3 (A0=1)
	MVI		A,00000000b			; Init (ICW4): Not nested mode, unbuff, normal EOI, 8080 mode
	OUT		PIC8259_0SP			; Send ICW4 (A0=1)
	;
	;MVI		A,00000000b			; Setup (OCW1): Reset interrupt MASK
	;OUT		PIC8259_0SP			; Send OCW1 (A0=1)
	;MVI		A,00100000b			; Setup (OCW2): Non-specific EOI, L2-L0 = 0
	;OUT		PIC8259_0CP			; Send OCW2 (A0=0)
	;
	RET
;
; Subroutine to Initialize 8259 IRQ Controller (Slave (1))
;
INIT8259_1::
	MVI		A,01110011b			; Init (ICW1): A7-A5 = 011b (0x60), Init, Single mode, Edge triger, Call interval 4 byte, ICW4 enable
	OUT		PIC8259_1CP			; Send ICW1 (A0=0)
	MVI		A,00000000b			; Init (ICW2): A15-A8 = 00000000b
	OUT		PIC8259_1SP			; Send ICW2 (A0=1)
	MVI		A,00000111b			; Init (ICW3): Slave ID IRQ7 = 00000111b
	OUT		PIC8259_1SP			; Send ICW3 (A0=1)
	MVI		A,00000000b			; Init (ICW4): Not nested mode, unbuff, normal EOI, 8080 mode
	OUT		PIC8259_1SP			; Send ICW4 (A0=1)
	;
	;MVI		A,00000000b			; Setup (OCW1): Reset interrupt MASK
	;OUT		PIC8259_1SP			; Send OSW1 (A0=1)
	;MVI		A,00100000b			; Setup (OCW2): Non-specific EOI, L2-L0 = 0
	;OUT		PIC8259_1CP			; Send OCW2 (A0=0)
	;
	RET
;
; Subroutine to Initialize 8279 KBD
;
INIT8279::
	PUSH 	PSW            		; Save PSW
	NOP
	POP 	PSW             	; Restore PSW
	RET

#include "RTC.asm"
#include "USART.asm"
#include "PIC.asm"