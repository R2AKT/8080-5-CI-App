#target bin
#charset ascii
.asm8080

;;;;
;;
;; Brainfuck machine implementation for the 580VM80 (i8080) by R2AKT
;;
;;;;
;; HL - BF RAM pointer
;; DE - BF programm pointer
;; BC - BF loop counter
;;;;
BF_PointDev		EQU		00h			; Brainfuck stdio
BF_Pogramm		EQU		0100h		; Brainfuck code
BF_RAM			EQU		1000h		; Brainfuck RAM location
BF_RAM_SIZE		EQU		7530h		; Brainfuck RAM size (30 000 byte's)
;;
ROM 			EQU		0000h
SP_TOP			EQU		0FFFFh		; Stack pointer top
;;
BF_plus			EQU		2Bh			; "+" - increment RAM[H:L]
BF_minus		EQU		2Dh			; "-" - decrement RAM[H:L]
BF_left			EQU		3Ch			; "<" - decrement H:L
BF_right		EQU		3Eh			; ">" - increment H:L
BF_start_loop	EQU		5Bh			; "["
BF_stop_loop	EQU		5Dh			; "]"
BF_point 		EQU		2Eh			; "."
BF_comma 		EQU		2Ch			; ","
BF_End			EQU		0FFh		; End Brainfuck programm
;;
#code BF_PRG, 	ROM
	DI							; Disable Interrupts
	LXI 	SP,SP_TOP        	; Set Stack Pointer (0xFFFF)
;; Clean Brainfuck memory
	LXI 	H,BF_RAM			; Set BF start address (HL)
	LXI 	B,BF_RAM_SIZE		; Set BF size (BC)
	MVI 	D,00h				; Set fill value
	CALL 	memset
;; Set Brainfuck enviroment
	LXI 	H,BF_RAM			; Set BF start address (HL)
	LXI 	B,00h				; Set BF loop count (BC)
	LXI 	D,BF_Pogramm		; Set BF programm pointer (DE)
BF_Get_CMD:
	LDAX	D					; Load A from the address pointed by DE
	CPI 	BF_End				; End BF programm ?
	JZ		BF_End_Programm
	CPI 	BF_plus
	JZ		plus
	CPI 	BF_minus
	JZ 		minus
	CPI 	BF_left
	JZ 		left
	CPI 	BF_right
	JZ 		right
	CPI 	BF_point
	JZ 		point
	CPI 	BF_comma
	JZ 		comma
	CPI 	BF_start_loop
	JZ 		start_loop
	CPI 	BF_stop_loop
	JZ 		stop_loop
	JMP 	BF_End_Programm
BF_Next_CMD:
	INX 	D					; Increment BF programm pointer (DE)
	JMP 	BF_Get_CMD
BF_End_Programm:
	HLT
	JMP 	BF_End_Programm		
;; CMD implementation
;;
minus:
	DCR 	M					; "-" = Decrement value into the address pointed by HL
	JMP 	BF_Next_CMD
;;
plus:
	INR 	M					; "+" = Increment value into the address pointed by HL
	JMP 	BF_Next_CMD
;;
left:
	DCX 	H					; "<" = Decrement pointer HL
	JMP 	BF_Next_CMD
;;
right:
	INX 	H					; ">" = Increment pointer HL
	JMP 	BF_Next_CMD
;;
point:
	MOV 	A,M					; Load A from the address pointed by HL
	OUT 	BF_PointDev			; Send data to out device
	JMP 	BF_Next_CMD
;;
comma:
	IN 		BF_PointDev			; Read data from in device
	MOV 	M,A					; Store A to the address pointed by HL
	JMP 	BF_Next_CMD
;;
start_loop:
	MOV 	A,M					; Load A from the address pointed by HL
	ORA 	A					; Check A <> 0?
	JNZ 	BF_Next_CMD
	INX 	B					; Increment loop counter
start_loop_count:
	MOV 	A,B
	ORA 	C					; Check BC = 0?
	JZ 		BF_Next_CMD
	INX 	D					; Increment BF programm pointer (DE)
	LDAX 	D					; Load A from the address pointed by DE
	CPI 	BF_start_loop		; A = '['?
	JZ 		start_loop_plus
	CPI 	BF_stop_loop		; A = ']'?
	JZ 		start_loop_minus
	JMP 	start_loop_count
start_loop_plus:
	INX 	B					; Increment loop counter
	JMP 	start_loop_count	
start_loop_minus:
	DCX 	B					; Decrement loop counter
	JMP 	start_loop_count
;;
stop_loop:
	MOV 	A,M					; Load A from the address pointed by HL
	ORA 	A					; Check A = 0?
	JZ 		BF_Next_CMD
	LDAX 	D					; Load A from the address pointed by DE
	CPI 	BF_stop_loop		; A = ']'?
	JZ 		stop_loop_plus
stop_loop_count:
	MOV 	A,B
	ORA		C					; Check BC = 0?
	JZ 		end_stop_loop
	DCX 	D					; Decrement DE
	LDAX 	D					; Load A from the address pointed by DE
	CPI 	BF_start_loop		; A = '['?
	JZ 		stop_loop_minus
	CPI 	BF_stop_loop
	JZ 		stop_loop_plus
	JMP 	stop_loop_count
end_stop_loop:
	DCX 	D					; Decrement DE
	JZ 		BF_Next_CMD
stop_loop_minus:
	DCX 	B					; Decrement B
	JMP 	stop_loop_count
stop_loop_plus:
	INX 	B					; Increment BC
	JMP 	stop_loop_count
;;
;; Library memset implementation
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
;;
;
;#code LIST, BF_Pogramm
	ORG BF_Pogramm
	DM	">+++++++++[<++++++++>-]<.>+++++++[<++++>-]<+.+++++++..+++.>>>++++++++[<++++>-]<.>>>++++++++++[<+++++++++>-]<---.<<<<.+++.------.--------.>>+.>++++++++++."
	DM 	BF_End, __date__ , 0, __TIME__
