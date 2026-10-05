; Эти находятся в модуле kp04_Comm
;	EXTERN	unk_F606, unk_F605, unk_F60C, word_F6DC, word_F66A, word_F67E, byte_F6DB
;	EXTERN	word_F678, word_F67A, byte_F67D, byte_F67C, word_F683, byte_F60F, word_F681
;	EXTERN	word_F6E2, word_F676, byte_F6E0, unk_F675, word_F600, word_F6E1, byte_F67F
;	EXTERN	byte_F6E2, byte_F66D, word_F6D9, byte_F669, byte_F680, word_F6E5, word_F6E3
;	EXTERN	word_F670, word_F673, unk_F66F, word_F6DC, unk_F672, word_F6E2

; Эти находятся в модуле kp04_Comm
;	EXTERN	Conf, AdefCrt, DspBuf, XYCur, FlagKey, TmpStk, Area2, Area3, AdefCrt

include	"Comm.def"
include "Dop.def"
include "DD30.def"
;include "DD28.def"

; Эти находятся в модуле kp04_DD28
	EXTERN	ExtFD86, ExtFED4, ExtFC72, ExtFD5A, ExtFF36, ExtFF8E, ExtFE0A, ExtFC00

	PUBLIC 	MON, mStrt, mCI, mMI, mOutDsp, mMO, mLP, mKeySt, mOutHex, mOutTxt
	PUBLIC	mInKey, mCurXY, mDspBuf, mMGblI, mMGblO, mCRSbl, mDspOn, mRMem, mWMem

module   MonDD29
;
include   "AdrIO.inc"
;ALIGN	0F800h
;	org 0F800h
SECTION 	kp04_DD29


MON:
mStrt:		jmp	Start
mCI:		jmp	KeyIn		; 03 Ввод символа с клавиатуры
mMI:		jmp	MagIn		; 06 Магнитофон ввод
mOutDsp:	jmp	OutDis		; 09 Вывести на дисплей
mMO:		jmp	MagOut		; 0C Магнитофон вывод
mLP:		jmp	unk_F605 + 1	; 0F Вывод на принтер
mKeySt:		jmp	KeyStat		; 12 Состояние клавиатуры
mOutHex:	jmp	OutHex		; 15 вывод в 16 виде
mOutTxt:	jmp	OutTxt		; 18 Выводим строку сообщения
mInKey:		jmp	InKey		; 1B Ввод с клавиатуры
mCurXY:		jmp	InCur		; 1E Местоположение курсора
mDspBuf:	jmp	InBufDis	; 21 Входной буфер дисплея
mMGblI:		jmp	InBlkMag	; 24 Ввод блока с магнитофона
mMGblO:		jmp	OutBlkMag	; 27 Вывод блока на магнитофон
mCRSbl:		jmp	CrcBlk		; 2A Контрольная сумма блока
mDspOn:		jmp	DisOn		; 2D Включить отображение на дисплее
mRMem:		jmp	InHiMem		; 30 Получить верхнюю память
mWMem:		jmp	OutHiMem	; 33 Сохранить верхнюю память


; ───────────────────────────────────────────────────────────────────────────
; Вывод на экран в 16 виде
OutHex:
		push	psw
		rrc
		rrc
		rrc
		rrc
		call	i_1
		pop		psw
i_1:
		ani		0Fh
		adi		030h
		cpi		03Ah
		jc		i_2
		adi		7
i_2:
		mov	c, a

; Вывести на дисплей
OutDis:
		push	h
		push	d
		push	b
		push	psw
		call	unk_F605	; 
		call	unk_F60C	; Вывод на дисплей в зависимости от конфигурации
POPAll:
		pop	psw
POPRg:
		pop		b
		pop		d
POPOnliH:
		pop		h
		ret

; Запуск дисплея
DisOn:
		push	h
		push	d
		push	b
		mvi		a, 5
		out		SysPrtCtl   ;
		lda		Conf		; Конфигурация
		rrc
		jc		Dis02		; Конфигурация 1 и 3
		rrc
		lxi		h, 037C2h	; Адрес буфера дисплея 16К
		jnc		Dis01		; Конфигурация 2 

; Начальная установка дисплея
; Конфигурация
;DisOnCon:
		mvi		h, 077h 	; Адрес буфера дисплея
Dis01:
		shld	word_F6DC	; Сохраняем адрес буфера дисплея
		mvi		l, 0		; Обнуляем младший байт
		dcr		h			; Уменьшаем старший 76h
		shld	word_F66A	; Сохраняем 7600h Буфер экрана
