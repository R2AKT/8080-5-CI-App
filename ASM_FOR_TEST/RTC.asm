#include "RTC.inc"

;;
; Subroutine to Initialize RTC
INITRTC::
	MVI 	A,RTC_RegD			; Set RTC 'registre D' address
	OUT 	RTC_Addr			; Write RTC_RegD address to RTC
	IN	 	RTC_Data			; Read RegD
	ANI		RTC_RegD_VRT		; 'VRT' set ?
	JNZ		RTC_Good				; RTC OK
	;
	MVI 	A,RTC_RegA			; Set RTC 'registre A' address
	OUT 	RTC_Addr			; Write RTC_RegA address to RTC
	MVI 	A,00101010b			; Set OSC - 32.768kHz, OutClk - 64Hz (15.625ms)
	OUT 	RTC_Data			; Write setup to RegA
	;
	MVI 	A,RTC_RegB			; Set RTC 'registre B' address
	OUT 	RTC_Addr			; Write RTC_RegB address to RTC
	MVI 	A,RTC_RegB_SET+RTC_RegB_Binary+RTC_RegB_24hr
								; Stop RTC (SET=1), Disable Periodical Interrupt (OutClk) (PIE=0),
								; Disable Alarm Interrupt (AIE=0), Disable Update Interrupt (UIE=0),
								; Disable SQW output (SQWE=0), binary format (DM=1), 24h format (24/12=1),
								; no winter-summer time correction (DSE=0) 
	OUT 	RTC_Data			; Write setup to RegB
	;;
	; Set default date & time (01-01-70, 00:00:00)
	MVI 	A,RTC_Year			; Set RTC_Year address
	OUT 	RTC_Addr			; Write RTC_Year address to RTC
	MVI 	A,70				; Year - 1970 (or 2070?)
	OUT 	RTC_Data			; Write to Year
	;
	MVI 	A,RTC_Month			; Set RTC_Month address
	OUT 	RTC_Addr			; Write RTC_Month address to RTC
	MVI 	A,01				; Set Month - 01 (Jan.)
	OUT 	RTC_Data			; Write to Month
	;
	MVI 	A,RTC_Day			; Set RTC_Day address
	OUT 	RTC_Addr			; Write RTC_Day address to RTC
	MVI 	A,01				; Day - 01
	OUT 	RTC_Data			; Write to Day
	;
	MVI 	A,RTC_Week			; Set RTC_Week address
	OUT 	RTC_Addr			; Write RTC_Week address to RTC
	MVI 	A,02				; Week - 02 (Monday)
	OUT 	RTC_Data			; Write to Week
	;
	MVI 	A,RTC_Hours			; Set RTC_Hours address
	OUT 	RTC_Addr			; Write RTC_Hours address to RTC
	MVI 	A,00				; Hour - 00
	OUT 	RTC_Data			; Write to Hours
	;
	MVI 	A,RTC_Minutes		; Set RTC_Minutes address
	OUT 	RTC_Addr			; Write RTC_Minutes address to RTC
	MVI 	A,00				; Minutes - 00
	OUT 	RTC_Data			; Setup Minutes
	;
	MVI 	A,RTC_Seconds		; Set RTC_Seconds address
	OUT 	RTC_Addr			; Write RTC_Seconds address to RTC
	MVI 	A,00				; Seconds - 00
	OUT 	RTC_Data			; Setup Seconds
	;
RTC_RAM_Clean:
	XRA		A					; Clean A
	LXI		H,RTC_RAM_start		; Load to HL RTC RAM start address
	CALL	RTC_PutByte			; Write to RTC
	DCX		H					; Increment HL
	MVI		A,RTC_RAM_end+1
	CMP		L					; HL = RTC_RAM_end+1 ?
	JNZ		RTC_RAM_Clean
	;
	STC							; Set 'carry' (RTC error (Lost data!))
	;
RTC_Start:
	MVI 	A,RTC_RegB			; Set RTC 'registre B' address
	OUT 	RTC_Addr			; Write RTC_RegB address to RTC
	MVI 	A,RTC_RegB_PIE+RTC_RegB_SQWE+RTC_RegB_Binary+RTC_RegB_24hr
								; Start RTC (SET=0), Enable Periodical Interrupt (OutClk) (PIE=1),
								; Disable Alarm Interrupt (AIE=0), Disable Update Interrupt (UIE=0),
								; Enable SQW output (SQWE=1), binary format (DM=1), 24h format (24/12=1),
								; no winter-summer time correction (DSE=0) 
	OUT 	RTC_Data			; Write setup to RegB
	;
	RET
RTC_Good:
	ANA		A					; Clean 'carry' (No error)
	JMP		RTC_Start			; Start RTC

;;
; H:L (H = 0x0 (const), L = 0x00-0xFF) - byte address, A - readed value
RTC_GetByte::
	MOV 	A,L					; Copy LSB address (L) to A
	OUT 	RTC_Addr			; Write byte address to RTC
	IN	 	RTC_Data			; Read byte
	RET

;;
; H:L (H = 0x0 (const), L = 0x00-0xFF) - block address, DE - destination, BC (B = 0x0 (const), C = 0x0-0xFF) - byte counter
RTC_GetBlock::
	PUSH	D					; Store destination (DE) to stack
	INR		C					; Check, start
	DCR		C					; counter = 0?
	JZ		RTC_GetBlockErr
RTC_GetBlockReadLoop:
	JZ		RTC_EndBlockRead
	CALL	RTC_GetByte			; Read RTC byte
	STAX	D					; Store byte (A) to destination (DE)
	INX		D					; Increment DE (destination)
	INR		L					; Increment L (source)
	DCR		C					; Decrement C (counter)
	JMP		RTC_GetBlockReadLoop
RTC_GetBlockErr:
	POP		D					; Restore destination (DE) from stack
	STC							; Set 'carry' (RTC error (Lost data!))
	RET
RTC_EndBlockRead:
	POP		D					; Restore destination (DE) from stack
	ANA		A					; Clean 'carry' (No error)
	RET

;;
; H:L (H = 0x0 (const), L = 0x00-0xFF) - byte address, A - writen value
RTC_PutByte::
	MOV 	H,A					; Copy value (A) to H
	MOV 	A,L					; Copy LSB address (L) to A
	OUT 	RTC_Addr			; Write byte address to RTC
	MOV 	A,H					; Copy value (H) to A
	OUT	 	RTC_Data			; Write byte
	RET

;;
; H:L (H = 0x0 (const), L = 0x00-0xFF) - block address, DE - source, BC (B = 0x0 (const), C = 0x0-0xFF) - byte counter
RTC_PutBlock::
	PUSH	D					; Store source (DE) to stack
	INR		C					; Check, start
	DCR		C					; counter = 0?
	JZ		RTC_PutBlockErr
RTC_GetBlockWriteLoop:
	JZ		RTC_EndBlockWrite
	LDAX	D					; Load byte (A) from source (DE)
	CALL	RTC_PutByte			; Write RTC byte
	INX		D					; Increment DE (destination)
	INR		L					; Increment L (source)
	DCR		C					; Decrement C (counter)
	JMP		RTC_GetBlockWriteLoop
RTC_PutBlockErr:
	POP		D					; Restore destination (DE) from stack
	STC							; Set 'carry' (RTC error (Lost data!))
	RET
RTC_EndBlockWrite:
	POP		D					; Restore destination (DE) from stack
	ANA		A					; Clean 'carry' (No error)
	RET
