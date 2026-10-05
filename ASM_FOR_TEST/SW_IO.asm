;;
; Software 8 bit address port I/O implementation by R2AKT
; based on MON85 by Dave Dunfield (1979-2007) and Roman Borik (2012)
; All rights reserved.

#target rom
#charset ascii
.asm8080

#code CODE, *

;;
;
INST:	DS	6			; Save area for "faking" instructions

;; Input from port
; A - data input
; H:L - port number (mask 0x00FF)
INPUT8_STACK::
	LXI		D,00C9h		; 'NOP' + 'RET' instruction
	PUSH	D			; Store DE in stack
	LXI		D,0E1E1h	; 'POP H' + 'POP H'
	PUSH	D			; Store DE in stack
	MOV		D,L			; Copy L (port number) to D
	MVI		E,0DBh		; 'IN' instruction
	PUSH	D			; Store DE in stack
	MVI		H,0000h
	DAD		SP
	PCHL
	;
	;IN		00h
	;POP		H
	;POP		H
	;RET					; [127]
	;NOP
	
;;
INPUT8_RAM::
	MVI		A,0DBh		; 'IN' instruction
	MVI		H,0C9h		; 'RET' instruction
	STA		INST		; Set RAM instruction
	SHLD	INST+1		; Set RAM instruction
	CALL	INST		; Perform the read
	RET
	;
	IN		00h
	RET					; [91]
;;

;; Output to port
; A - data output
; H:L - port number (mask 0x00FF)
OUTPUT8::
	PUSH	PSW			; Store A in stack
	MVI		A,0D3h		; 'OUT' instruction
	MVI		H,0C9h		; 'RET' instruction
	STA		INST		; Set RAM instruction
	SHLD	INST+1		; Set RAM instruction
	POP		PSW			; Restore A from stack
	CALL	INST		; Output the data
	RET

;; Read 2 byte to HL from address pointer in DE
; H:L - Data
; D:E - Address
MEM16R_SW::
	MVI		A,2Ah		; 'LHLD'
	STA		INST		; Set RAM instruction
	MOV		A,E			; Copy E (LSB address) to A
	STA		INST+1		; Store LSB address (Set RAM instruction)
	MOV		A,D			; Copy D (MSB address) to A
	STA		INST+2		; Store MSB address (Set RAM instruction)
	MVI		A,0C9h		; 'RET' instruction
	STA		INST+3		; Set RAM instruction
	CALL	INST		; Output the data
	RET					; [101]

;; Write 2 byte in HL to address pointer in DE
; H:L - Data
; D:E - Address
MEM16W_SW::
	MVI		A,22h		; 'SHLD'
	STA		INST		; Set RAM instruction
	MOV		A,E			; Copy E (LSB address) to A
	STA		INST+1		; Store LSB address (Set RAM instruction)
	MOV		A,D			; Copy D (MSB address) to A
	STA		INST+2		; Store MSB address (Set RAM instruction)
	MVI		A,0C9h		; 'RET' instruction
	STA		INST+3		; Set RAM instruction
	CALL	INST		; Output the data
	RET					; [101]

;; Read 2 byte to HL from address pointer in DE
; H:L - Data
; D:E - Address
MEM16R::
	LDAX	D			; Load A from address pointer by DE
	MOV		L,A			; Copy A to L
	INX		D			; Increment DE
	LDAX	D			; Load A from address pointer by DE
	MOV		H,A			; Copy A to H
	RET					; [38]

;; Write 2 byte in HL to address pointer in DE
; H:L - Data
; D:E - Address
MEM16W::
	MOV		A,L			; Copy L to A
	STAX	D			; Store A to address pointer by DE
	INX		D			; Increment DE
	MOV		A,H			; Copy H to A
	STAX	D			; Store A to address pointer by DE
	RET					; [38]