;		mvi		a, 080h 	; Режим автозагрузка
;		out		DmaCtrl		; Контроллер ПДП
;		mvi		a, 0CEh		; Адрес младший
;		out		DmaAdr2     ;
;		mov		a, h		; Адрес старший
;		out		DmaAdr2     ; Адрес 76CEh
;		mvi		a, 024h 	; Количество младший
;		out		DmaCkl2     ; Количество 8924
;		mvi		a, 089h 	; Количество старший
;		out		DmaCkl2     ;
;		mvi		a, 084h 	; Автозагрузка разрешить канал 2
;		out		DmaCtrl   	;
;		xra		a			; Команда сброс
;		out		BB75Comm    ; Контроллер дисплея
;		sta		word_F67E	; Последняя команда ВГ75
;		mvi		a, 04Dh 	; Число знаков в знакоряду 77
;		out		BB75Dat     ;
;		mvi		a, 01Dh		; Число знакорядов в кадре 29
;		out		BB75Dat     ;
;		mvi		a, 099h 	; Номер строки подчеркивания, число строк растра
;		out		BB75Dat     ;
;		mvi		a, 091h 	; Режим счетчика строк,тип курсора,
;							; 	число знаков обратного хода развертки
;		out		BB75Dat     ;
;		mvi		a, 027h 	; Запуск, интервал между пакетами
;							; 	число запросов в пакете
;		out		BB75Comm    ;
; Настройка страницы и кодировки
		mvi	a,0x80 				; Страница 0, кодировка KOI8R
; Настраиваем ПДП
		mvi		a, 080h 	; Режим автозагрузки
		out		DmaCtrl     ;
		xra		a
		out		DmaAdr2     ; Адрес ОЗУ
		out		BB75Comm    ; Команда сброс
		mvi		a, 0x00		;0A2h
		out		DmaAdr2     ; Адрес 0000h
		mvi		a, 0x9F		;0D7h
		out		DmaCkl2     ; Количество
		mvi		a, 0x8F		; 083h
		out		DmaCkl2     ; Количество 83D7h
		mvi		a, 0xA4		;084h
		out		DmaCtrl     ; Режим автозагрузки разрешить 2 канал
; настраиваем ВГ75
		mvi		a, 79		;049h 	; Число знаков в знакоряду 73
		out		BB75Dat     ; 73
		mvi		a, 0x98		;011h		; Число знакорядов в кадре 17
		out		BB75Dat     ; 17
		mvi		a, 0Fh		; Номер строки подчеркивания, число строк растра
		out		BB75Dat     ; 16
		mvi		a, 0x09		;052h 	; Режим счетчика строк,тип курсора,
							; число знаков обратного хода развертки
		out		BB75Dat     ;
		mvi		a, 0xE0
		out 	BB75Comm
		nop
		nop
		nop
		mvi		a, 0x21		;027h
		out		BB75Comm    ; Запуск, интервал между пакетами
							;	число запросов в пакете
		in		BB75Comm	; Сбрасываем 5 бит
loop1:
		in 		BB75Comm	;
		ani 20h
		jz 		loop1		; Ожидаем что он установился

		lxi		h, ExtFD5A	;DefCrt	; Программа вывода на дисплей в	графическом режиме
		shld	AdefCrt		; Устанавливаем по умолчанию
;		call	CallBn2		; 
; ───────────────────────────────────────────────────────────────────────────
		call	ExtFD86		; .dw 0hFD86	; Вывод графический
; ───────────────────────────────────────────────────────────────────────────
		mvi		c, 01Fh
		call	OutDis		; Очистить экран
							; А в ВГ75 тоже сработает??????
		jmp		POPRg

; Конфигурация 1 и 3
Dis02:
		rrc
		mvi		a, 2
		ral
		out		SysPrtCtl   ; ВВ55
		lxi		h, DefCrt2	; Вывод на дисплей символьном режиме 
		shld	AdefCrt		; Устанавливаем по умолчанию
;		call	CallBn2		; 
		call 	ExtFED4		; Вывод в символьном виде ; Настройка дисплея
Dis03 	equ	ASMPC -2		; Для замены адреса вывода на дисплей
; ───────────────────────────────────────────────────────────────────────────
;DisO3:		.dw 0hFED4		; ExtFED4  
; ───────────────────────────────────────────────────────────────────────────

OutHiMem:
		shld	DspBuf

InHiMem:
		lhld	DspBuf		; HiMem
		ret

; ───────────────────────────────────────────────────────────────────────────
; Читать байт с текущего адреса буфера дисплея
InBufDis:
		sta		byte_F6DB	; Сохранить
		lda		Conf		; Конфигурация
		rrc
		jnc		i_191		; InBuf1
		push	d
		mvi		a, 0DFh
		sub		c
		mov		c, a
		call	sub_FF67
		mov		a, m
		ana		b
		pop		d
		ret
;Не первый
i_191:							; InBuf1:
		push	h
		lhld	word_F66A	; Буфер экрана или текущий адрес в буфере экрана
		mov		a, m		; Читаем данные
		pop		h
		ret
;
; Местоположение курсора
InCur:
		lhld	XYCur
		ret
;
; Ввод символа с клавиатуры
KeyIn:
		call	KeyStat		; Прверка готовности клавиатуры
		ora		a
		jz		KeyIn		; Ввод символа с клавиатуры
		xra		a
		sta		FlagKey		; Обнуляем флаг
		push	h
		push	d
		lhld	word_F678
		xchg
		lhld	word_F67A
		mov		a, e
		cpi		060h
		jc		i_12
		cpi		07Fh
		jz		i_11
		sui		040h

i_11:
		pop		d
		pop		h
		ret

i_12:
		cpi		40h
		jnc		i_14
		cpi		021h
		jnc		i_13
		cpi		5
		jnc		i_15

i_13:
		xra		l
		pop		d
		pop		h
		ret

