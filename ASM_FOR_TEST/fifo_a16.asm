;; FIFO implementation
FIFO_OK			EQU		00000000b	; FIFO OK
FIFO_Err_ZS		EQU 	00000001b	; FIFO error - ZERO SIZE!
FIFO_Err_OS		EQU 	00000010b	; FIFO error - OVER SIZE!
FIFO_EMPTY		EQU		00000100b	; FIFO empty
FIFO_SEM_EMPTY	EQU		00001000b	; FIFO semiempty
FIFO_HALF		EQU		00010000b	; FIFO half
FIFO_SEM_FULL	EQU		00100000b	; FIFO semifull
FIFO_FULL		EQU		01000000b	; FIFO full
FIFO_OVER		EQU		10000000b	; FIFO overflow
;;
FIFO_a16_max_size_mask 	EQU		16			; Maximal FIFO size mask (maximal FIFO size = 65536)
FIFO_a8_max_size_mask 	EQU		8			; Maximal FIFO size mask (maximal FIFO size = 256)
;;
; FIFO structure:
; int FIFO_size_mask, byte FIFO_status, int FIFO_read_index, int FIFO_write_index, byte[FIFO_size_mask] FIFO_data
;

#target bin
#charset ascii
.asm8080

#code CODE, *
;;
; Entry registers
;       HL - FIFO structure address
;		B  - FIFO size 2^n
;
; Return registers
;       A - Status, Carry - error
fifo_a16_make::
	;; Check 'FIFO size'
	;
	MOV		A,B							; Copy B to A
	ORA		A							; A = A|A
	JZ 		fifo_a16_make_null_size			; FIFO Size NULL, ERROR, EXIT!
	CPI		FIFO_a16_max_size_mask+1		; FIFO mask size =< FIFO_a16_max_size_mask (16)
	JNC		fifo_a16_make_over_size			; FIFO Size OVER, ERROR, EXIT!
	;; Generate FIFO mask size in DE
	;
	LXI		D,0000h				; Clear DE
fifo_a16_MaskShift:
	MOV		A,E					; Copy E to A
	STC							; Set 'carry' (Error)
	RAL							; Rotate Left trough Carry
	MOV		E,A					; Copy A to E
	MOV		A,D					; Copy D to A
	RAL							; Rotate Left trough Carry
	MOV		D,A					; Copy A to D
	DCR		B					; Decrement B
	JNZ		fifo_a16_MaskShift
	;; Store 'FIFO size mask'
	;
	MOV 	M,E					; Store E to the address pointed by HL (LSB FIFO Size Mask)
	INX 	H					; Increment HL to FIFO size (FIFO Size (MSB))
	MOV		M,D					; Store D to the address pointed by HL (MSB FIFO Size Mask)
	;; Store FIFO status
	;
	INX 	H					; Increment HL (FIFO Status)
	MVI		M,FIFO_EMPTY		; Set EMPTY to the address pointed by HL (FIFO Status)
	;; Store 'FIFO read index'
	;
	INX 	H					; Increment HL (pointer FIFO read index)
	MVI		M,00				; Set 'FIFO Read Index' (LSB)
	INX 	H					; Increment HL (pointer FIFO read index)
	MVI		M,00				; Set 'FIFO Read Index' (MSB)
	;; Store 'FIFO write index'
	;
	INX 	H					; Increment HL (pointer FIFO write index)
	MVI		M,00				; Set 'FIFO Read Index' (LSB)
	INX 	H					; Increment HL (pointer FIFO write index)
	MVI		M,00				; Set 'FIFO Read Index' (MSB)
	;; Fill ZERO data
	;
	INX 	H					; Increment HL (Array 0 element address pointer)
	MVI 	D,00h				; Set D (fill byte)
	CALL 	memset				; Fill memory addressed by HL, for size in BC, by value in D
	MVI 	A,FIFO_OK			; Return 'FIFO OK' Status
	;
	ANA		A					; Clear 'carry' (No error)
	RET							; [193]
	;; FIFO OVER SIZE
	;
fifo_a16_make_over_size:
	MVI 	A,FIFO_Err_OS		; Return 'FIFO OVERSIZE' Status
	;
	STC							; Set 'carry' (Error)
	RET
	;; FIFO ZERO SIZE
	;
fifo_a16_make_null_size:
	MVI 	A,FIFO_Err_ZS		; Return 'FIFO ZERO SIZE' Status
	;
	STC							; Set 'carry' (Error)
	RET
	
