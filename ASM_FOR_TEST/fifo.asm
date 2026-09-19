;; FIFO implementation
FIFO_OK			EQU		00000000b	; FIFO OK
FIFO_ZS			EQU 	00000001b	; FIFO error!
FIFO_FULL		EQU		00000010b	; FIFO full
FIFO_EMPTY		EQU		00000100b	; FIFO empty
FIFO_HALF		EQU		00001000b	; FIFO half
FIFO_OVER		EQU		00010000b	; FIFO overflow

;;
; FIFO structure:
; int FIFO_size, byte FIFO_status, int FIFO_read_index, int FIFO_write_index, byte[FIFO_size] FIFO_data
;

;;
; Entry registers
;       HL - FIFO structure address
;		DE - FIFO size
;
; Return registers
;       A - Status, Carry - error
fifo_make::
	;; Check 'FIFO size'
	;
	MOV 	A,D					; Copy D to A (so as to compare DE with zero)
	ORA 	E					; A = A | E (are both D and E zero?)
	JZ 		fifo_make_null_size	; FIFO Size NULL, ERROR, EXIT!
	PUSH 	D					; Store DE (FIFO size) in stack
	PUSH 	H					; Store HL (FIFO structure address) in stack
	;; Set 'FIFO size'
	;
	MOV 	M,E					; Store E to the address pointed by HL (LSB FIFO Size)
	INX 	H					; Increment HL to FIFO size (FIFO Size (MSB))
	MOV		M,D					; Store D to the address pointed by HL (MSB FIFO Size)
	;; Set FIFO status
	;
	INX 	H					; Increment HL (FIFO Status)
	MVI		M,FIFO_EMPTY		; Set EMPTY to the address pointed by HL (FIFO Status)
	;; Set 'FIFO read index'
	;
	INX 	H					; Increment HL (pointer FIFO read index)
	MOV		B,H					; Copy H to B (pointer FIFO read index (MSB))
	MOV		C,L					; Copy L to C (pointer FIFO read index (LSB))
	POP		H					; Restore HL (FIFO structure address) from stack
	LXI		D,07				; Load FIFO data array offset
	DAD		D					; HL = HL + DE (Array 0 element address pointer)
	XCHG						; HL <-> DE
	MOV		H,B					; Copy B to H (pointer FIFO read index (MSB))
	MOV		L,C					; Copy C yo L (pointer FIFO read index (LSB))
	;
	MOV		M,E					; Store E to the address pointed by HL (Array 0 element address pointer (LSB))
	INX		H					; Increment HL (pointer FIFO read index (MSB))
	MOV		M,D					; Store D to the address pointed by HL (Array 0 element address pointer (MSB))
	;; Set 'FIFO write index'
	;
	INX		H					; Increment HL (pointer FIFO write index (LSB))
	MOV		M,E					; Store E to the address pointed by HL (Array 0 element address pointer (LSB))
	INX		H					; Increment HL (pointer FIFO write index (MSB))
	MOV		M,D					; Store D to the address pointed by HL (Array 0 element address pointer (MSB))
	;; Fill ZERO data
	;
	INX 	H					; Increment HL (Array 0 element address pointer)
	MVI 	D,00h				; Set D (fill byte)
	POP 	B					; Restore BC (FIFO size) from stack
	CALL 	memset
	MVI 	A,FIFO_OK
	;
	ANA		A					; Clear 'carry' (No error)
	RET
fifo_make_null_size:
	MVI 	A,FIFO_ZS
	;
	STC							; Set 'carry' (Error)
	RET

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;
; FIFO Empty
fifo_empty_check::

	RET

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;;;;;;;;;;;;;;;;;;
; Entry registers
;       HL - FIFO structure address
;
; Return registers
;       C - Status
fifo_destroy::
	;; Check 'FIFO size'
	;
	PUSH 	H					; Store FIFO address (HL) in stack
	MOV 	C,M					; Load C from the address HL (FIFO size (LSB))
	INX 	D					; Increment DE
	LDAX 	D					; Load A from the address DE (FIFO size (MSB))
	MOV 	B,A					; Store A (FIFO size (MSB)) in B. 'FIFO size' in BC
	ORA 	C					; A = A | C (are both B and C zero?)
	JZ 		fifo_destroy_null_size; FIFO Size NULL, ERROR, EXIT!
	;; Clean 'FIFO_size', 'FIFO_status', 'FIFO_read_index', 'FIFO_write_index', 'FIFO_data'
	;
	MOV 	C,E					; Copy E to C
	ADI 	07h					; Add offset 7 byte
	MOV 	C,A					; Copy A to C
	MVI 	A,00h				; Clean A (LSB)
	ADC 	B					; Add B to A with carry
	MOV 	B,A					; Store to B (MSB)
	MVI 	D,00h				; Set fill
	POP 	H					; Restore FIFO address to HL
	CALL 	memset
	MVI 	C,FIFO_OK
	JMP 	fifo_destroy_exit