i_14:
		xra		h
		ana		d

i_15:
		pop		d
		pop		h
		ret

; Состояние клавиатуры
KeyStat:
		lda		FlagKey			; Получаем флаг состояния
		ora		a
		rnz						; Если не 0 возвращаемся
		call	InKey			; Читать клавиатуру
		lda		FlagKey			; Получаем флаг состояния
		ora		a
		rz						; Если 0 возвращаемся
		lda		byte_F67D		; 
		sta		word_F678		; 
		lda		byte_F67C		; Частота для канала 1 таймера
		out		Tim1    		; 0D1h Таймер
		xra		a
		out		Tim1    		; 0D1h
		dcr		a				; устанавливаем -1
		ret

InKey:
;		call	CallBn2			;
		call 	ExtFC72			; Ввод с клавиатуры
;		db  0FC72h 			; ExtFC72
		ret
;
; Выводим строку сообщения
OutTxt:
		mov		a, m	; Выводимый символ
		ora		a		; Проверка на конец строки
		rz				; выход
		mov		c, a	; выводимый симвл в С
		call	OutDis	; Вывести на дисплей
		inx		h		; Следующий символ
		jmp		OutTxt	; Повторить
; ───────────────────────────────────────────────────────────────────────────
; Программа вывода на дисплей в символьном режиме
;DefCrt:
;		call	CallBn2		; 
;		call 	ExtFD5A		; Вывод на дисплей в символьном режиме
; ───────────────────────────────────────────────────────────────────────────
;		.dw 0hFDA5			; ExtFDA5
; ───────────────────────────────────────────────────────────────────────────
;		ret

sub_F96A:
		xra		a
		
; Магнитофон ввод
MagIn:
		push	h
		push	d
		push	b
		mov		b, a
		rlc
		jc		i_21
		mvi		b, 8
i_21:
		lxi		h, 0
		dad		sp
		shld	TmpStk
		mvi		a, 80h
		out		DmaCtrl     	; 0F8h ПДП команда
		lhld	word_F683
i_22:
		pop		psw
		in		Tim0    	; 0D0h Таймер
		in		Tim0    	; 0D0h
		ora		a
		jp		i_22
		in		SysPrtC    ; 0C2h ППА канал В
		ani		080h
		mov		e, a
		mov		d, a
i_23:
		pop		psw
		in		SysPrtC    ; 0C2h ППА канал В
		ani		080h
		cmp		e
		jnz		i_26
		dcr		d
		jnz		i_23
		lhld	TmpStk
		sphl
		call	InKey
		cpi		3
		jz		i_24
		mov		a, b
		rlc
		lhld	word_F683
		jc		i_23
i_24:
		mvi		a, 094h
		out		DmaCtrl     ; 0F8h ПДП команда запуск
		stc
		jmp		POPRg
i_26:
		rlc
		mov		a, l
		out		Tim0    	; 0D0h Таймер канал 1
		mov		a, h
		out		Tim0    	; 0D0h Таймер канал 1
		mov		a, c
		ral
		mov		c, a
		dcr		b
		jz		i_29
		jp		i_22
		inr		b
		lda		byte_F60F	; Байт синхронизации
		cmp		c
		jnz		i_27
		xra		a
		jmp		i_28
i_27:
		cma
		cmp		c
		jnz		i_22
		mvi		a, 0FFh
i_28:
		sta		Area2
		mvi		b, 8
		in		SysPrtC    ; 0C2h ППА канал С
		xri		8
		out		SysPrtC    ; 0C2h ППА канал С
i_210:
MagI10:
		jmp		i_22
i_29:
		mvi		a, 094h
		out		DmaCtrl     ; 0F8h ПДП команда
		lhld	TmpStk
		sphl
		lda		Area3
		xra		c
		jmp		POPRg
		
; Ввод блока с магнитофона
InBlkMag:
		di
		mvi		a, 030h
		out		TimC    ; 0D3h Таймер команда
		out		Tim0    ; 0D0h Таймер данные
		out		Tim0    ; 0D0h Таймер данные
		call	i_32
		rc
		push	h
		dad		b
		xchg
		call	Met4
		pop		h
		rc
		dad		b
		xchg
		push	h
i_31:
		call	sub_F96A
		jc		POPOnliH
		mov		m, a
		inx		h
		mov		a, e
		sub		l
		mov		a, d
		sbb		h
		jnc		i_31
		pop		h
i_32:
		mvi		a, 0AFh	   ; Константа переписывается
Met4	equ   ASMPC - 1
		call	MagIn
		rc
		mov		b, a
		call	sub_F96A
		mov		c, a
		ret
; ───────────────────────────────────────────────────────────────────────────
; Вывод блока на магнитофон
OutBlkMag:
		di
		mvi		a, 030h
		out		TimC    ; 0D3h
		out		Tim0    ; 0D0h
		out		Tim0    ; 0D0h
		push	b
		push	h
		mov		a, l
		cma
		mov		l, a
		mov		a, h
		cma
		mov		h, a
		inx		h
		inx		h
		dad		d
		xthl
		push	d
		lxi		d, 0200h	; Количество
