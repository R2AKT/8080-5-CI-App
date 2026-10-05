#target bin
#charset ascii
.asm8080

;;;;
;;
;; Esc - DeEsc (KISS) implementation for the 580VM80 (i8080) by R2AKT
;;
;;;;

;;
; Definitions
_FEND			EQU		0C0h		;
_FESC			EQU		0DBh		;
_TFEND			EQU		0DCh		;
_TFESC			EQU		0DDh		;

#code MAIN, 0x100, *

;; EscData --
; Escape 0Ch (replace to 0DBDCh) and DBh (replace to 0DBDDh) data from one array location to another.
; Target size MUST be double source size!!!
;
; Entry registers
;       BC - Number of bytes to Esc
;       DE - Address of source unEsc data block
;       HL - Address of target Esc data block
;
; Return registers
;       HL - Esc byte counter
EscData:
		MOV A,B						; Copy register B to register A
		ORA C						; Bitwise OR of A and C into register A
		JZ EscDataNull				; Return if the zero-flag is set high. (Zero size!)
		PUSH H						; Store HL (address pointer)
		MVI H,0h					; Clean byte counter
EscData_loop:
		XTHL						; Exchange stored HL (address pointer) <-> current HL (byte counter)
		LDAX D						; Load A from the address pointed by DE
		CPI _FEND					; A = '_FEND' (0xC0) ?
		JZ EscData_stuf_FEND
		CPI _FESC					; A = '_FESC' (0xDB) ?
		JZ EscData_stuf_FESC		
		MOV M,A						; Store A into the address pointed by HL
EscData_loop_check:
		INX D           			; Increment DE
		INX H          				; Increment HL (address pointer)
		XTHL						; Exchange stored HL (byte counter) <-> current HL (address pointer)
		INX H						; Increment byte counter
		DCX B           			; Decrement BC (does not affect Flags)
		MOV A,B         			; Copy B to A (so as to compare BC with zero)
		ORA C           			; A = A | C (are both B and C zero?)
		JNZ EscData_loop       		; Jump to 'loop:' if the zero-flag is not set.
		POP B						; Dummy unload stack to BC
		RET                 		; Return. HL - byte counter
EscData_stuf_FEND:
		MVI A,_FESC					; Insert '_FESC' (0xDB)
		MOV M,A						; Store A into the address pointed by HL
		INX D           			; Increment DE
		MVI A,_TFEND				; Insert '_TFEND' (0xDC)
		MOV M,A						; Store A into the address pointed by HL
		JMP EscData_loop_check
EscData_stuf_FESC:
		MVI A,_FESC					; Insert '_FESC' (0xDB)
		MOV M,A						; Store A into the address pointed by HL
		INX D           			; Increment DE
		MVI A,_TFESC				; Insert '_TFESC' (0xDD)
		MOV M,A						; Store A into the address pointed by HL
		JMP EscData_loop_check
EscDataNull:
		MVI H,0h					; Set ZERO byte counter
		RET

;; DeEscData --
; DeEscape 0xDBDC (replace to 0C0h) and 0xDBDD (replace to 0DBh) data from one location to another.
; Target size MUST be source size - 2 !!
;
; Entry registers
;       BC - Number of bytes to DeEsc
;       DE - Address of source Esc data block
;       HL - Address of target deEsc data block
;
; Return registers
;       HL - deEsc byte counter
DeEscData:
		MOV A,B						; Copy register B to register A
		ORA C						; Bitwise OR of A and C into register A
		JZ DeEscDataNull			; Return if the zero-flag is set high. (Zero size!)
		PUSH H						; Store HL (address pointer)
		MVI H,0h					; Clean byte counter
DeEscData_loop:
		XTHL						; Exchange stored HL (address pointer) <-> current HL (byte counter)
		LDAX D						; Load A from the address pointed by DE
		CPI _FESC					; A = '_FESC' (0xDB) ?
		JZ DeEscData_replace
		MOV M,A						; Store A into the address pointed by HL
DeEscData_loop_check:
		INX D           			; Increment DE
		INX H          				; Increment HL (address pointer)
		XTHL						; Exchange stored HL (byte counter) <-> current HL (address pointer)
		INX H						; Increment byte counter
		DCX B           			; Decrement BC (does not affect Flags)
		MOV A,B         			; Copy B to A (so as to compare BC with zero)
		ORA C           			; A = A | C (are both B and C zero?)
		JNZ DeEscData_loop     		; Jump to 'loop:' if the zero-flag is not set.   
		POP B						; Dummy unload stack to BC
		RET                 		; Return. HL - byte counter
DeEscData_replace:
		INX D           			; Increment DE
		LDAX D						; Load A from the address pointed by DE
		CPI _TFEND					; A = '_TFEND' (0xDC) ?
		JZ DeEscData_TFEND
		CPI _TFESC					; A = '_TFESC' (0xDD) ?
		JZ DeEscData_TFESC
		POP B						; Dummy unload stack to BC
		MVI H,0
		RET                 		; Error ! Return. HL - byte counter
DeEscData_TFEND:
		MVI A,_FEND					; Insert '_FEND' (0xC0)
		MOV M,A						; Store A into the address pointed by HL
		JMP DeEscData_loop_check
DeEscData_TFESC:
		MVI A,_FESC					; Insert '_FESC' (0xDB)
		MOV M,A						; Store A into the address pointed by HL
		JMP DeEscData_loop_check
DeEscDataNull:
		MVI H,0h					; Set ZERO byte counter
		RET                 		; Return. HL - byte counter