;;;;;;;;;;;;;;;;;;;
;;
; Entry registers
;       HL - FIFO structure address
;		B - FIFO size 2^n
;
; Return registers
;       A - Status, Carry - error
fifo_a16_fast_make::
	;; Check 'FIFO size'
	;
	MOV		A,B					; Copy B to A
	ORA		A					; A = A|A
	JZ 		fifo_a16_fast_make_null_size	; FIFO Size NULL, ERROR, EXIT!
	CPI		FIFO_a16_max_size_mask+1		; FIFO mask size =< FIFO_a16_max_size_mask (16)
	JNC		fifo_a16_fast_make_over_size	; FIFO Size OVER, ERROR, EXIT!
	;; Generate FIFO mask size in DE
	;
	LXI		D,0000h				; Clear DE
fifo_a16_fast_MaskShift:
	MOV		A,E					; Copy E to A
	STC							; Set 'carry' (Error)
	RAL							; Rotate Left trough Carry
	MOV		E,A					; Copy A to E
	MOV		A,D					; Copy D to A
	RAL							; Rotate Left trough Carry
	MOV		D,A					; Copy A to D
	DCR		B					; Decrement B
	JNZ		fifo_a16_fast_MaskShift
	;; Store 'FIFO size mask'
	;
	MOV 	M,E					; Store E to the address pointed by HL (LSB FIFO Size Mask)
	INX 	H					; Increment HL to FIFO size (FIFO Size (MSB))
	MOV		M,D					; Store D to the address pointed by HL (MSB FIFO Size Mask)
	;; Store FIFO status
	;
	INX 	H					; Increment HL (FIFO Status)
	MVI		M,FIFO_EMPTY		; Set EMPTY to the address pointed by HL (FIFO Status)
	;; Store 'FIFO read index'
	;
	INX 	H					; Increment HL (pointer FIFO read index)
	MVI		M,00h				; Set 'FIFO Read Index' (LSB)
	INX 	H					; Increment HL (pointer FIFO read index)
	MVI		M,00h				; Set 'FIFO Read Index' (MSB)
	;; Store 'FIFO write index'
	;
	INX 	H					; Increment HL (pointer FIFO write index)
	MVI		M,00h				; Set 'FIFO Read Index' (LSB)
	INX 	H					; Increment HL (pointer FIFO write index)
	MVI		M,00h				; Set 'FIFO Read Index' (MSB)
	;;
	MVI 	A,FIFO_OK			; Return 'FIFO OK' Status
	;
	ANA		A					; Clear 'carry' (No error)
	RET							; [163]
	;; FIFO OVER SIZE
	;
fifo_a16_fast_make_over_size:
	MVI 	A,FIFO_Err_OS		; Return 'FIFO OVERSIZE' Status
	;
	STC							; Set 'carry' (Error)
	RET
	;; FIFO ZERO SIZE
	;
fifo_a16_fast_make_null_size:
	MVI 	A,FIFO_Err_ZS		; Return 'FIFO ZERO SIZE' Status
	;
	STC							; Set 'carry' (Error)
	RET

;;;;;;;;;;;;;;;;;;;
; Entry registers
;       HL - FIFO structure address
;
; Return registers
;       A - Status, Carry - error
fifo_a16_destroy::
	;; Check 'FIFO size'
	;
	MOV 	C,M					; Load C from the address HL (FIFO size mask (LSB))
	INX 	H					; Increment HL (FIFO structure address)
	MOV 	B,M					; Load B from the address HL (FIFO size mask (MSB))
	MOV		A,B					; Copy B to A
	ORA 	C					; A = A | C (are both B and C zero?)
	JZ 		fifo_a16_destroy_null_size		; FIFO Size NULL, ERROR, EXIT!
	MOV		A,C					; Copy C to A
	ADI		08h					; A = A + 1 (mask correction) + 7 (FIFO structure size)
	MOV		C,A					; Copy A to C
	MOV		A,B					; Copy B to A
	ACI		00h					; A = A + Carry
	;; Clean 'FIFO_size_mask', 'FIFO_status', 'FIFO_read_index', 'FIFO_write_index', 'FIFO_data'
	;
	DCX		H					; Decrement HL (FIFO structure address)
	MVI 	D,00h				; Set D (fill byte)
	CALL 	memset				; Fill memory addressed by HL, for size in BC, by value in D
	MVI 	A,FIFO_OK			; Return 'FIFO OK' Status
	;
	ANA		A					; Clear 'carry' (No error)
	RET							; [115]