i_41:
		mvi		c, 0AAh
		call	MagOut
		dcx		d
		mov		a, e
		ora		d
		jnz		i_41
		lda		byte_F60F	; Байт синхронизации
		mov		c, a
		call	MagOut
		call	OutHL		; Вывод	содержимого HL
		xthl
		call	OutHL		; Вывод	содержимого HL
		pop		h
		pop		d
i_42:
		mov		c, m
		call	MagOut
		inx		h
		dcx		d
		mov		a, e
		ora		d
		jnz		i_42
		lxi		b, 01000h	; Количество
i_43:
		call	MagOut
		dcr		b
		jnz		i_43
		lda		byte_F60F	; Байт синхронизации
		mov		c, a
		call	MagOut
		pop		h
		call	OutHL

; Вывод	содержимого HL
OutHL:
		mov		c, h
		call	MagOut
		mov		c, l
		
; Магнитофон вывод
MagOut:
		push	h
		push	d
		push	b
		push	psw
		mvi		a, 080h
		out		DmaCtrl      ; 0F8h ПДП команда стоп
		lhld	word_F681
		xchg
		lxi		h, 0
		dad		sp
		mvi		b, 8
i_51:
		pop		psw
		in		Tim0    ; 0D0h
		in		Tim0    ; 0D0h
		ora		a
		jp		i_51
		mov		a, e
		out		Tim0    ; 0D0h
		mov		a, d
		out		Tim0    ; 0D0h
		mov		a, c
		rlc
		mov		c, a
		mvi		a, 3
		ral
		out		SysPrtCtl     ; 0C3h
i_52:
		pop		psw
		in		Tim0    ; 0D0h
		in		Tim0    ; 0D0h
		ora		a
		jp		i_52
		mov		a, e
		out		Tim0    ; 0D0h
		mov		a, d
		out		Tim0    ; 0D0h
		in		SysPrtC    ; 0C2h
		xri		8
		out		SysPrtC    ; 0C2h
		dcr		b
		jnz		i_51
		mvi		a, 094h
		sphl
		out		DmaCtrl     ; 0F8h ПДП команда старт
		jmp		POPAll
		
; Контрольная сумма блока
CrcBlk:
		lxi		b, 0		; Контрольная сумма блока

i_61:
		mov		a, m
		add		c
		mov		c, a
		push	psw
		call	HLeqBC		; Проверка на равенство	регистров
		jnz		i_62
		pop		psw
		ret
i_62:
		pop		psw
		mov		a, b
		adc		m
		mov		b, a
		call	HLeqBC		; Проверка на равенство	регистров
		rz
		inx		h
		jmp		i_61

; Проверка на равенство	регистров
HLeqBC:
		mov		a, h
		cmp		d
		rnz
		mov		a, l
		cmp		e
		ret
; Настройка конфигурации
Config:
loc_FAF4:
		lxi		h, DspOUT	;0FAFDh	; Адрес программы вывода на дисплей
		shld	AdefCrt		; Установить его
		jmp		sub_FD49

; ───────────────────────────────────────────────────────────────────────────
DspOUT:
;sub_FAFD:					; Вывод на дисплей
		lda		Conf		; Конфигурация 
		ani		0b11111101
		xra		c
		sta		Conf		; Конфигурация
		mov		b, a
		mov		a, c
		ani		8
		jz		i_72			;
		in		BB75Stat    	; сбросить 5 бит
i_71:							;
		in		BB75Stat    	;
		ani		20h				; Проверить 5 бит установлен
		jz		i_71			; Ожидать его устанвки
i_72:							;
		mov		a, c
		rrc
		rrc
		mvi		a, 2
		ral
		out		SysPrtCtl    	;
		mov		a, c
		ani		10h
		jz		i_73			;
		ana		b
;		call	CallBn2			;
		call 	ExtFF36			; Вывод символа
; ───────────────────────────────────────────────────────────────────────────
;		.dw 	0hFF36			; ExtFF36
; ───────────────────────────────────────────────────────────────────────────
i_73:							; loc_FB2A:
		lxi		h, Dat1
		push	h
		jmp		Home
		
; Выбор цветовой палитры
Palet:
;loc_FB31:
		lxi		h, Dat2
		mvi		a, 3
		jmp		loc_FB4B

; Вывод на дисплей
Dat2:							; Устанавливаем цвет рег С
		mov		a, c
		out		ColPrtC			;
		lhld	byte_F6E2		; Цвет
		mov		a, l
		out		ColPrtB			; Модуль цветности
		mov		a, h
		out		ColPrtA			;
		ret

; Команда 59h из ESC последовательности
Cmd59:
;loc_FB46:
		lxi		h, Sub_FCD5		; Цвет
		mvi		a, 2

loc_FB4B:
		shld	word_F676
		sta		byte_F6E0
		lxi		h, Dat3

loc_FB54:
		shld	AdefCrt			; Текущий адрес программы вывода на дисплей
		ret

; Вывод на дисплей
Dat3:
		lda		byte_F6E0		; счетчик
		lxi		h, 0F6E1h		; Цвет
		dcr		a				; Уменьшить счетчик
		sta		byte_F6E0
		jz		i_411			; Все завершить
		add		l				; Младший адрес
		mov		l, a			;
		mov		m, c			; Что у нас в С?
		ret
