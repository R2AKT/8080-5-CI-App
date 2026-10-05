;;
; USART (8251+8253) software implementation by R2AKT
; Use ZASM assembler (https://github.com/Megatokio/zasm) for compilation
;

;;
; Divisor = PIT_CLK/(BOUD_RATE*16) for prescaller = 16,
; Divisor = PIT_CLK/(BOUD_RATE) for prescaller = 1
;
;	Example:
;	- External ocilator = 1.8432MHz, Speed = 9600:
;		1843200 / (9600*16) = 115200/9600 = 12 (prescaller = 16)
;		1843200 / (9600) = 192 (prescaller = 1)

;;
;
;#define USART_PRESCALER 1
#define USART_PRESCALER 16

;;
;
;#define USART_Rx_Boud 19200
;#define USART_Tx_Boud 19200
#define USART_Rx_Boud 9600
#define USART_Tx_Boud 9600

;;
;
;#define USART_Freq_kHz 1778	; PIT Clk = 1.778MHz
#define USART_Freq_kHz 1843		; PIT Clk = 1.8432MHz
;#define USART_Freq_kHz 2000	; PIT Clk = 2.0MHz
;#define USART_Freq_kHz 2433	; PIT Clk = 2.433MHz
;#define USART_Freq_kHz 2457	; PIT Clk = 2.457MHz
;#define USART_Freq_kHz 24576	; PIT Clk = 2.4576MHz
;#define USART_Freq_kHz 2500	; PIT Clk = 2.5MHz
;#define USART_Freq_kHz 3000	; PIT Clk = 3.0MHz

;;
;
#include "USART.inc"
#include "PIT.inc"

;;
; Subroutine to Initialize & start USART 
INITUSART::
	CALL	INIT8253_BOUDCLK
	CALL	INIT8251_USART
	;
	RET

;;
; Subroutine to Initialize 8251 USART
INIT8251_USART::
	XRA		A					; A = 0 (Dummy squency)
	OUT 	USART8251CMD		; Write to COMMAND Reg.
	OUT 	USART8251CMD		; Write to COMMAND Reg.
	OUT 	USART8251CMD		; Write to COMMAND Reg.
	; Software reset 8251
	MVI		A,USART_CMD_Reset	; Send 'Reset' command
	OUT 	USART8251CMD		; Write to COMMAND Reg.
	; Set USART MODE	
#if USART_PRESCALER = 16
	MVI 	A,01001110b			; Load COMMAND Reg.: Stop 1, No parity, 8 bit, prescaller 16 (*,8N1)
#else
	MVI 	A,01001101b			; Load COMMAND Reg.: Stop 1, No parity, 8 bit, prescaller 1 (*,8N1)
#endif
	OUT 	USART8251CMD		; Write to CMD Reg.
	; Set USART COMMAND
	;MVI 	A,00010000b			; Load COMMAND Reg.: Disable receiver, disable transmiter, clean DTR, clean RTS, clean error
	;OUT 	USART8251CMD		; Write to COMMAND Reg.
	;
	;IN		USART8251CMD		; Read USART Status
	;ANI	USART_ST_TxRdy		; Mask 'Tx Ready'
	;CPI	USART_ST_TxRdy		; 'Tx Ready' clean ?
	;JZ		TxInitNotReady		; Transmiter Ready, exit with error
	;
	MVI 	A,00110111b			; Load COMMAND Reg.: Enable receiver, enable transmiter, set DTR, set RTS, clean error
	;MVI	A,00000101b			; Load COMMAND Reg.: Enable receiver, enable transmiter, clean DTR, clean RTS
	OUT 	USART8251CMD		; Write to COMMAND Reg.
	;
	IN		USART8251CMD		; Read USART Status	
	ANI		USART_ST_TxRdy		; Mask 'TxReady'
	CPI		USART_ST_TxRdy		; 'TxReady' set ?
	JNZ		USARTNotReady		; USART Not Ready, exit with error
	;
	;XRA	A					; A = 0
	;OUT	USART8251DATA		; Dummy write DATA Reg.
	;
	IN		USART8251DATA		; Dummy read DATA Reg.
	;
	XRA		A					; A = 0, clean 'carry' (No error)
	RET
USARTNotReady:
	MVI 	A,00010000b			; Load COMMAND Reg.: Disable receiver, disable transmiter, clean DTR, clean RTS, clean error
	OUT 	USART8251CMD		; Write to COMMAND Reg.
	;
	STC							; Set 'carry' (USART error!)
	RET

;;
;
; Subroutine to Initialize USART Boudrate generator (8253 PIT)
INIT8253_BOUDCLK:
	; Set MODE Ch0 (USART Rx)
	MVI 	A,PIT_MOD_Ch0+PIT_MOD_WORD+PIT_MOD_MODE3	; Load Command Ch.0, binary, mode3 (Square Wave Rate Generator), uint16 couter
	OUT 	PIT8253_USARTMOD	; Write to MODE Reg. Ch.0
	; Set MODE Ch1 (USART Tx)
	MVI 	A,PIT_MOD_Ch1+PIT_MOD_WORD+PIT_MOD_MODE3	; Load Command Ch.0, binary, mode3 (Square Wave Rate Generator), uint16 couter
	OUT 	PIT8253_USARTMOD	; Write to MODE Reg. Ch.1
	; Set MODE Ch2 (CLK/1000)
	MVI 	A,PIT_MOD_Ch2+PIT_MOD_WORD+PIT_MOD_MODE3	; Load Command Ch.0, binary, mode3 (Square Wave Rate Generator), uint16 couter
	OUT 	PIT8253_USARTMOD	; Write to MODE Reg. Ch.2
	; Set DIVIDE COUNTER Ch0
	MVI 	A,CLK_RX_LSB		; Load Counter Ch.0 prescaller, LSB
	OUT 	PIT8253_USARTCNT0	; Write LSB prescaller
	MVI 	A,CLK_RX_MSB		; Load Counter Ch.0 prescaller, MSB
	OUT 	PIT8253_USARTCNT0	; Write LSB prescaller
	; Set DIVIDE COUNTER Ch1
	MVI 	A,CLK_TX_LSB		; Load Counter Ch.1 prescaller, LSB
	OUT 	PIT8253_USARTCNT1	; Write LSB prescaller
	MVI 	A,CLK_RX_MSB		; Load Counter Ch.1 prescaller, MSB
	OUT 	PIT8253_USARTCNT1	; Write LSB prescaller
	; Set DIVIDE COUNTER Ch2
	MVI 	A,0E8h				; Load Counter Ch.2 prescaller, LSB
	OUT 	PIT8253_USARTCNT2	; Write LSB prescaller
	MVI 	A,03h				; Load Counter Ch.2 prescaller, MSB
	OUT 	PIT8253_USARTCNT2	; Write LSB prescaller
	;
	RET

; ;;
; ;
; USART_Start::
	; ; Set USART COMMAND
	; MVI 	A,00000010b			; Load COMMAND Reg.: Disable receiver, disable transmiter, set DTR
	; OUT 	USART8251CMD		; Write to COMMAND Reg.
	; ;
	; IN		USART8251CMD		; Read USART Status
	; ANI		USART_ST_DSR		; Mask 'DSR'
	; CPI		USART_ST_DSR		; 'DSR' set ?
	; JNZ		DCENotReady			; DCE Not Ready, exit with error
	; ;
	; XRA		A					; A = 0, clean 'carry' (No error)
	; RET
; TxNotReady:
	; MVI 	A,00010000b			; Load COMMAND Reg.: Disable receiver, disable transmiter, clean DTR, clean RTS, clean error
	; OUT 	USART8251CMD		; Write to COMMAND Reg.
	; ;
	; STC							; Set 'carry' (USART error (Transmiter not ready!))
	; RET
; DCENotReady:
	; MVI 	A,00010000b			; Load COMMAND Reg.: Disable receiver, disable transmiter, clean DTR, clean RTS, clean error
	; ;MVI 	A,00110111b			; Load COMMAND Reg.: Enable receiver, enable transmiter, set DTR, set RTS, clean error
	; OUT 	USART8251CMD		; Write to COMMAND Reg.
	; ;
	; STC							; Set 'carry' (USART error (DCE not ready!))
	; RET

; ;;
; ;
; USART_Stop::
	; ; Set USART COMMAND
	; MVI 	A,00000000b			; Load COMMAND Reg.: Disable receiver, disable transmiter, clean DTR, clean RTS
	; OUT 	USART8251CMD		; Write to COMMAND Reg.
	; ;
	; RET

; ;;
; ;
; USART_En_Tx::
	; MVI 	A,00100111b			; Load COMMAND Reg.: Enable receiver, enable transmiter, set DTR, set RTS
	; OUT 	USART8251CMD		; Write to COMMAND Reg.
	; ;
	; RET

; ;;
; ;
; USART_Dis_Tx::
	; MVI 	A,00000110b			; Load COMMAND Reg.: Enable receiver, disable transmiter, set DTR, set RTS
	; OUT 	USART8251CMD		; Write to COMMAND Reg.
	; ;
	; RET

;;
;
USART_GetByte::
	IN		USART8251CMD		; Read USART Status
	;
	;ANI		USART_ST_DSR		; Mask 'DSR'
	;CPI		USART_ST_DSR		; 'DSR' set ?
	;JNZ		GetByteErr			; DCE Not Ready, exit with error
	;
	;ANI	USART_ST_OverErr		; Mask 'Overrun'
	;CPI	USART_ST_OverErr		; 'Overrun' set ?
	;JNZ	GetByteErr				; No data, exit with error
	;
	;ANI	USART_ST_FrameErr		; Maks 'Frame error'
	;CPI	USART_ST_FrameErr		; 'Frame error' set ?
	;JNZ	GetByteErr				; No data, exit with error
	;
	ANI		USART_ST_RxRdy		; Mask 'RxReady'
	CPI		USART_ST_RxRdy		; 'RxReady' set ?
	JNZ		GetByteErr			; No data, exit with error
	;
	IN		USART8251DATA		; Read USART Data to A
	;
	ANA		A					; Clean 'carry' (No error)
	RET
GetByteErr:
	;
	;MVI 	A,00110111b			; Load COMMAND Reg.: Enable receiver, enable transmiter, set DTR, set RTS, clean error
	;OUT 	USART8251CMD		; Write to COMMAND Reg.
	;
	XRA		A					; Clean A
	STC							; Set 'carry' (USART error (DCE not ready or no data!))
	RET

;;
;
USART_PutByte::
	PUSH	PSW					; Store A (Data) in stack
	;
	IN		USART8251CMD		; Read USART Status
	ANI		USART_ST_TxRdy		; Mask 'Tx Ready'
	CPI		USART_ST_TxRdy		; 'Tx Ready'	set ?
	JNZ		PutByteErr			; Tx full/Tx disabled/No CTC set, exit with error
	;
	POP		PSW					; Restore A (Data) from stack
	;
	OUT		USART8251DATA		; Write Data to USART
	;
	ANA		A					; Clean 'carry' (No error)
	RET
PutByteErr:
	POP		PSW					; Restore A (Data) from stack
	;
	;MVI 	A,00110111b			; Load COMMAND Reg.: Enable receiver, enable transmiter, set DTR, set RTS, clean error
	;OUT 	USART8251CMD		; Write to COMMAND Reg.
	;
	STC							; Set 'carry' (USART error (DCE not ready or no data!))
	RET

;;
; HL - destination, BC - byte counter
USART_GetBlock::
	PUSH	H					; Store destination (HL) to stack
	MOV		A,B					; Copy B to A
	ORA		C					; A = A | C (are both A and C zero?)
	JZ		USART_GetBlockErr	; Jump if the zero-flag is set.
USART_GetBlockReadLoop:
	JZ		USART_EndBlockRead
	CALL	USART_GetByte		; Read USART byte
	MOV		M,A					; Store byte (A) to destination (HL)
	INX		H					; Increment HL (destination)
	DCX		B					; Decrement BC (counter)
	JMP		USART_GetBlockReadLoop
USART_GetBlockErr:
	POP		H					; Restore destination (HL) from stack
	STC							; Set 'carry' (RTC error (Lost data!))
	RET
USART_EndBlockRead:
	POP		H					; Restore destination (HL) from stack
	ANA		A					; Clean 'carry' (No error)
	RET

;;
; HL - source, BC - byte counter
USART_PutBlock::
	PUSH	H					; Store destination (HL) to stack
	MOV		A,B					; Copy B to A
	ORA		C					; A = A | C (are both A and C zero?)
	JZ		USART_PutBlockErr	; Jump if the zero-flag is set.
USART_PutBlockWriteLoop:
	JZ		USART_EndBlockWrite
	MOV		A,M					; Read byte (A) from source (HL)
	CALL	USART_PutByte		; Write USART byte
	INX		H					; Increment HL (source)
	DCX		B					; Decrement C (counter)
	JMP		USART_PutBlockWriteLoop
USART_PutBlockErr:
	POP		H					; Restore destination (HL) from stack
	STC							; Set 'carry' (RTC error (Lost data!))
	RET
USART_EndBlockWrite:
	POP		H					; Restore destination (HL) from stack
	ANA		A					; Set 'carry' (No error)
	RET