fifo_a16_destroy_null_size:
	MVI 	A,FIFO_Err_ZS		; Return 'FIFO ZERO SIZE' Status
	STC							; Set 'carry' (Error)
	RET

;;;;;;;;;;;;;;;;;;;
; Entry registers
;       HL - FIFO structure address
;
; Return registers
;       A - Status, Carry - error
;       HL - FIFO structure address
fifo_a16_fast_destroy::
	;; Check 'FIFO size'
	;
	MOV		C,M					; Load C from the address HL (FIFO size mask (LSB))
	INX 	H					; Increment HL (FIFO structure address)
	MOV 	B,M					; Load B from the address HL (FIFO size mask (MSB))
	MOV		A,B					; Copy B to A
	ORA 	C					; A = A | C (are both B and C zero?)
	JZ 		fifo_a16_fast_destroy_null_size; FIFO Size NULL, ERROR, EXIT!
	;; Clean 'FIFO_size_mask', 'FIFO_status', 'FIFO_read_index', 'FIFO_write_index'
	;
	MVI		M,00h				; Set 'FIFO size mask' (MSB)
	DCX		H					; Decrement HL (FIFO size mask (LSB))
	MVI		M,00h				; Set 'FIFO size mask' (MSB)
	MVI 	A,FIFO_OK			; Return 'FIFO OK' Status
	;
	ANA		A					; Clear 'carry' (No error)
	RET							; [85]
fifo_a16_fast_destroy_null_size:
	DCX		H					; Decrement HL (FIFO structure address)
	;
	MVI 	A,FIFO_Err_ZS		; Return 'FIFO ZERO SIZE' Status
	STC							; Set 'carry' (Error)
	RET

;;;;;;;;;;;;;;;;;;;
;
; Entry registers
;       HL - FIFO structure address
; Return registers
;       A - FIFO data
;		Carry - error, then A - FIFO Status
fifo_a16_read::
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
	PUSH	H					; Store HL in stack (FIFO structure address)
	MOV		E,A					; Store A (FIFO data) to E
	;; Check FIFO size
	;
	MOV		C,M					; Load C from the address pointed by HL (FIFO Size mask (LSB))
	INX 	H					; Increment HL (pointer FIFO Size mask (MSB))
	MOV		A,M					; Load A from the address pointed by HL (FIFO Size mask (MSB))
	ORA 	C           		; A = A | C (are both A and C zero?)
	JZ 		fifo_a16_read_null_size; FIFO Size NULL, ERROR, EXIT!
	;; Check FIFO status
	;
	INX 	H					; Increment HL (pointer FIFO Status)
	MOV		A,M					; Load A from the address pointed by HL (FIFO Status)
	ANI		FIFO_EMPTY			; FIFO empty ? (A xor 'FIFO_EMPTY')
	JNZ 	fifo_a16_read_already_empty		; FIFO EMPTY, EXIT!
	MVI		A,FIFO_FULL			; Load to A 'FIFO Full' status
	CMA							; Invert status
	ANA		M					; A = A & value address pointed by HL (FIFO Status)
	MOV		M,A					; Store A to the address pointed by HL (FIFO Status)
	;; Read Write Index
	;
	LXI		B,0003h				; Load offset (pointer FIFO Write Index (LSB)) to BC
	DAD		B					; HL = HL + BC
	MOV		C,M					; Load C from the address pointed by HL (FIFO Write Index (LSB))
	INX 	H					; Increment HL (pointer FIFO Write Index (MSB))
	MOV		B,M					; Load B from the address pointed by HL (FIFO Write Index (MSB)). FIFO write index in BC
	;; Write data to FIFO
	;
	MOV		A,E					; Restore A from E (FIFO data)
	POP 	H					; Restore HL from stack (FIFO structure address)
	;; Copy HL to DE
	MOV		E,L					; Copy L (FIFO structure address (LSB)) to E
	MOV		D,H					; Copy H (FIFO structure address (MSB)) to D
	;
	DAD		B					; HL = HL + BC
	MOV		M,A					; Store A to the address pointed by HL (FIFO data)
	;; Update Write Index
	;
	;; Restore HL from DE
	XCHG						; DE <-> HL
	;; Read FIFO Size mask
	MOV		E,M					; Load E from address pointed by HL (Size mask (LSB))
	INX 	H					; Increment HL (pointer FIFO Size mask (MSB))
	MOV		D,M					; Load D from address pointed by HL (Size mask (MSB)). FIFO Size mask in DE
	;; BC++
	INX		B					; Increment BC (FIFO Write Index)
	;; DE = BC & DE
	MOV		A,C					; Copy C (FIFO Write Index (LSB)) to A
	ANA		E					; A = A & E
	MOV		E,A					; Copy A to E
	;
	MOV		A,B					; Copy B (FIFO Write Index (MSB)) to A
	ANA		D					; A = A & D
	MOV		D,A					; Copy A to D
	;; Store FIFO Write Index
	LXI		B,0005h				; Load offset (pointer FIFO Write Index (MSB)) to BC
	DAD		B					; HL (FIFO Write Index (LSB))= HL (FIFO Size mask (MSB)) + BC
	;
	MOV		M,D					; Store D to the address pointed by HL (FIFO Write Index (MSB))
	DCX		H					; Decrement HL (pointer FIFO Write Index (LSB))
	MOV		M,E					; Store E to the address pointed by HL (FIFO Write Index (LSB)). FIFO Write Index in DE
	;; Check FIFO Read Index > FIFO Write Index ?
	;
	;; Read FIFO Read Index
	DCX		H					; Decrement HL (pointer FIFO Read Index (MSB))
	MOV		B,M					; Load B from the address pointed by HL (FIFO Read Index (MSB))
	DCX		H					; Decrement HL (pointer FIFO Read Index (LSB))
	MOV		C,M					; Load C from the address pointed by HL (FIFO Read Index (LSB)). FIFO Read index in BC
	;; FIFO Read Index > FIFO Write Index ?
	MOV		A,B					; Copy B (FIFO Read Index (MSB)) to A
	CMP		D					; A (FIFO Read Index (MSB)) > D (FIFO Write Index (MSB))
	JZ		fifo_a16_read_empty	; FIFO is EMPTY!
	MOV		A,C					; Copy C (FIFO Read Index (LSB)) to A
	CMP		E					; A (FIFO Read Index (LSB)) > E (FIFO Write Index (LSB))
	JZ		fifo_a16_read_empty	; FIFO is EMPTY!
	;;
	MVI 	A,FIFO_OK			; Return 'FIFO OK' Status
	RET							; [359]