i_411:							; Счетчик обнулился, завершаем
		lxi		h, DefCrt2		; Вывод в графическом режиме
		shld	AdefCrt			; Установить адрес
		jmp		unk_F675		; 

Sub_0FB72:
		lhld	word_F600		;
		xchg
		lhld	word_F6E1
		mov		l, c
		shld	word_F600
		lda		byte_F6DB
		ora		a
		rnz
;		call	CallBn2		; 
		call 	ExtFF8E		; Программа перемещения фонта
; ───────────────────────────────────────────────────────────────────────────
;		.dw 	0hFF8E			; ExtFF8E
; ───────────────────────────────────────────────────────────────────────────
		ret
; ───────────────────────────────────────────────────────────────────────────
; Таблица Подпрограмм 0FB85h
		dw Sub_0FDD7
		dw Sub_0FE8A
		dw Sub_0FE00
		dw Sub_0FE4C
		dw Sub_0FE33
		dw Sub_0FE18
		dw Sub_0FB72
; ───────────────────────────────────────────────────────────────────────────
; Подпрограмма вывода на дисплей анализ символа на управляющие
DefCrt2:
		mov		a, c
		cpi		01Bh		; ESC
		jz		ESC			; loc_FD94
		lxi		h, Dat1
		push	h
		push	b
		call	sub_FD49
		pop		b
		xchg
		lhld	XYCur		; положение курсора
		xchg				; в DE
		mov		a, c
		cpi		020h		; Пробел
		jnc		Spc
		cpi		0Dh			; ВК
		jz		CR
		cpi		0Ah			; LF
		jz		LF
		cpi		01Fh		; Очистка экрана
		jz		Clear
		cpi		8			; Влево
		jz		Left
		cpi		018h		; Вправо
		jz		Right		; loc_FBE8
		cpi		019h		; Вверх
		jz		Up
		cpi		01Ah
		jz		Down		; loc_FC0D Вниз
		cpi		0Ch
		jz		Home		; Начало экрана
		cpi		7
		jnz		Spc			; Пробел
;		call	CallBn2		; 
		call 	ExtFE0A		; Звуковой сигнал
; ───────────────────────────────────────────────────────────────────────────
;		.dw 	0hFE0A			; ExtFE0A
; ───────────────────────────────────────────────────────────────────────────
		ret
		
; Вывод пробела
Spc:
;		call	CallBn2		; 
		call 	ExtFC00		; 
; ───────────────────────────────────────────────────────────────────────────
;		.dw 	0hFC00 			;  ExtFC00

; Перемещение вправо
Right:
loc_FBE8:
		inr		e
		inx		h
		in		SysPrtC     ; 0C2h
		ani		4
		mov		a, e
		jz		i_81			; loc_FBFA
		ani		3
		dcr		a
		jnz		i_82			; loc_FBFE
		dcx		h
		ret
i_81:							; loc_FBFA:
		ani		1
		rnz
		inx		h
i_82:							; loc_FBFE:
		mov		a, l		; столбец
		ani		03Fh
		cpi		03Eh		; предпоследний
		rc					; нет
		call	CR			; Да перейти на начало строки
		
; Переход на новую строку
LF:
		mov		a, d		; символ для вывода
		cpi		018h		; вправо
		jz		Rght		; Да перейти на подпрограмму
		
; Перемещение вниз
Down:
;loc_FC0D:
		lxi		b, 0240h
		dad		b
		inr		d
		mov		a, d
		cpi		019h
		rc
		lxi		b, 0C7C0h
		dad		b
		mvi		d, 0
		ret
		
; Вправо
Rght:
		push	h
		push	d
		lxi		h, 0
		dad		sp
		shld	TmpStk
		lhld	word_F6DC	; Начало текущего буфера экрана
		inx		h
		inx		h			; Смещаемся на 2 байта
		push	h			; сохраняем
		lxi		b, 0240h
		dad		b
		pop		d			; восстанавливаем
		sphl
		xchg
		lxi		b, 01BE0h	; количество
i_91:
		pop		d
		mov		m, e
		inx		h
		mov		m, d
		inx		h
		dcr		c
		jnz		i_91
		dcr		b
		jnz		i_91

		lhld	word_F6DC	; Начало текущего буфера экрана
		lxi		d, 03800h	; размер экрана
		dad		d			; Добавляем к адресу буфера
		sphl				; адрес в указатель стэка
		lxi		d, 0		; обнуляем
		mvi		b, 090h		; количество записей
i_92:
		push	d			; Записываем данные
		push	d			; Записываем данные
		dcr		b
		jnz		i_92		; Все записали?
		lhld	TmpStk		; Возвращаем стэк
		sphl				; на место
		pop		d
		pop		h			; Восстанавливаем указатель стэка
		ret

; Переход на начало строки
CR:
		mov		a, l
		ani		0C0h
		ori		2
		mov		l, a
		mvi		e, 0
		ret
		
; Очистка экрана
Clear:
		lxi		h, 0
		dad		sp
		xchg					; DE указатеь стэла
		lhld	word_F6DC		; Начало текущего буфера экрана 
		lxi		b, 03800h		; Размер экрана
		dad		b				;
		sphl					; В стэке адрес
		lxi		h, 0			; Обнуляем
		shld	word_F67E		; Запоминаем
		shld	byte_F67F
		lxi		b, 0E00h		; Количество