fifo_destroy_null_size:
	POP 	D					; Dummy restore FIFO address (DE) from stack
	MVI 	C,FIFO_ZS
	;JMP fifo_destroy_exit
fifo_destroy_exit:
	RET

;;;;;;;;;;;;;;;;;;;
; Entry registers
;       DE - FIFO structure address
;
; Return registers
;       C - Status
fast_fifo_destroy::
	;; Check 'FIFO size'
	;
	PUSH 	D					; Store FIFO address (DE) in stack
	LDAX 	D					; Load A from the address DE (FIFO size (LSB))
	MOV 	C,A					; Store A (FIFO size (LSB)) in C
	INX 	D					; Increment DE
	LDAX 	D					; Load A from the address DE (FIFO size (MSB))
	MOV 	B,A					; Store A (FIFO size (MSB)) in B. 'FIFO size' in BC
	ORA 	C					; A = A | C (are both B and C zero?)
	JZ 		fifo_fast_destroy_null_size; FIFO Size NULL, ERROR, EXIT!
	;; Clean 'FIFO_size', 'FIFO_status', 'FIFO_read_index', 'FIFO_write_index'
	;
	MVI		B,07h				;
	MVI 	D,00h				; Set fill
	POP 	H					; Restore FIFO address to HL
	CALL 	memset
	MVI 	C,FIFO_OK
	JMP 	fifo_fast_destroy_exit
fifo_fast_destroy_null_size:
	POP 	D					; Dummy restore FIFO address (DE) from stack
	MVI 	C,FIFO_ZS
	;JMP fifo_destroy_exit
fifo_fast_destroy_exit:
	RET
;;;;;;;;;;;;;;;;;;;
;
; Entry registers
;       DE - FIFO structure address
; Return registers
;       A - FIFO data
;		C - FIFO status
fifo_read::
	;; Check 'FIFO size'
	;
	LDAX 	D					; Load A from the address pointed by DE (FIFO Size (LSB))
	MOV 	L,A					; Store A to L (FIFO Size (LSB))
	INX 	D					; Increment pointer (FIFO Size (MSB))
	LDAX 	D					; Load A from the address pointed by DE (FIFO Size (MSB))
	MOV 	H,A					; Store A to H (FIFO Size (MSB)). 'FIFO size' in HL
	ORA 	L           		; A = A | L (are both A and L zero?)
	JZ 		fifo_read_null_size	; FIFO Size NULL, ERROR, EXIT!
	PUSH	H					; Store HL ('FIFO size') to stack
	;; Check 'FIFO status'
	;
	INX 	D					; Increment pointer (FIFO Status)
	LDAX 	D					; Load A from the address pointed by DE (FIFO Status)
	XRI		FIFO_EMPTY			; FIFO empty ? (A xor 'FIFO_EMPTY')
	JZ 		fifo_read_empty		; FIFO EMPTY, EXIT!
	;XRI		FIFO_OVER			; FIFO overflow ? (A xor 'FIFO_OVER')
	;JZ 		fifo_read_overflow	; FIFO OVERFLOW, EXIT!
	;; Clean 'FIFO_OVER' and 'FIFO_FULL' flag in 'FIFO status'
	;
	MVI		A,FIFO_OVER			; A = FIFO_OVER
	ANI		FIFO_FULL			; A = A and FIFO_FULL
	CMA							; A = !A
	MOV		B,A					; Store A to B
	LDAX 	D					; Load A from the address pointed by DE (FIFO Status)
	ORA		B					; A = A & B (!(FIFO_OVER+FIFO_FULL)). Clean 'FIFO_OVER' and 'FIFO_FULL' flag
	STAX 	D					; Store A to the address pointed by DE (FIFO Status)
	;; Read 'FIFO data' value
	;
	INX 	D					; Increment pointer (FIFO Read Index (LSB))
	LDAX 	D					; Load A from the address pointed by DE (FIFO Read Index (LSB))
	MOV 	L,A					; Store A to L (FIFO Read Index (LSB))
	INX 	D					; Increment pointer (FIFO Read Index (MSB))
	LDAX 	D					; Load A from the address pointed by DE (FIFO Read Index (MSB))
	MOV 	H,A					; Store A to H (FIFO Read Index (MSB)). FIFO read index in HL
	MOV 	A,M					; Load A from the address pointed by HL (FIFO data)
	;; Store 'FIFO data' value
	;
	PUSH	PSW					; Store A to stack
	;;
	; 'FIFO Read Index' check
	POP		B					; Restore BC ('FIFO size') from stack
	
	INX 	B					; Increment FIFO read pointer index in BC (FIFO Read Index).

	;;
	;; Store new 'FIFO Read Index'
	;
	MOV 	A,B					; Store C to A (FIFO Read Index (MSB))
	STAX 	D					; Load A from the address pointed by DE (FIFO Read Index (MSB))
	DCX 	D					; Decrement pointer (FIFO Read Index (LSB))
	MOV 	A,C					; Store C to A (FIFO Read Index (LSB))
	STAX 	D					; Store A from the address pointed by DE (FIFO Read Index (LSB))
	;; Restore 'FIFO data' value
	;
	POP		PSW					; Restore A from stack
	JMP 	fifo_read_exit		