fifo_a16_read_already_empty:
	POP		H					; Restore HL (FIFO structure address) from stack
	MVI 	A,FIFO_EMPTY		; Return 'FIFO EMPTY' Status
	STC							; Set 'carry' (Error)
	RET
fifo_a16_read_empty:
	MOV		A,M					; Load A from the address pointed by HL (FIFO Status)
	ORI		FIFO_EMPTY			; Set 'FIFO Status' EMPTY
	MOV		M,A					; Store A to the address pointed by HL (FIFO Status)
	MVI 	A,FIFO_FULL			; Return 'FIFO EMPTY' Status
	RET
fifo_a16_read_null_size:
	POP		H					; Restore HL (FIFO structure address) from stack
	MVI 	A,FIFO_Err_ZS		; Set 'FIFO Status' ZERO SIZE
	STC							; Set 'carry' (Error)
	RET
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
	RET

;;;;;;;;;;;;;;;;;;;
;
; Entry registers
;       HL - FIFO structure address
;       A - FIFO Data
; Return registers
;		A - FIFO status, Carry - error
fifo_a16_write::
	PUSH	H					; Store HL in stack (FIFO structure address)
	MOV		E,A					; Store A (FIFO data) to E
	;; Check FIFO size
	;
	MOV		C,M					; Load C from the address pointed by HL (FIFO Size mask (LSB))
	INX 	H					; Increment HL (pointer FIFO Size mask (MSB))
	MOV		A,M					; Load A from the address pointed by HL (FIFO Size mask (MSB))
	ORA 	C           		; A = A | C (are both A and C zero?)
	JZ 		fifo_a16_write_null_size; FIFO Size NULL, ERROR, EXIT!
	;; Check FIFO status
	;
	INX 	H					; Increment HL (pointer FIFO Status)
	MOV		A,M					; Load A from the address pointed by HL (FIFO Status)
	ANI		FIFO_FULL			; FIFO full ? (A xor 'FIFO_FULL')
	JNZ 	fifo_a16_write_already_full		; FIFO FULL, EXIT!
	MVI		A,FIFO_EMPTY		; Load to A 'FIFO Empty' status
	CMA							; Invert status
	ANA		M					; A = A & value address pointed by HL (FIFO Status)
	MOV		M,A					; Store A to the address pointed by HL (FIFO Status)
	;; Read Write Index
	;
	LXI		B,0003h				; Load offset (pointer FIFO Write Index (LSB)) to BC
	DAD		B					; HL = HL + BC
	MOV		C,M					; Load C from the address pointed by HL (FIFO Write Index (LSB))
	INX 	H					; Increment HL (pointer FIFO Write Index (MSB))
	MOV		B,M					; Load B from the address pointed by HL (FIFO Write Index (MSB)). FIFO write index in BC
	;; Write data to FIFO
	;
	MOV		A,E					; Restore A from E (FIFO data)
	POP 	H					; Restore HL from stack (FIFO structure address)
	;; Copy HL to DE
	MOV		E,L					; Copy L (FIFO structure address (LSB)) to E
	MOV		D,H					; Copy H (FIFO structure address (MSB)) to D
	;
	DAD		B					; HL = HL + BC
	MOV		M,A					; Store A to the address pointed by HL (FIFO data)
	;; Update Write Index
	;
	;; Restore HL from DE
	XCHG						; DE <-> HL
	;; Read FIFO Size mask
	MOV		E,M					; Load E from address pointed by HL (Size mask (LSB))
	INX 	H					; Increment HL (pointer FIFO Size mask (MSB))
	MOV		D,M					; Load D from address pointed by HL (Size mask (MSB)). FIFO Size mask in DE
	;; BC++
	INX		B					; Increment BC (FIFO Write Index)
	;; DE = BC & DE
	MOV		A,C					; Copy C (FIFO Write Index (LSB)) to A
	ANA		E					; A = A & E
	MOV		E,A					; Copy A to E
	;
	MOV		A,B					; Copy B (FIFO Write Index (MSB)) to A
	ANA		D					; A = A & D
	MOV		D,A					; Copy A to D
	;; Store FIFO Write Index
	LXI		B,0005h				; Load offset (pointer FIFO Write Index (MSB)) to BC
	DAD		B					; HL (FIFO Write Index (LSB))= HL (FIFO Size mask (MSB)) + BC
	;
	MOV		M,D					; Store D to the address pointed by HL (FIFO Write Index (MSB))
	DCX		H					; Decrement HL (pointer FIFO Write Index (LSB))
	MOV		M,E					; Store E to the address pointed by HL (FIFO Write Index (LSB)). FIFO Write Index in DE
	;; Check FIFO Read Index > FIFO Write Index ?
	;
	;; Read FIFO Read Index
	DCX		H					; Decrement HL (pointer FIFO Read Index (MSB))
	MOV		B,M					; Load B from the address pointed by HL (FIFO Read Index (MSB))
	DCX		H					; Decrement HL (pointer FIFO Read Index (LSB))
	MOV		C,M					; Load C from the address pointed by HL (FIFO Read Index (LSB)). FIFO Read index in BC
	;; FIFO Read Index > FIFO Write Index ?
	MOV		A,B					; Copy B (FIFO Read Index (MSB)) to A
	CMP		D					; A (FIFO Read Index (MSB)) > D (FIFO Write Index (MSB))
	JZ		fifo_a16_write_full		; FIFO is FULL!
	MOV		A,C					; Copy C (FIFO Read Index (LSB)) to A
	CMP		E					; A (FIFO Read Index (LSB)) > E (FIFO Write Index (LSB))
	JZ		fifo_a16_write_full		; FIFO is FULL!
	;;
	MVI 	A,FIFO_OK			; Return 'FIFO OK' Status
	RET							; [359]
fifo_a16_write_already_full:
	POP		H					; Restore HL (FIFO structure address) from stack
	MVI 	A,FIFO_FULL			; Return 'FIFO FULL' Status
	STC							; Set 'carry' (Error)
	RET
fifo_a16_write_full:
	MOV		A,M					; Load A from the address pointed by HL (FIFO Status)
	ORI		FIFO_FULL			; Set 'FIFO Status' FULL
	MOV		M,A					; Store A to the address pointed by HL (FIFO Status)
	MVI 	A,FIFO_FULL			; Return 'FIFO FULL' Status
	RET
fifo_a16_write_null_size:
	POP		H					; Restore HL (FIFO structure address) from stack
	MVI 	A,FIFO_Err_ZS		; Set 'FIFO Status' ZERO SIZE
	STC							; Set 'carry' (Error)
	RET
;;
;
#include "memlib.asm"