CCle1:
		push	h				; Записываем данные
		push	h
		dcr		c
		jnz		CCle1
		dcr		b
		jnz		CCle1
		xchg
		sphl					; Возвращаем стэк
		
; Переход в начало экрана
Home:
		lhld	word_F6DC		; Начало текущего буфера экрана
		lxi		d, 01C2h
		dad		d
		lxi		d, 0
		ret

L1:								; ????? Как сюда попасть
		mov		a, l
		xri		03Fh
		mov		l, a
		mvi		e, 028h
		in		SysPrtC    ; 0C2h
		ani		4
		jz		L2
		mvi		e, 050h
L2:
		call	Up
		
; Перемещение влево
Left:
		dcx		h
		dcr		e
		jm		L1
		in		SysPrtC    ; 0C2h
		ani		4
		mov		a, e
		jz		L3
		ani		3
		rnz
		inx		h
		ret

L3:
		ani		1
		rz
		dcx		h
		ret

; Перемещение вверх
Up:	
		lxi		b, 0FDC0h		;
		dad		b
		dcr		d
		rp
		lxi		b, 03840h
		dad		b
		mvi		d, 018h
		ret

loc_FCCC:
		ani		1
		mov		b, a
		xra		c
		mov		c, a
		rrc
		jmp		i_103			; loc_FCEF

; ───────────────────────────────────────────────────────────────────────────
; Вывод на дисплей
;
Sub_FCD5:
		push	b			; FCD5h
		call	sub_FD49
		mvi		h, 0
		pop		b
		mov		a, c
		sui		' '
		mov		c, a
		in		SysPrtC    ; 0C2h
		ani		4
		mov		a, c
		jz		loc_FCCC
		ani		3
		mov		b, a
		xra		c
		mov		c, a
		rrc
		rrc

i_103:							; loc_FCEF:
		mov		l, a
		mov		e, l
		mov		d, h
		dad		h
		dad		d
		mov		e, c

i_101:							; loc_FCF5:
		dcr		b
		jm		i_102			; loc_FCFF
		call	loc_FBE8
		jmp		i_101			; loc_FCF5

i_102:							; loc_FCFF:
		push	h
		lda		byte_F6E2
		sui		020h
		mov		d, a
		mov		b, h
		mov		l, a
		mov		c, l
		dad		h
		dad		h
		dad		h
		dad		b
		dad		h
		dad		h
		dad		h
		dad		h
		dad		h
		dad		h
		push	h
		lhld	word_F6DC	; Начало текущего буфера экрана
		lxi		b, 01C2h
		dad		b
		pop		b
		dad		b
		pop		b
		dad		b

; Вывод на дисплей

Dat1:
		shld	word_F66A	; Адрес позиции курсора
		xchg
		shld	XYCur		; позиция курсора
		mov		a, l
		ani		3
		mov		l, a
		in		SysPrtC    ; 0C2h
		ani		4			; Прверяем цветной/монохром
		add		l
		lxi		h, DefCrt2	; Программа вывода на дисплей в графическом режиме
		shld	AdefCrt		; Установить адрес
		mov		l, a		; Смещение в таблице
		rlc
		add		l
		lxi		h, Tbl1
		add		l			; Добавляем смещение
		mov		l, a
		mov		a, m		; Читаем данные
		sta		byte_F66D	; запоминаем ст. байт программы вывода пробела ?????
		inx		h			; следующее
		mov		a, m		; временно сохраняем
		inx		h			; следующее
		mov		h, m
		mov		l, a		; считанные данные в HL
		shld	word_F6D9	; Сохраняем
sub_FD49:
		lhld	word_F6D9	; Восстанавливаем
		xchg
		lhld	word_F66A	; Адрес позиции курсора
		lda		Conf		; Читаем конфигурацию
		ani		40h
		rnz
		push	h
		call	sub_FD63
		lxi		b, 03Fh
		dad		b
		call	sub_FD63
		pop		h
		ret

sub_FD63:
		lda		byte_F669
		mov		b, a
		ana		e
		xra		m
		mov		m, a
		inx		h
		mov		a, b
		ana		d
		xra		m
		mov		m, a
		ret
; ───────────────────────────────────────────────────────────────────────────
Tbl1:		
		db  1Fh, 0FFh, 33h, 19h, 0CCh, 0FFh, 1Fh
		db  0FFh, 33h, 19h, 0CCh, 0FFh, 1Fh, 3Fh, 0
		db  1Dh, 0C0h, 0Fh, 01Bh, 0F0h, 3, 19h, 0FCh
		db    0, 11h, 22h, 44h, 88h
		db    1, 2, 4, 8, 10h, 20h, 40h, 80h

; Обработка последовательности ESC
ESC:
;loc_FD94:
		lxi		h, loc_FD9A
		jmp		loc_FB54
		