fifo_read_empty:
	MVI		A,00h
	MVI 	C,FIFO_EMPTY
	JMP 	fifo_read_exit
;fifo_read_overflow:
;		MVI		A,00h
;		MVI 	C,FIFO_OVER
;		JMP 	fifo_read_exit
fifo_read_null_size:
	MVI		A,00h
	MVI 	C,FIFO_ZS
	;JMP fifo_read_exit
fifo_read_exit:
	RET
;
; Entry registers
;       DE - FIFO structure address
;       A - FIFO Data
; Return registers
;		C - FIFO status
fifo_write::
	;;;
	;PUSH A						; Store A
	;;;
	; Check FIFO size
	LDAX 	D					; Load A from the address pointed by DE (FIFO Size (LSB))
	MOV 	C,A					; Store A to C (FIFO Size (LSB))
	INX 	D					; Increment pointer (FIFO Size (MSB))
	LDAX 	D					; Load A from the address pointed by DE (FIFO Size (MSB))
	MOV 	B,A					; Store A to B (FIFO Size (MSB)). FIFO size in BC
	ORA 	C           		; A = A | C (are both A and C zero?)
	JZ 		fifo_write_null_size; FIFO Size NULL, ERROR, EXIT!
	;; Check FIFO status
	;
	INX 	D					; Increment pointer (FIFO Status)
	LDAX 	D					; Load A from the address pointed by DE (FIFO Status)
	XRI		FIFO_FULL			; FIFO full ? (A xor 'FIFO_FULL')
	JZ 		fifo_write_full		; FIFO FULL, EXIT!
	;; Write data
	;
	INX 	D					; Increment pointer (FIFO Read Index (LSB))
	INX 	D					; Increment pointer (FIFO Read Index (MSB))
	INX 	D					; Increment pointer (FIFO Write Index (LSB))
	LDAX 	D					; Load A from the address pointed by DE (FIFO Write Index (LSB))
	MOV 	C,A					; Store A to C (FIFO Write Index (LSB))
	INX 	D					; Increment pointer (FIFO Write Index (MSB))
	LDAX 	D					; Load A from the address pointed by DE (FIFO Write Index (MSB))
	MOV 	B,A					; Store A to B (FIFO Write Index (MSB)). FIFO write index in BC
	;;;
	;POP A						; Restore A
	;;;
	STAX 	B					; Store A to the address pointed by BC (FIFO data)

fifo_write_index_update:
	INX 	B					; Increment pointer (FIFO Write Index (LSB)). FIFO write index in BC
	DCX 	B					; Decrement pointer (FIFO Write Index (LSB)). FIFO write index in BC
	
	JMP 	fifo_write_exit		
fifo_write_full:
	MVI 	C,FIFO_FULL
	JMP 	fifo_write_exit
fifo_write_null_size:
	MVI 	C,FIFO_ZS
	;JMP fifo_write_exit
fifo_write_exit:
	RET
