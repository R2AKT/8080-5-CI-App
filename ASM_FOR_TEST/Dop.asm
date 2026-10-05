;.title  "Дополнительные возможности Terminfk для отладки"
module   DopMon
;
include   "AdrIO.inc"

SECTION 	kp04_DOP
	org	0e000h

;    LXI     SP,TEMPSTACK    ; установить стэк
    mvi     a,0C0h           ; Маска для запрета прерываний
    sim						; и для отключения ПЗУ
    mvi		a,40h			; Сброс тригера отключене ПЗУ
    sim
    DI
	jmp		0F000h			;  Переход на монитор

; Дополнения
include   	"Term85.asm"		; Использовать для отладки
include		"MonNoICE.asm"		; Монитор отладчик
	REPT 0x800 - ASMPC - 2
		db   0xCC
	ENDR
ww:	db   0E0h,00
		ASSERT	ASMPC == 0x800