;
loc_FD9A:
		mov		a, c			; следующий байт за ESC
		cpi		059h 			;
		jz		Cmd59			;loc_FB46
		cpi		058h 			; Выбор конфигурации
		jz		Config			;loc_FAF4
		cpi		05Ah 			; Выбор цветовой палитры
		jz		Palet			;loc_FB31
		cpi		4				; Выбор Точки на экране 4 - 5
		jc		Point4			;loc_FFBD
		cpi		012h			;
		jnc		Cmd12			;loc_FFE0
		ani		1
		sta		byte_F6DB
		xra		c
		mvi		b, 2
		cpi		8				; 
		jc		i_111				; loc_FDC8
		cpi		010h			; Переключение знакогенератора 10 - 11
		jnc		i_111				; loc_FDC8
		mvi		b, 6
i_111:								; loc_FDC8:
		mov		e, a
		mvi		d, 0
		lxi		h, 0FB84h
		dad		d
		mov		a, m
		inx		h
		mov		h, m
		mov		l, a
		mov		a, b
		jmp		loc_FB4B

; ───────────────────────────────────────────────────────────────────────────
Sub_0FDD7:
		lda		byte_F6E2	; FDD7h
		mov		b, a
		mvi		a, 0DFh
		sub		c
		rc
		mov		c, a
		mov		l, a
		mov		h, b
		shld	word_F67E
		lda		byte_F6DB
		sta		byte_F680
		call	sub_FF67
		
sub_FDEE:
		lda		Conf		; Конфигурация
		rlc
		jc		loc_FDF9
		mov		a, b
		cma
		ana		m
		mov		m, a
loc_FDF9:
		lda		byte_F669
		ana		b
		xra		m
		mov		m, a
		ret

; ───────────────────────────────────────────────────────────────────────────
Sub_0FE00:
		call	sub_FE64	; FE00h
loc_FE03:
		push	b
		push	h
i_123:							; loc_FE05:
		ldax	d
		mov		m, a
		inx		h
		inx		d
		dcr		c
		jnz		i_123			; loc_FE05
		pop		b
		lxi		h, 0FFC0h
		dad		b
		pop		b
		dcr		b
		jnz		loc_FE03
		ret
		
; ───────────────────────────────────────────────────────────────────────────
Sub_0FE18:
		call	sub_FE64	; FE18h
loc_FE1B:
		push	b
		push	h
loc_FE1D:
		mov		b, m
		ldax	d
		mov		m, a
		mov		a, b
		stax	d
		inx		h
		inx		d
		dcr		c
		jnz		loc_FE1D
		pop		b
		lxi		h, 0FFC0h
		dad		b
		pop		b
		dcr		b
		jnz		loc_FE1B
		ret
; ───────────────────────────────────────────────────────────────────────────
Sub_0FE33:
		call	sub_FE64	; FE33h
i_331:							; loc_FE36:
		push	b
		push	h
i_332:							; loc_FE38:
		ldax	d
		xra		m
		mov		m, a
		inx		h
		inx		d
		dcr		c
		jnz		i_332			; loc_FE38
		pop		b
		lxi		h, 0FFC0h
		dad		b
		pop		b
		dcr		b
		jnz		i_331			; loc_FE36
		ret
; ───────────────────────────────────────────────────────────────────────────
Sub_0FE4C:
		call	sub_FE64	; FE4Ch
loc_FE4F:
		push	b
		push	h
loc_FE51:
		mov		a, m
		stax	d
		inx		h
		inx		d
		dcr		c
		jnz		loc_FE51
		pop		b
		lxi		h, 0FFC0h
		dad		b
		pop		b
		dcr		b
		jnz		loc_FE4F
		ret

sub_FE64:
		lda		byte_F6E2
		mov		b, a
		push	b
		lhld	word_F6E5
		mov		b, h
		mvi		a, 0DFh
		sub		l
		mov		c, a
		call	sub_FF67
		xchg
		lhld	word_F6E3
		xchg
		pop		b
		mov		a, c
		ora		a
		ral
		rrc
		mov		c, a
		rp
		in		BB75Stat    ; 0E1h
loc_FE82:
		in		BB75Stat    ; 0E1h
		ani		020h
		rnz
		jmp		loc_FE82
		
; ───────────────────────────────────────────────────────────────────────────
Sub_0FE8A:
		lhld	byte_F67F	; FE8Ah
		lda		word_F67E
		mov		b, a
		mvi		a, 0DFh
		sub		c
		mov		c, a
		sta		word_F67E
		lda		byte_F6DB
		mov		d, a
		lda		byte_F6E2
		mov		e, a
		xchg
		shld	byte_F67F
		xchg
		push	b
		mov		a, l
		sub		e
		mov		c, a
		mov		a, h
		sbb		d
		mov		b, a
		jnc		i_131			; loc_FEBB
		cma
		mov		b, a
		mov		a, c
		cma
		mov		c, a
		inx		b
		xchg
		xthl
		mov		a, h
		mov		h, l
		mov		l, a
		xthl
i_131:							; loc_FEBB:
		mov		l, c
		mov		h, b
		shld	Area3		; word_F6C5
		pop		b
		push	h
		mov		a, b
		sub		c
		lxi		h, 040h
		jnc		i_132			; loc_FECF
		cma
		inr		a
		lxi		h, 0FFC0h
