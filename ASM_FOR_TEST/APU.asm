#include "APU.inc"

APU8231_Init::
		MVI		A,80h				; 'Reset' CMD
		OUT		APU8231CR			; Send to 'Command'
		;
		MVI		C,10				; Loop try count
APU8231_Init_Loop:
		IN		APU8231SP			; Read 'Status'
		ANI		APU_BUSY			; APU busy ?
		JZ		APU8231_Test		; No, go test
		DCR		C					; Decrement try counter
		JNZ		APU8231_Init_Loop	; C > 0 ?
		;
		STC							; Set 'carry' (Error)
		RET
;;
; APU test
APU8231_Test::
;;
; Stack test
		MVI		A,55h
		OUT		APU8231D			; Write 'DATA'
		;
		IN		APU8231D			; Read 'DATA'
		CPI		0x55				; A = 0x55 ?
		JNZ		APU8231_Test_Err
		;
		MVI		A,0AAh
		OUT		APU8231D			; Write 'DATA'
		;
		IN		APU8231D			; Read 'DATA'
		CPI		0x0AA				; A = 0xAA ?
		JNZ		APU8231_Test_Err
		;
		MVI		A,0FFh
		OUT		APU8231D			; Write 'DATA'
		;
		IN		APU8231D			; Read 'DATA'
		CPI		0x0FF				; A = 0xFF ?
		JNZ		APU8231_Test_Err
		;
		MVI		A,00h
		OUT		APU8231D			; Write 'DATA'
		;
		IN		APU8231D			; Read 'DATA'
		CPI		0x00				; A = 0x00 ?
		JNZ		APU8231_Test_Err
;;
; 'Pi' test		
		MVI		A,1Ah				; 'PUPI' CMD. Must be return 0x02 0xC9 0x0F 0xDA !
		OUT		APU8231CR			; Send to 'Command'
		;
		IN		APU8231D			; Read 'DATA'
		CPI		02h
		JNZ		APU8231_Test_Err
		;
		IN		APU8231D			; Read 'DATA'
		CPI		0C9h
		JNZ		APU8231_Test_Err
		;
		IN		APU8231D			; Read 'DATA'
		CPI		0Fh
		JNZ		APU8231_Test_Err
		;
		IN		APU8231D			; Read 'DATA'
		CPI		0DAh
		JNZ		APU8231_Test_Err
		;
		ANA		A					; Clean 'carry' (No error)
		RET
APU8231_Test_Err:
		STC							; Set 'carry' (Error)
		RET
;;
; Math library

;;
; 16 bit signed integer

;;
; Add 16-bit signed integer
SADD::
		;
		MVI		A,SADD				; 'SADD' CMD
		OUT		APU8231CR			; Send to 'Command'
		;
		
		;
		IN		APU8231SP			; Read 'Status'
		ANI		APU_ERROR_ANY		; APU error ?
		JNZ		APU_Error			; Yes, go error
		;
		
		;
		RET
;;
; Substruct 16-bit signed integer
SSUB::
		;
		MVI		A,SSUB				; 'SSUB' CMD
		OUT		APU8231CR			; Send to 'Command'
		;

		RET
;;
; Multiply 16-bit signed integer
SMUL::
		;
		MVI		A,SMUL				; 'SMUL' CMD
		OUT		APU8231CR			; Send to 'Command'
		;

		RET
;;
; Divide 16-bit signed integer
SDIV::
		;
		MVI		A,SDIV				; 'SDIV' CMD
		OUT		APU8231CR			; Send to 'Command'
		;

		RET

;;
; 32 bit signed integer
;;
; Add 16-bit signed integer
DADD::
		;
		MVI		A,DADD				; 'DADD' CMD
		OUT		APU8231CR			; Send to 'Command'
		;

		RET
;;
; Substruct 16-bit signed integer
DSUB::
		;
		MVI		A,DSUB				; 'DSUB' CMD
		OUT		APU8231CR			; Send to 'Command'
		;

		RET
;;
; Multiply 16-bit signed integer
DMUL::
		;
		MVI		A,DMUL				; 'DMUL' CMD
		OUT		APU8231CR			; Send to 'Command'
		;

		RET
;;
; Divide 16-bit signed integer
DDIV::
		;
		MVI		A,DDIV				; 'DDIV' CMD
		OUT		APU8231CR			; Send to 'Command'
		;

		RET
