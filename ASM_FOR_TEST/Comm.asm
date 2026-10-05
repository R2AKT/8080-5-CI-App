PUBLIC	word_F600, DspBuf,Conf, unk_F605, unk_F609, unk_F60C, AdefCrt, byte_F60F
PUBLIC	FlagKey, byte_F669, word_F66A, unk_F66C, byte_F66D, unk_F66F, word_F670, word_F671, unk_F672
PUBLIC	word_F673, word_F674, unk_F675, word_F676, word_F678, word_F67A, byte_F67C, byte_F67D
PUBLIC	word_F67E, byte_F67E, byte_F67F, byte_F680, word_F681, word_F683, CmdGo, TmpStk, Area2, Area3
PUBLIC	Buf, ppDMA, XYCur, word_F6D9, byte_F6DB, word_F6DC, word_F6DE, byte_F6EF
PUBLIC	byte_F6E0, word_F6E1, byte_F6E2, word_F6E3, byte_F6E4, word_F6E5, byte_F6E6, SrcDMA, SrcDMA1
PUBLIC	BitTime, HalfBit,  HiMem, ADspBuf, BegBUF, endBuf1, Stack, unk_F66C, word_F610

;.title "Рабочая область"
;.include  "AdrIO.inc"

module  Common

	SECTION kp04_COMMON
		org 	0DE00h
word_F600:	dw 0E800h		; Адрес знакогенератора, по умолчанию E800
DspBuf:		dw 0			; буфер экрана
;unk_F603:	db 0B4h			; Старший байт буфера экрана
Conf:		db    1			; Конфигурация
							; Биты 0-1
							;	0 - текст. 16K/64,
							;   1 - граф. 48K/40,
							;	2 - текст. 32K/64,
							;   3 - граф. 48K/80).
							; Бит 2
							;       Требуется ли очистка экрана
							; 		при установке режима
unk_F605:	dw 0C9C9h 		; Адрес подпрограммы ??????
;unk_F606:	db 0C9h 		; C9C9  Вывод на принтер
			dw  0			; Адрес программы вывода на принтер
unk_F609:	db 0C9h, 0, 0
unk_F60C:	db 0C3h			; Адрес подпрограммы ??????
AdefCrt:	dw 0			; Адрес программы вывода на дисплей
byte_F60F:	db 0E6h 		; Байт синхронизации
word_F610:	db  4440h
			db  05Dh
			db  038h
			db  039h
			db  05Ah
			db  056h
			db  02Ch
			db  049h
			db  050h
			db  045h
			db  034h
			db  03Ah
			db  0Dh
			db  018h
			db  020h
			db  041h
			db  04Bh
			db  033h
			db    2
			db  0Ah
			db  065h
			db  07Fh
			db  04Dh
			db  057h
			db  055h
			db  032h
			db    1
			db  01Fh
			db  0Ch
			db  06Bh
			db  053h
			db  059h
			db  043h
			db  031h
			db    0
			db  076h
			db  075h
			db  074h
			db  05Eh
			db  051h
			db  046h
			db  04Ah
			db  03Bh
			db  073h
			db  072h
			db  071h
			db  062h
			db  061h
			db  063h
			db    9
			db  01Bh
			db  06Ch
			db  06Eh
			db  070h
			db  064h
			db    0
			db  0Ch
			db  06Dh
			db  0Dh
			db  079h
			db  078h
			db  077h
			db  060h
			db  04Ch
			db  05Bh
			db  037h
			db  030h
			db  048h
			db  05Ch
			db    8
			db  042h
			db  047h
			db  036h
			db    4
			db  02Dh
			db  05Fh
			db  02Eh
			db  058h
			db  04Fh
			db  04Eh
			db  035h
			db    3
			db  02Fh
			db  019h
			db  01Ah
			db  054h
			db  052h
FlagKey:	db 0		;byte_F668 Флаг состояния клавиатуры
byte_F669:	db 0F0h		;byte_F669
			db	0
word_F66A:	dw 0C3C0h	; текущий адрес в буфера экрана
unk_F66C:	db 0	; Сюда переход из подпрограммы вывода пробела
byte_F66D:	db 0FCh		; Работа с дисплеем
			db 0C3h
unk_F66F:	db 0
word_F670:	db 0
word_F671:	db 0C3h
unk_F672:	db 0
word_F673:	db 0
word_F674:	db 0C3h
unk_F675:	db 0
word_F676:	dw 0		; Работа с командой ESC 59h
word_F678:	dw	0FFFFh	; при работе с клавиатурой
;byte_F679:	db 0FFh
word_F67A:	dw    0		; при работе с клавиатурой
byte_F67C:	db 058h		; Частота для клавиатуры
byte_F67D:	db 0FFh		; Работа с клавиатурой
word_F67E:				; Работа с дисплеем
byte_F67E:	db    0		; Последняя команда ВГ75
byte_F67F:	db    0
byte_F680:	db    0
word_F681:	dw 0200h	; Работа с магнитофоном
word_F683:	dw 0300h	; Работа с магнитофоном
CmdGo:		db 0C3h		; jmp	0h83E	; Выполнить программу с адреса
TmpStk:		dw 083Eh	; Первый аргумент адрес	программы
Area2:		dw 050D3h	; Второй аргумент
Area3:		dw 013Eh	; Третий аргумент
Buf:		DS 	15		; Буфер ввода
ppDMA:		db  0FFh	; F6D6 Конец буфера
XYCur:		dw  04ECDh 	; Адрес курсора
word_F6D9:	db  3EFEh	; Работа с дисплеем
;byte_F6DA:	db  03Eh 	;	3EFE
byte_F6DB:	db    7
word_F6DC:	dw  04ECDh	; Начало текущего буфера экрана
;byte_F6DD:	db  04Eh
word_F6DE:	db  0FEh	;
byte_F6EF:	db  03Eh
byte_F6E0:	db    0		; Счетчик   Работа с командой ESC 59H
word_F6E1:	db  0CDh	; Цвет
byte_F6E2:	db  04Eh	; Цвет 4ECD
word_F6E3:	db  0FEh
byte_F6E4:	db  0Eh		; 0EFE
word_F6E5:	db  064h
byte_F6E6:	db  0CDh	; CD64
SrcDMA:		db  06Eh 		; F6E7h
SrcDMA1:	db  0FEh 	;
;--------------------------------------------------------------
BitTime:   	dw  0      	; Адрес для вычисления задержки бита
HalfBit:   	dw  0      	; Адрес для задерки половина бита
HiMem		equ 	0A600h	; Верхняя память
ADspBuf		equ		0A600h	; Адрес начала буфера дисплея вмеcто BC00h
FntChar		equ		09E00h	; Фонт для символьного режима
FntGfaph	equ		0A200h	; Фонт для графического режима
; ------------------------------------------------------------
BegBUF:					; Еще один буфер для работы
		REPT	253
			DB	0F0h	; Эти 256 байт заполняются F0 до EndBuf1
		ENDR
endBuf1:				;
		REPT	14
			DB	0FFh
		ENDR
Stack:					; Это стэк компьютера
		REPT	64
			db 	0Fh
		ENDR
		rept 0x200 - ASMPC -2
			db	0x55
		endr
		DB	0DEh,0
		ASSERT	ASMPC == 0x200
