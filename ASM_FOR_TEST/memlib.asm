;; memcpy --
; Copy a block of memory from one location to another.
;
; Entry registers
;       BC - Number of bytes to copy
;       DE - Address of source data block
;       HL - Address of target data block
;
; Return registers
;       BC - Zero
memcpy::
	MOV		A,B					; Copy register B to register A
	ORA 	C					; Bitwise OR of A and C into register A
	RZ							; Return if the zero-flag is set high. (Zero size!)
memcpy_loop:
	LDAX 	D					; Load A from the address pointed by DE
	MOV 	M,A					; Store A into the address pointed by HL
	INX 	D           		; Increment DE
	INX 	H          			; Increment HL
	DCX 	B           		; Decrement BC (does not affect Flags)
	MOV 	A,B         		; Copy B to A (so as to compare BC with zero)
	ORA 	C           		; A = A | C (are both B and C zero?)
	JNZ 	memcpy_loop       	; Jump to 'loop:' if the zero-flag is not set.   
	RET                 		; Return

;; memset --
; Set a block of memory to value.
;
; Entry registers
;       BC - Number of bytes to set
;       D - Value
;       HL - Address of target data block
;
; Return registers
;       BC - Zero
memset::
	MOV 	A,B					; Copy register B to register A
	ORA 	C					; Bitwise OR of A and C into register A
	RZ							; Return if the zero-flag is set high. (Zero size!)
memset_loop:
	MOV 	M,D					; Store D into the address pointed by HL
	INX 	H           		; Increment HL
	DCX 	B           		; Decrement BC (does not affect Flags)
	MOV 	A,B         		; Copy B to A (so as to compare BC with zero)
	ORA 	C           		; A = A | C (are both B and C zero?)
	JNZ 	memset_loop       	; Jump to 'loop:' if the zero-flag is not set.   
	RET							; Return
