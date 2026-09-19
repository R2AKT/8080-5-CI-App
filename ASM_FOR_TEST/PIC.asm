;;
; PIC (8259) software implementation by R2AKT
; Use ZASM assembler (https://github.com/Megatokio/zasm) for compilation
;

;;
; IVT_BASE = Interrupt vector base address (A15-A5), A4-A0 calculated by PIC

#include "PIC.inc"
;
; Subroutine to Initialize 8259 IRQ Controller (Single)
;
INIT8259::
	MVI		A,IVT_BASE_LSB+ICW1_D4+ICW1_SINGL+ICW1_ADI	;+ICW1_IC4	; Init (ICW1): LSB (A7-A5) IVT Base Address, Init, Single mode, Edge triger, Call interval 4 byte, ICW4 enable
	OUT		PIC8259_CP			; Send ICW1 (A0=0)
	MVI		A,IVT_BASE_MSB		; Init (ICW2): MSB (A15-A8) IVT Base Address
	OUT		PIC8259_SP			; Send ICW2 (A0=1)
	;
	;MVI		A,00000000b			; Init (ICW4): Not nested mode, unbuff, normal EOI, 8080 mode
	;OUT		PIC8259_SP			; Send ICW4 (A0=1)
	;
	;MVI		A,00000000b			; Setup (OCW1): Reset interrupt MASK
	;OUT		PIC8259_SP			; Send OCW1 (A0=1)
	;
	MVI		A,OCW2_EOI			; Setup (OCW2): Non-specific EOI, L2-L0 = 0
	OUT		PIC8259_CP			; Send OCW2 (A0=0)
	;
	RET
