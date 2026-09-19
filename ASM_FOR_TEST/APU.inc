;;
; APU definition

;;
; APU 8231/9511 status register bits
APU_BUSY			EQU		10000000b		; Busy
APU_SIGN			EQU		01000000b		; Top stack iz Negative
APU_ZERO			EQU		00100000b		; Top stack iz Zero
APU_ERROR_ARGNEG	EQU		00001000b		; Negative argument
APU_ERROR_DIV0		EQU		00010000b		; Zero divizor
APU_ERROR_ARGBIG	EQU		00011000b		; Argument to large
APU_ERROR_UFLOW		EQU		00000100b		; Underflow
APU_ERROR_OFLOW		EQU		00000010b		; Overflow
APU_CARRY			EQU		00000001b		; Carry or Borrow
;
APU_ERROR_ANY		EQU		00011110b		; Any error

;;
; Instruction set APU 8231/9511, 32-bit floating point (A = TOS, B = NOS, C, D)
ACOS	EQU		06h ; 'ACOS(A), U, U, U
ASIN	EQU		05h ; 'ASIN(A), U, U, U
ATAN	EQU		07h ; 'ATAN(A), B, U, U
CHSF	EQU		15h ; '-A, B, C, D
COS 	EQU		03h ; 'COS(A), B, U, U
EXP 	EQU		0Ah ; 'EXP(A), B, U, U
FADD	EQU		10h ; 'A + B, C, D, U
FDIV	EQU		13h ; 'B / A, C, D, U
FLTD	EQU		1Ch ; 'FLOAT(A), B, C, U
FLTS	EQU		1Dh ; 'FLOAT(AU), B, C, U
FMUL	EQU		12h ; 'A * B, C, D, U
FSUB	EQU		11h ; 'B - A, C, D, U
LOG 	EQU		08h ; 'LOG(A), B, U, U
LN  	EQU		09h ; 'LN(A), B, U, U
POPF	EQU		18h ; 'B, C, D, A
PTOF	EQU		17h ; 'A, A, B, C
PUPI	EQU		1Ah ; '3.1415927, A, B, C
PWR 	EQU		0Bh ; 'B ^ A, C, U, U
SIN 	EQU		02h ; 'SIN(A), B, U, U  
SQRT	EQU		01h ; 'SQRT(A), B, C, U
TAN 	EQU		04h ; 'TAN(A), B, U, U
XCHF	EQU		19h ; 'B, A, C, D

;;
; Instruction set APU 8231/9511, 32-bit signed integers (A = TOS, B = NOS, C, D)
CHSD	EQU		34h ; '-A, B, C, D
DADD	EQU		2Ch ; 'A + B, C, D, A
DDIV	EQU		2Fh ; 'B / A, C, D, U
DMUL	EQU		2Eh ; 'LOWER32(A * B), C, D, U
DMUU	EQU		36h ; 'UPPER32(A * B), C, D, U
DSUB	EQU		2Dh ; 'B - A, C, D, A
FIXD	EQU		1Eh ; 'INT32(A), B, C, U
POPD	EQU		38h ; 'B, C, D, A
PTOD	EQU		37h ; 'A, A, B, C
XCHD	EQU		39h ; 'B, A, C, D

;;
; Instruction set APU 8231/9511, 16-bit signed integers (AU = TOS, AL = NOS, BU, BL, CU, CL, DU, DL)
CHSS	EQU		74h ; '-AU, AL, BU, BL, CU, CL, DU, DL, AU
FIXS	EQU		1Fh ; 'INT16(A), BU, BL, CU, CL, U, U, U
POPS	EQU		78h ; 'AL, BU, BL, CU, CL, DU, DL, AU
PTOS	EQU		77h ; 'AU, AU, BU, BL, CU, CL, DU
SADD	EQU		6Ch ; 'AL + AU, BU, BL, CU, CL, DU, DL, AU
SDIV	EQU		6Fh ; 'AL / AU, BU, BL, CU, CL, DU, DL, U
SMUL	EQU		6Eh ; 'LOWER16(AL * AU), BU, BL, CU, CL, DU, DL, U
SMUU	EQU		76h ; 'UPPER16(AL * AU), BU, BL, CU, CL, DU, DL, U
SSUB	EQU		6Dh ; 'AL - AU, BU, BL, CU, CL, DU, DL, AU
XCHS	EQU		79h ; 'AL, AU, BU, BL, CU, CL, DU, DL
NOOP	EQU		00h ; 'A, B, C, D (Note: slighly changed name to avoid collision with ; reserved word)
