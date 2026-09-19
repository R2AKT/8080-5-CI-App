;;
; LCD (LCD2004) implementation

; ;;
; Send data (acc. A) to LCD
LCD_Send::
		OUT LCD2004DATA				; Send LCD command
;;
; Initialize LCD display.
LCD_Init::
		MVI A,00111000b				; Function Set - 8 bit line, 2 line display, 5x8 dot
		OUT LCD2004CMD				; Send LCD command
		OUT LCD2004CMD				; Send LCD command
		OUT LCD2004CMD				; Send LCD command (Repeat 3)
		MVI A,00011100b				; Cursor or Display shift
		OUT LCD2004CMD				; Send LCD command
		MVI A,00001100b    			; Display ON/OFF Control - display on, cursor off, blink cursor off
		OUT LCD2004CMD				; Send LCD command
		MVI A,00000110b				; Entry Mode Set - increment by 1, no entire display shift
		OUT LCD2004CMD				; Send LCD command
		MVI A,00000001b				; Clear Display  (delay 1.5 ms after send data)
		OUT LCD2004CMD				; Send LCD command
		MVI A,00000010b				; Return To Home (delay 1.5 ms after send data)
		OUT LCD2004CMD				; Send LCD command
		MVI A,52h					; Set data to display - char "R"
		OUT LCD2004DATA				; Send LCD data
		CALL LCD_Off
		RET
;;
; On LCD driver
LCD_On::
		MVI A,00000001b				; Clear Display  (delay 1.5 ms after send data)
		OUT LCD2004CMD				; Send LCD command
		MVI A,00001100b				; Display ON/OFF Control - display on, cursor off, blink cursor off
		OUT LCD2004CMD				; Send LCD command
		RET
;;
; Off LCD driver
LCD_Off::
		MVI A,00000001b				; Clear Display  (delay 1.5 ms after send data)
		OUT LCD2004CMD				; Send LCD command
		MVI A,00001000b				; Display ON/OFF Control - display off, cursor off, blink cursor off
		OUT LCD2004CMD				; Send LCD command
		RET
;;
; Set LCD cursor position (Position: H = ROW, L = COLUM)
LCD_Set_Locate::
		MOV A,H						; H -> A
		CPI 00h       				; If A=0 Then DIRECT ADDRESS SET
		JZ Direct
		CPI 01h						; If A=1 Then DIRECT ADDRESS SET
		JZ Line1
		CPI 02h						; If A=2 Then DIRECT ADDRESS SET
		JZ Line2
		CPI 03h						; If A=3 Then DIRECT ADDRESS SET
		JZ Line3
		CPI 04h						; If A=4 Then DIRECT ADDRESS SET
		JZ Line4
		JMP End_LCD_Set_Locate
Direct:
		MOV A,L						; L -> A
		ORI 80h						; Set 7 bit (Address Set)
		OUT LCD2004CMD				; Send LCD command
		JMP End_LCD_Set_Locate
Line1:
		MOV A,L						; L -> A
		ORI 80h      				; Set 7 bit (Address Set)
		OUT LCD2004CMD				; Send LCD command
		JMP End_LCD_Set_Locate
Line2:
		MOV A,L						; L -> A
		ORI 0C0h      				; Start address row 2, set 7 bit (Address Set). (40h|80h = C0h)
		OUT LCD2004CMD				; Send LCD command
		JMP End_LCD_Set_Locate
Line3:
		MOV A,L						; L -> A
		ORI 94h      				; Start address row 3, set 7 bit (Address Set). (14h|80h = 94h)
		OUT LCD2004CMD				; Send LCD command
		JMP End_LCD_Set_Locate
Line4:
		MOV A,L						; L -> A
		ORI 0D4h      				; Start address row 4, set 7 bit (Address Set). (54h|80h = D4)
		OUT LCD2004CMD				; Send LCD command
		JMP End_LCD_Set_Locate
End_LCD_Set_Locate:
		RET
; ;;
; ; Send Message Number (acc. A) to LCD
; LCD_Print_Msg:
; ;            PUSH H      			; Store HL
; ;;
            ; STA     Msg_Index     	; Store message index
            ; MOV     #$01, Msg_Found ; Set founded message index to 1
; ;
			; LHLD	MESSAGE			;LDHX    #Start_Msg    	; Load start index to HL
            ; INX H					;AIX     #$01          	; Set offset to first message (Start_Msg - NOT MESSAGE)
; Find_Msg:
            ; LDA     Msg_Found
            ; CMP     Msg_Index
            ; BEQ     Get_Char      	; If Msg_Found = Msg_Index Then Print Message
            ; MOV A,M					;LDA     0,X			; Load A from address pointer in HL 
            ; CPI 00h					; CMP     #$FF ('Stop byte' changed from FFh to 00h)
            ; JZ Msg_Find_Index_Inc	;BEQ     Msg_Find_Index_Inc
            ; INX H					; AIX     #$01	; Increment HL
            ; CPHX    #$FDFF
            ; JZ No_Msg_Found			; BEQ     No_Msg_Found 	; HL = FDFFh
            ; JMP     Find_Msg
; ;
; Msg_Find_Index_Inc:
            ; INX H					; AIX     #$01	; Increment HL
            ; INC     Msg_Found
            ; JMP     Find_Msg
; ;
; No_Msg_Found:
            ; LHLD Msg_NoMsg			;LDHX    #Msg_NoMsg    	; If message not found !!! Load to HL 'NO MESSAGE' address
; ;
; Get_Char:
            ; MOV A,M					;LDA     0,X
            ; CMP     #$FF
            ; BEQ     End_LCD_Print_Ms; If $FF Then End message string
; ;
; ;            PUSH H					; Store HL
            ; CALL Send_Lcd			; Send CHAR data to LCD
; ;            POP HL					; Restore HL
; ;
            ; INX H					; AIX     #$01	; Increment HL
            ; JMP Get_Char			; Get next message CHAR
; ;
; End_LCD_Print_Msg:
; ;            POP H					; Restore HL
            ; RET
