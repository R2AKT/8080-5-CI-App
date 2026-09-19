#include "Smyk.inc"

Smyk_Init::
	;; PPI (8255)
	;
	MVI		A,80h					; Mode 0, Port A - out, Port B - out, Port C (Up) - out, Port C (Low) - out
	OUT		PPI8255_SmykCMD			; Set mode
	;
	XRA		A						; Clean A
	OUT		PPI8255_SmykPortA		; Clean Port A
	OUT		PPI8255_SmykPortB		; Clean Port B
	OUT		PPI8255_SmykPortC		; Clean Port C
	;; PIT (8253)
	;
	; Set MODE Ch0 (Smyk Ch0_0)
	MVI 	A,PIT_MOD_Ch0+PIT_MOD_WORD+PIT_MOD_MODE3	; Load Command Ch.0, binary, mode3 (Square Wave Rate Generator), uint16 couter
	OUT 	PIT8253_SmykMOD		; Write to MODE Reg. Ch.
	; Set MODE Ch1 (Smyk Ch0_1)
	MVI 	A,PIT_MOD_Ch1+PIT_MOD_WORD+PIT_MOD_MODE3	; Load Command Ch.1, binary, mode3 (Square Wave Rate Generator), uint16 couter
	OUT 	PIT8253_SmykMOD		; Write to MODE Reg. Ch.1
	; Set MODE Ch2 (Smyk Ch0_2)
	MVI 	A,PIT_MOD_Ch2+PIT_MOD_WORD+PIT_MOD_MODE3	; Load Command Ch.2, binary, mode3 (Square Wave Rate Generator), uint16 couter
	OUT 	PIT8253_SmykMOD		; Write to MODE Reg. Ch.2
	; Set DIVIDE COUNTER Ch0 (F_clk/1000)
	MVI 	A,0E8h				; Load Counter Ch.0 prescaller, LSB
	OUT 	PIT8253_SmykCNT0	; Write LSB prescaller
	MVI 	A,03h				; Load Counter Ch.0 prescaller, MSB
	OUT 	PIT8253_SmykCNT0	; Write LSB prescaller
	; Set DIVIDE COUNTER Ch1 (F_clk/2000)
	MVI 	A,0D0h				; Load Counter Ch.1 prescaller, LSB
	OUT 	PIT8253_SmykCNT1	; Write LSB prescaller
	MVI 	A,07h				; Load Counter Ch.1 prescaller, MSB
	OUT 	PIT8253_SmykCNT1	; Write LSB prescaller
	; Set DIVIDE COUNTER Ch2 (F_clk/4000)
	MVI 	A,0A0h				; Load Counter Ch.2 prescaller, LSB
	OUT 	PIT8253_SmykCNT2	; Write LSB prescaller
	MVI 	A,0Fh				; Load Counter Ch.2 prescaller, MSB
	OUT 	PIT8253_SmykCNT2	; Write LSB prescaller
	;;
	RET