i_132:							; loc_FECF:
		shld	Area2
		mov		b, a
		pop		h
		push	d
		push	h
		mov		a, h
		rrc
		mov		a, l
		lxi		h, Sub_FFAF
		lxi		d, Sub_FFB5
		jc		i_133			; loc_FEEF
		cmp		b
		jnc		i_133			; loc_FEEF
		xchg
		mov		a, b
		sta		Area3		; word_F6C5
		xthl
		mov		b, l
		mov		l, a
		xthl	
i_133:							; loc_FEEF:
		shld	word_F670
		xchg
		shld	word_F673
		pop		d
		lda		Area3		; word_F6C5
		ora		a
		jz		i_134			; loc_FF65
		push	b
		lxi		h, 0FFFFh
		mov		a, b
		cmp		e
		jnz		i_135			; loc_FF0C
		mov		a, d
		ora		a
		jz		i_136			;
i_135:							; loc_FF0C:
		push	d
		mov		e, b
		mvi		d, 0
		pop		b
		inx		h
		mvi		a, 010h
i_137:							; loc_FF14:
		push	psw
		dad		h
		xchg
		dad		h
		xchg
		mov		a, d
		cmp		b
		jc		i_138			; loc_FF2D
		jnz		i_139			; loc_FF26
		mov		a, e
		cmp		c
		jc		i_138			; loc_FF2D
i_139:							; loc_FF26:
		inx		h
		mov		a, e
		sub		c
		mov		e, a
		mov		a, d
		sbb		b
		mov		d, a
i_138:							; loc_FF2D:
		pop		psw
		dcr		a
		jnz		i_137			;
		inx		h
i_136:							; loc_FF33:
		pop		b
		pop		d
		push	h
		mov		a, d
		sta		byte_F6DB
		mov		b, e
		call	sub_FF67
		pop		d
		push	h
		lxi		h, 08000h
		xthl
		lda		Area3		; word_F6C5
		mov		c, a
		call	sub_FDEE
i_1310:						; loc_FF4B:
		call	unk_F66F
		call	sub_FDEE
		xthl
		dad		d
		xthl
		cc		unk_F672
		dcr		c
		jnz		i_1310			; loc_FF4B
		lda		Area3 + 1		; word_F6C5+1
		dcr		a
		sta		Area3 + 1	; word_F6C5+1
		jp		i_1310			; loc_FF4B
i_134:							; loc_FF65:
		pop		psw
		ret

sub_FF67:
		mvi		h, 0
		mov		l, c
		dad		h
		dad		h
		dad		h
		dad		h
		dad		h
		dad		h
		in		SysPrtC    ; 0C2h
		ani		4
		mvi		a, 4
		jz		i_141			; loc_FF7A
		rlc
i_141:							; loc_FF7A:
		mov		c, a
		dcr		c
		mov		a, b
		ana		c
		mov		e, a
		mov		a, c
		cma
		ana		b
		rrc
		rrc
		dcr		c
		jpo		i_142			; loc_FF89
		rrc
i_142:							; loc_FF89:
		mov		c, a
		mvi		b, 0
		dad		b
		mov		c, l
		mov		b, h
		lhld	word_F6DC
		dad		b
		inx		h
		inx		h
		lda		byte_F6DB
		ora		a
		jz		i_143			; loc_FFA0
		lxi		b, 020h
		dad		b
i_143:							; loc_FFA0:
		xchg
		mov		b, l
		lxi		h, 0FD88h
		in		SysPrtC    ; 0C2h
		ani		4
		add		b
		add		l
		mov		l, a
		mov		b, m
		xchg
		ret
; ───────────────────────────────────────────────────────────────────────────
Sub_FFAF:
		mov		a, b		; FFAFh
		rlc
		mov		b, a
		rnc
		inx		h
		ret
; ───────────────────────────────────────────────────────────────────────────
Sub_FFB5:
		push	d			; FFB5h
		xchg
		lhld	Area2		; word_F6C3
		dad		d
		pop		d
		ret
; ───────────────────────────────────────────────────────────────────────────
; Выбор Точки на экране 4 - 5
Point4:
loc_FFBD:
		ora		a
		jz		i_152			; loc_FFD5
		in		SysPrtC     ; 0C2h
		ani		4
		jnz		i_151			; loc_FFD3
		mvi		a, 0Fh
		dcr		c
		jz		i_152			; loc_FFD5
		cma
		dcr		c
		jz		i_152			; loc_FFD5
i_151:							; loc_FFD3:
		mvi		a, 0FFh
i_152:							; loc_FFD5:
		push	psw
		call	sub_FD49
		pop		psw
		sta		byte_F669
		call	sub_FD49
		
; Команда 12h  из ERS последовательности
Cmd12:
loc_FFE0:
		lxi		h, DefCrt2
		shld	AdefCrt
		ret
		
; Начальный старт
Start:
		lxi		h, MagI10	;
		push	h
		push	psw
		xra		a			; Установить 0 страницу
		out		SysPrtCtl   ; 0C3h 
		pop		psw
		ret			;

; ───────────────────────────────────────────────────────────────────────────
		DEFM "15-01-24"		; Дата написания
		REPT 0x800 - ASMPC - 2
			db 	0x80
		ENDR
		db 0F8h,00
		ASSERT	ASMPC == 0x800

