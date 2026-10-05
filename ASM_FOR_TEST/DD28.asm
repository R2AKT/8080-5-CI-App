	PUBLIC	Mon
	PUBLIC	ExtFD86, ExtFED4, ExtFC72, ExtFD5A, ExtFF36, ExtFF8E, ExtFE0A, ExtFC00

; Эти находлятся в модуле kp04_DD29
	EXTERN 	MON, mStrt, mCI, mMI, mOutDsp, mMO, mLP, mKeySt, mOutHex, mOutTxt,  Znk
	EXTERN	mInKey, mCurXY, mDspBuf, mMGblI, mMGblO, mCRSbl, mDspOn, mRMem, mWMem

; Эти находятся в модуле kp04_Comm
;	EXTERN	word_F66A, unk_F603, unk_F66C, byte_F679, word_F6DE
;	EXTERN	word_F67A, byte_F67D, word_F683, word_F681, unk_F609
;	EXTERN	word_F600, byte_F67E, word_F6D9, byte_F669, word_F6DC

; Эти находятся в модуле kp04_Comm
;	EXTERN	Conf, AdefCrt, DspBuf, XYCur, FlagKey, TmpStk, Area2, Area3, AdefCrt
;	EXTERN	endBuf1, Buf, HiMem, SrcDMA1, ppDMA, CmdGo, BegBUF, Stack,

include	"Comm.def"
include "Dop.def"
include "DD30.def"
;include "DD29.def"

;title 	"Монитор начало DD28"
module 	MonDD28

include	"AdrIO.inc"


		org 0F000h
	SECTION 	kp04_DD28

Mon:		
;		jmp		Init		; Для включения правильного выбора адресов при старте
Init:
;		mvi		a, 08Ah
;		out		SysPrtCtl   ; Настройка ППА, управляющее слово
;		lxi		sp, Stack	; Устанавливаем стэк
;		in		ColPrtA     ; 0 Считываем данные
;		mov		c, a		; Запоминаем
;		mvi		a, 055h 	; Шаблон проверки
;		out		ColPrtA     ; 0 Проверка на наличие блока цветности
;		in		ColPrtA     ; 0 Считываем шаблон
;		xri		055h		; Проверяем
;		mov		a, c		; Возвращаем данные
;		out		ColPrtA     ; 0
;		jnz		i_1			; Совпал шаблон
;		mvi		a, 080h 	; Блок цветности присутсвует
;		out		ColPrtCtl	; Настраваем ППИ
;		mvi		a, 8
;		out		ColPrtA     ; Блок цветности данные
;		mvi		a, 020h
;		out		ColPrtB		; Блок цветности данные
;		mvi		a, 080h
;		out		ColPrtC		; Блок цветности данные
i_1:							; Сюда перешли если нет блока цветности
		mvi		a, 030h
		out		TimC    	; Настраиваем таймер
		mvi		a, 070h
		out		TimC    	;
		mvi		a, 0B6h
		out		TimC    	;
		xra		a
		out		Tim1    	; обнуляем МБ счетчика 0
		out		SysPrtA    	; ППА регистр А
		inr		a
		out		Tim1    	; устанавливаем СБ счетчика 0
		in		SysPrtB    	; ППА регистр А
		inr		a
		jz		Begin		; Клавиша не нажата, пропускаем	тест памяти
		lxi		h, HiMem	; Максимальный адрес ОЗУ
i_2:						; TstOZU:
		dcx		h			; Заполнение всей доступной памяти
		mov		m, l
		mov		a, l
		ora		h
		jnz		i_2;		; TstOZU	; Заполнение всей доступной памяти
		lxi		h, HiMem	; Максимальный адрес ОЗУ
i_3:
		dcx		h			; Проверка заполненой памяти
		mov		a, m
		xra		l
		jnz		TstErr		; F855 Ошибка сравнения памяти
		xra		l
		ora		h
		jnz		i_3			; Проверка заполненой памяти
		jmp		TstPZU		; Проверка ПЗУ
		
; Вывод сигнала и текст ошибки
TstErr:		
		mov		e, a		; Ошибка сравнения памяти
		mvi		a, 01Ch
		out		Tim2    	; 0D2h Выводим сигнал
		mvi		a, 6
		out		Tim2    	; 0D2h Частота сигнала
		mvi		a, 012h
		out		Tim1    	; 0D1h
		mvi		a, 07Ah
		out		Tim1    	; 0D1h Длительность сигнала
;		call	Common		;
		call 	mDspOn		; Запустить отображение
		call	OutText
; ───────────────────────────
		DEFM 	"neisprawna D",0
;		DEFM	"неисправна D",0
; ───────────────────────────
		mov		c, a
		mov		a, e
i_10:
		inr		c			; Номер	неисправной микросхемы
		rrc
		jnc		i_10
		mvi		a, 035h
		add		c
		daa
		call 	mOutHex
;		.dw 	 0hF815		; Адрес для вызываемой программы
		jmp		InK7
		
; 
TstPZU:
;		call	Common		; Прверка ПЗУ
		call 	mDspOn		; Запустить отображение
		call	OutText
; ─────────────────────────────
		DEFM 	"ozu isprawno",0
;		DEFM 	"ОЗУ исправно",0
; ─────────────────────────────

InK7:
		call	KeyRelease	; ожидание нажатие клавиши

Begin:
;		call	Common		; переносим блок подпрограмм для всех ПЗУ
		call 	mDspOn		; Запустить отображение
;		call	TestROM		; Тестируем ПЗУ
		lxi		h, Buf		; Очищаем рабочую область
		lxi		d, ppDMA	;
		mvi		c, 0FFh		; Образец для записи
		call	CmdF		; Заполнить область  образцом
		lxi		h, SrcDMA1	; Другая область для работы
		lxi		d, endBuf1
		mvi		c, 0F0h		; Образец для заполнения
		call	CmdF		; Заполнить область  образцом
		call	OutText		; Вывести заставку и меню
;──────────────────────────────────────────────────
; Заставка
		db  01Bh
		db    2
		db  01Fh
K1:		db  01Bh
		db  059h 		; Y Прямая адресация курсора
		db  020h		; Х = 0
		db  02Ah 		; У = 10
A11:	db  022h
		DEFM 	"|lektronika kr-04"
;		DEFM 	"Электроника КР-04"
		db 022h
		db 01Bh
		DEFM 	"Y7)(C)  urlz  1990"
;		DEFM	"У7)(С)  УРЛЗ  1980"
		db 01Bh
		DEFM "Y*%48k/40"
		db 01Bh
;		DEFM "Y*916k/64"
;		db 01Bh
		DEFM "Y,%48k/80"
		db 01Bh
		DEFM "Y,932k/64"
		db 01Bh
		db 0
;────────────────────────────────────────────────
		mov		c, a
		call 	mOutDsp		; Вывести на дисплей
;		dw 	0F809h
i_11:
		mvi		e, 1
i_12:
		call	Switch		; Переключение конфигурации
		call 	mCI			; Ввести с клавиатуры
;		dw 	0F803h
		cpi		0Dh			; ВК
		jz		Beg3		; Выбор завершен
		call	Switch		; Преключаем конфигурацию
		mov		a, e
		adi		2
		mov		e, a
		cpi		4			; Проверяем для очистки экрана
		jz		i_11			; F941
		jc		i_12			;
		mvi		e, 0
		jmp		i_12

; ожидание нажатие клавиши
KeyRelease:
		xra		a
		out		SysPrtA    ; 0C0h
KeyPush:
		in		SysPrtB    ; 0C1h
		inr		a
		jz		KeyPush
KeyUnpush:
		in		SysPrtB    ; 0C1h
		inr		a
		jnz		KeyUnpush
		ret

; Блок подпрограмм для всех ПЗУ
;Common:
;		lxi		h, CommBeg		; Начало блока
;		lxi		d, CommEnd		; Конец	блока
;		lxi		b, TestROM		; Куда перемещается
;		call	CmdT			; Переместить блок памяти
;		call	
;		call 	mDspOn			; Запустить отображение
;		dw 	0F82Dh
;		ret

;Ozu16K:
;		call	OutText
; ─────────────────────
;		DEFM "16k/64)",0
; ─────────────────────
;		jmp		Prompt

;Ozu48K:
;		call	OutText
; ────────────────────
;		DEFM "48k/40)",0
;  ───────────────────
;		jmp		Prompt

Ozu32K:
		call	OutText
; ─────────────────────
		DEFM "32k/64)",0
; ─────────────────────
		jmp		Prompt
		
; Переключение конфигурации
Switch:	
		mov		a, e
		dcr		a
;		jm		Sw1
;		jz		Sw2
		rrc
		jc		Sw3
; Режим 3
		call	OutText
; ──────────────────────
		db 	01Bh, 0Ch, 01Eh, 06Bh, 0F6h, 0E8h, 0Ah, 0Ah, 0
; ──────────────────────
		mvi		d, (ADspBuf >> 8) & 0xFF	; Адрес буфера экрана (старший байт)
							; Для 2ВГ75 нужно указать адрес ОЗУ
		ret
		
; Режим 0
;Sw1:
;		call	OutText
; ──────────────────────
;		db 0h1B
;		db  0hC
;		db  0h96 ; Ц
;		db  0h7D ; }
;		db 0hF6 ; ?
;		db 0hE8 ; ш
;		db  0hA
;		db  0hA
;		db    0
; ─────────────────────
;		mvi		d, 036h 	; Адрес буфера экрана (старший байт)
							; Для 2ВГ75 нужно указать адрес ОЗУ
;		ret
		
; Режим 1
;Sw2:
;		call	OutText
; ─────────────────────
;		db  	01Bh, 0Ch, 01Eh, 07Dh, 0F6h, 0E8h, 0Ah, 0Ah, 0
; ─────────────────────
;		mvi		d, 0A6h		; Адрес буфера экрана (старший байт)
							; Для 2ВГ75 нужно указать адрес ОЗУ
;		ret
		
; Режим 2
Sw3:
		call OutText
; ─────────────────────
		db  	01Bh, 0Ch, 096h, 06Bh, 0F6h, 0E8h, 0Ah, 0Ah, 0
; ────────────────────
		mvi		d, 076h 	; Адрес буфера экрана (старший байт)
							; Для 2ВГ75 нужно указать адрес ОЗУ
		ret
		
; Приняли выбор конфигурации		
Beg3:	
		mov		a, e		; Выбранная конфигурация
		sta		Conf		; Запомнить её
		mov		a, d		; Старший байт буфера экрана
		sta		DspBuf + 1  ; Запомнить
		call 	mDspOn		; Запустить отображение
;		dw 	0F82Dh			; Запустить дисплей
		lxi		sp, Stack	; Установить стэк
		di					; запретить прерывания
		mvi		a, 030h
		out		TimC    	; 0D3h	; Команда
		mvi		a, 070h
		out		TimC    	; 0D3h
		mvi		a, 0B6h
		out		TimC    	; 0D3h
		mvi		a, 0Fh
		out		Tim1    	; 0D1h	; канал 1 0F0FH
		out		Tim1    	; 0D1h
		out		Tim2    	; 0D2h	; канал 2 0F0Fh
		out		Tim2    	; 0D2h
		call 	OutText
; ────────────────────
Msg7:	db 01Bh, 2, 0Dh, 0Ah, "kr-04 (", 0
;		DEFM 	"|lektronika kr-04 (",0
;		DEFM	"Электроника КР-04 (",0
; ──────────────────

MsgConf:
		lda		Conf		; Получить конфигурацию
		ani		3			; Выделить нужные биты
		dcr		a			; 
;		jm		Ozu16K		; Конфигурвция 0
;		jz		Ozu48K		; Конфигурация 1
		rrc	
		jc		Ozu32K		; Конфигурация 2
		call	OutText		; Конфигурация 3
; ──────────────────
		DEFM "48k/80)",0
; ──────────────────

;MsgC1:
;		call	OutText		; Закрыть скобку
; ─────────────────
;		DEFM  	")",0
; ─────────────────

Prompt:	
		lxi		sp, Stack	; Установит стэк
		call	OutText	 	; Вывести приглашение
; ─────────────────────
		db 0Dh, 0Ah, "m->",0
; ─────────────────────
		di					; Запретить прерываня
		call	sub_FAB7
		lxi		h, Prompt
		push	h			; Запомнить для возврата
		lxi		h, SrcDMA1	; Буфер
		mov		a, m		; Получить данные
		push	psw			; Сохранить
		call	CmdParam	; Введение параметров команды
		lhld	Area3		; Третий аргумент
		mov		c, l
		mov		b, h		; в ВС
		lhld	Area2		; Второй аргумент
		xchg				; в DE
		lhld	TmpStk		; Первый аргумент адрес	подпрограммы в HL
		pop		psw			; Восстановить команду
		cpi		'D'			; Дамп области пвмяти
		jz		CmdD
		cpi		'C'			; сравнение содержимого двух областей памяти
		jz		CmdC
		cpi		'F'			; Заполнить область памяти константой
		jz		CmdF		; Запонить область  образцом
		cpi		'S'			; поиск кода в заданной области памяти
		jz		CmdS
		cpi		'T'			; Переместить область памяти
		jz		CmdT		; Переместить блок памяти
		cpi		'M'			; просмотр и изменение ячеек памяти
		jz		CmdM
		cpi		'I'			; Ввести  с магнитофона
		jz		CmdI
		cpi		'O'			; Вывести на магнитофон
		jz		CmdO
		cpi		'R'			; Выполнить программу из ПЗУ
		jz		CmdR
		cpi		'L'			; Секретная программа
		jz		Error		; Met3
		cpi		'G'			; Выполнить программу с адреса
		jnz		Error
		call 	CmdGo		; Выполнить программу с адреса
;		dw 	0F6C0h		;
		ret
		
; Стереть предыдущий символ
CmdBS:
		mvi		a, 0E8h
		cmp		l
		jz		c_1
		push	h
		call	OutText
; ───────────────────────
		db    8, 020h, 8, 0
; ───────────────────────
		pop		h
		dcx		h
		jmp		c_2

sub_FAB7:
		lxi		h, SrcDMA1
c_1:					;loc_FABA:
		mvi		b, 0
c_2:							;loc_FABC:
;		call	CallDE
		call 	mCI				; Ввод с клавиатуры
;		dw 	0F803h
		cpi		8
		jz		CmdBS
		cpi		07Fh
		jz		CmdBS
		mov		c, a
		jz		c_3			;loc_FAD2
;		call	CallDE
		call 	mOutDsp			; Вывод на дисплей
c_3: 	equ 	ASMPC - 2
;		dw 	0F809h
		mov		m, a
		cpi		0Dh
		jz		c_4				;loc_FAEB		; Завершение программы
		cpi		02Eh 			; точка
		jz		Prompt			; перейти на начало
		mvi		b, 0FFh
		mvi		a, 0FCh			;
		cmp		l				; Начало строки
		jz		Error			; Ошибка
		inx		h
		jmp		c_2				;loc_FABC		; обработать следующее
c_4:							;loc_FAEB:
		mov		a, b
		ral
		lxi		d, SrcDMA1
		mvi		b, 0
		ret

; Введение параметров команды
CmdParam:
		lxi		h, TmpStk	; Адрес для Go
		lxi		d, Buf		; Адрес буфера
		mvi		c, 0		; шаблон
		call	CmdF		; Очистить буфер
		lxi		d, BegBUF	; Начало другого буфера
		call	Trmn		; Проверка на разделитель и окончание ввода
		shld	TmpStk 		; Первый аргумент адрес перехода
		rc					; Возврат если нужен один аргумент
		call	Trmn		; Проверка на разделитель и окончание ввода
		shld	Area2		; Второй аргумент
		rc					; Возврат когда два аргумента
		call	Trmn		; Проверка на разделитель и окончание ввода
		shld	Area3		; Третий аргумент
		rc					; Взврат когда три аргумента
		jmp		Error		; Ошибка больше трех аргументов

; Проверка на разделитель и окончание ввода
Trmn:
		lxi		h, 0
i_21:
		ldax	d
		inx		d			
		cpi		0Dh			; Конец	ввода
		stc					; Установить флаг С
		rz
		cpi		022h		; Ковычки
		stc					; Установить флаг С
		rz
		cpi		02Ch		; Запятая
		rz
		cpi		020H		; Пробел
		jz		i_21			; следующий
		sui		030H
		jm		Error
		cpi		0AH			; Перевод строки
		jm		i_22
		cpi		011H	    ; 11h
		jm		Error
		cpi		017H
		jp		Error
		sui		7
i_22:
		mov		c, a
		dad		h
		dad		h
		dad		h
		dad		h
		dad		b
		jmp		i_21

; Сравнение  регистров и инкремент регистра
CmpInx:
		call	CmpHLxDE	; Сравнение регистров
		jnz		inxHL
		inx		sp			; уменьшаем указатель стэка
		inx		sp
		ret
;
inxHL:
		inx		h			; Уменьшаем HL
		ret
		
; Директива R чтение из ПЗУ диска
CmdR:
		mvi		a, 090H
		out		RomPrtCtl   ; 13h Режим ППА
I_31:
		mov		a, l
		out		RomPrtB     ; 11h Адрес ПЗУ
		mov		a, h
		out		RomPrtC     ; 12h Адрес ПЗУ
		in		RomPrtA     ; 10h Данные из ПЗУ
		stax	b			; Сохраняем
		inx		b
		call	CmpInx		; Сравнение  регистров и инкремент регистра
		jmp		I_31			; Повторяем

; Сравнение регистров
CmpHLxDE:
		mov		a, l
		cmp		e
		rnz
		mov		a, h
		cmp		d
		ret

; Перейти на новую строку
NewLine:
		push	h
		call	OutText
;──────────────────────
		db  0DH, 0AH, 0
;──────────────────────
		pop		h
		ret
		
; Вывод пробела
Space::
		mvi		c, ' '
		call 	mOutDsp			; Вывод на дисплей
;		dw 	0F809H
		ret
		
; Вывод содержимого памяти в 16 виде и пробела
sub_FB83:	
		mov		a, m			; Читаем данные
sub_FB84:
		push	b
		call 	mOutHex			; Вывод в 16 виде
;		dw 	0F815H
		call	Space			; Выводим пробел
		pop		b
		ret
		
; Директива D
CmdD:
		mov		a, l
		ani		0F8H
		mov		l, a
		mov		a, e
		ori		7
		mov		e, a
		call	sub_FC79
		mov		c, l
		mov		b, h
		call	sub_FBC2
		mov		l, c
		mov		h, b
		call	Space			; sub_FB7B
I_41:
		mov		a, m
		ora		a
		jm		I_42
		cpi		20h
		jnc		I_43
I_42:
		mvi		a, '.'		;0h2E Точка если символ меньше 20h
I_43:
		mov		c, a		; Выводим символ
		call 	mOutDsp		; Вывод на дисплей
;		dw 	0F809H
		call	CmpInx		; Сравнение  регистров и инкремент регистра
		mvi		a, 7
		ana		l
		jnz		I_41			; следующий
		jmp		CmdD		; с новой строки

sub_FBC2:
		call	sub_FB83	; Получить и вывести символ в  16 и пробел
		call	CmpInx		; Сравнение  регистров и инкремент регистра
		in		SysPrtC     ; 0C2h
		mvi		a, 7
		ana		l
		jnz		sub_FBC2	; Повторить
		ret
		
; Директива C
CmdC:
		ldax	b			; Получить символ	
		cmp		m			; Сравнить
		jz		i_51
		call	sub_FC79	; не равны
		call	sub_FB83	; Получить и вывести символ в  16 и пробел
		ldax	b			; Получить символ
		call	sub_FB84	; Вывести символ в  16 и пробел
i_51:							; равны
		inx		b			; Следующий адрес
		call	CmpInx		; Сравнение  регистров и инкремент регистра
		jmp		CmdC		; повторить

; Запонить область  образцом
CmdF:
		mov		m, c		; Записать образец
		call	CmpInx		; Сравнение  регистров и инкремент регистра
		jmp		CmdF		; Повторить
		
; Директива S
CmdS:
		mov		a, c
		cmp		m
		cz		sub_FC79
		call	CmpInx		; Сравнение  регистров и инкремент регистра
		jmp		CmdS

; Переместить блок памяти
CmdT:
		mov		a, m
		stax	b
		inx		b
		call	CmpInx		; Сравнение  регистров и инкремент регистра
loc_FBFF:					; Переместить блок памяти
		jmp		CmdT
		
; Директива M
CmdM:
		call	sub_FC79
		call	sub_FB83
		push	h
		call	sub_FAB7
		pop		h
		jnc		i_61
		push	h
		call	Trmn		; Проверка на разделитель и окончание ввода
		mov		a, l
		pop		h
		mov		m, a
i_61:
		inx		h
		jmp		CmdM
;
; Директива I
CmdI:
		mov		a, e
		ora		d
		jz		i_71
		xchg
		shld	word_F683
		xchg
i_71:
		call 	mMGblI
;		dw 	0F824h			; Ввод блока с магнитофона
		jc		Error
		call	sub_FC79
		xchg
		call	sub_FC79
		xchg
		push	b
		call 	mCRSbl
;		dw 	0F82Ah				; Контрольная сумма блока
		mov	 	h, b
		mov		l, c
		call	sub_FC79
		pop		d
		call	CmpHLxDE	; Сравнение регистров
		rz
		xchg
		call	sub_FC79
		
; Вывод ошибка
Error:
		call	OutText
; ───────────────────────────────────────────────────────────────────────────
		db  03Fh, 0
; ───────────────────────────────────────────────────────────────────────────
		jmp		Prompt
		
; Директива O
CmdO:
		push	h
		mov		a, c
		ora		b
		jz		i_81
		push	h
		mov		l, c
		mov		h, b
		shld	word_F681
		pop		h
i_81:
		call 	mCRSbl
;		dw 	0F82Ah			; Контрольная сумма блока
		pop	 	h
		call	sub_FC79
		xchg
		call	sub_FC79
		xchg
		push	h
		mov		h, b
		mov		l, c
		call	sub_FC79
		pop		h
		call 	mMGblO
;		dw 	0F827h			; Вывод блока на магнитофон
		ret
		
; С новой строки выводим H в 16 ??? и пробел
sub_FC79:
		push	b
		call	NewLine		; Перейти на новую строку
		mov		a, h
		call 	mOutHex
;		dw 	0F815h		; вывод в 16 виде
		mov		a, l
		call	sub_FB84
		call	Space		; sub_FB7B
		pop		b
		call 	mInKey		; Ввод с клавиатуры
;		dw 	0F81Bh
		cpi		3			; Проверка на CTRL + C
		jz		Error
		ret

OutText:
		pop		h
Txt1:
		mov		c, m
		call 	mOutDsp
;		dw 	0F809h		; Вывод на дисплей
		inx		h
		mov		a, m
		ora		a
		jnz		Txt1
		pchl				; Вывести текст на экран
;
TestROM:
;		mvi		a, 8
;		out		Tim2   			; 0D2h
;		out		Tim2   			; 0D2h
;		lxi		h, 0
;		mov		d, l
;		call	CrcROM		; Проверка микросхемы D28
;		inr		a
;		out		SysPrtCtl   	; 0C3h
;		call	CrcROM		; Проверка микросхемы D29
;		mvi		a, 2
;		out		SysPrtC   		; 0C2h
;		call	CrcROM		; Проверка микросхемы D30
;		out		SysPrtC   		; 0C2h
;		mov		a, l
;		cmp		h
;		nop
;		rz					; Ошибок нет
;		mvi		a, 0h71 
;		out		Tim2   			; 0D2h	Выдаем звук ошибки
;		mvi		a, 2
;		out		Tim2   			; 0D2h
;		mvi		a, 0h12
;		out		Tim1   			; 0D1h
;		mvi		a, 0h7A 
;		out		Tim1   			; 0D1h
;		call	OutText		; Выводим сообщение об ошибке
;		DB		 "pzu neisprawno",0
		jmp		KeyRelease		; ожидание нажатие клавиши

;CrcROM:	
;		lxi		b, Mon
;c_1:
;		ldax	b
;		mov		e, a
;		dad		d
;		inx		b
;		mov		a, c
;		ora		b
;		jnz		c_1
;		ret
		
; $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
; $               Перенесено из DD30 					   $
; $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

; Вывод пробела
ExtFC00:
		push	d
		push	h
		push	h
		lhld	word_F6D9
		xchg
		mvi		h, 0
		mov		l, a
		inx		h
		dad		h
		dad		h
		dad		h
		mov		c, l
		mov		b, h
		lhld	word_F600
		dad		b
loc_FC14:
		dcx		h
		mov		a, m
		jmp		unk_F66C
;
;
;
sub_FC19:
		rrc					; FC19h
		rrc
		rrc
		rrc
		rrc
		rrc
		xthl
		mov		c, a
		mov		b, a
		in		SysPrtC     ;
		ani		4			; Проверяем цветной/монохромный
		jnz		i_91		; Цветной
		mov		a, b		; Монохромный
		ani		0Fh
		mov		c, a
		rlc
		rlc
		rlc
		rlc
		ora		c
		mov		c, a
		mov		a, b
		ani		0F0h
		mov		b, a
		rlc
		rlc
		rlc
		rlc
		ora		b
		mov		b, a
i_91:						; Цветной
		lda		byte_F669
		ana		e
		ana		c
		mov		c, a
		lda		byte_F669
		ana		d
		ana		b
		mov		b, a
		lda		Conf		; Конфигурация
		rlc
		jc		loc_FC6A	; Режим 1 и 3
		mov		a, e		; режим 2
		cma
		ana		m
		ora		c
		mov		m, a
		inx		h
		mov		a, d
		cma
		ana		m
loc_FC59:
		xra		b
		mov		m, a
		lxi		b, 0FFBFh	; Не адрес переменная
		dad		b
		xthl
		mov		a, l
		ani		7
		jnz		loc_FC14
		pop		h
		pop		h
		pop		d
		ret
; 
; Режим 1 и 3
;
loc_FC6A:
		mov		a, m
		xra		c
		mov		m, a
		inx		h
		mov		a, m
		jmp		loc_FC59
;
; Ввод с клавиатуры
;
ExtFC72:  					;
		push	h
		lxi		h, 0F6D6h
		mvi		a, 0FEh
i_101:							; loc_FC78:
		out		SysPrtA
		in		SysPrtB      ; 0C1h
		cmp		m
		jnz		loc_FCBB
		dcr		l
		in		SysPrtC      ; 0C2h
		rlc
		ori		1Fh
		cmp		m
		jnz		loc_FD6E
		in		SysPrtA      ; 0C0h
		dcr		l
		rlc
		jc		i_101			; loc_FC78
loc_FC91:
		lda		byte_F67D
		ora		a
		jm		loc_FCB9
		cpi		60h
		jc		loc_FCA2
		cpi		69h
		jc		loc_FCB9
loc_FCA2:
		lhld	word_F6DE
		dcx		h
		mov		a, l
		ora		h
		jnz		loc_FCB3
		lxi		h, 078h
		mvi		a, 0FFh
		sta		FlagKey
loc_FCB3:
		shld	word_F6DE
		lda		byte_F67D
loc_FCB9:
		pop		h
		ret
; 
loc_FCBB:
		push	b
		mvi		b, 4
		mov		c, a
loc_FCBF:
		in		SysPrtB      ; 0C1h
		cmp		c
		jnz		loc_FD82
		dcr		b
		jnz		loc_FCBF
loc_FCC9:
		lxi		b, 0
		xra		m
loc_FCCD:
		inr		c
		rlc
		jnc		loc_FCCD
		mov		a, b
		mov		b, c
loc_FCD4:
		rar
		dcr		c
		jnz		loc_FCD4
		mov		c, a
		xra		m
		mov		m, a
		ana		c
		push	psw
		dcr		b
		mov		a, l
		ani		0Fh
		mov		l, a
		mov		a, b
		rlc
		rlc
		rlc
		rlc
		ora		l
		rar
		jnc		loc_FCEF
		adi		040h
loc_FCEF:
		lxi		h, word_F610
		add		l
		mov		l, a
		jnc		loc_FCF8
		inr		h
loc_FCF8:
		lda		word_F678 + 1
		mov		b, a
		mov		a, m
		mov		c, a
		lhld	word_F67A
		cpi		063h
		jnz		loc_FD0A
		mov		a, b
		xri		0E0h
		mov		b, a
loc_FD0A:
		cpi		060h
		jnz		loc_FD17
		mov		a, l
		xri		010h
		mov		l, a
		mov		a, h
		xri		020h
		mov		h, a
loc_FD17:
		pop		psw
		mov		a, c
		jz		loc_FD1E
		ori		080h
loc_FD1E:
		mov		c, a
		ora		a
		sta		byte_F67D
		jm		loc_FD4C
		cpi		060h
		jc		loc_FD5F
		cpi		06Bh
		jnc		loc_FD5F
		cpi		061h
		jnz		loc_FD37
		mvi		h, 020h
loc_FD37:
		cpi		064h
		jnz		loc_FD3E
		mvi		h, 0
loc_FD3E:
		cpi		062h
		jnz		loc_FD47
		mov		a, l
		xri		010h
		mov		l, a
loc_FD47:
		cpi		065h
		cnc		unk_F609
loc_FD4C:
		shld	word_F67A
		mov		a, b
		sta		word_F678 + 1
		mov		a, h
		rlc
		rlc
		rlc
		mvi		a, 3
		ral
;
; Вывод на дисплей символа
;
ExtFD5A:
		out		SysPrtCtl       ; Включаем страницу ??
		jmp		DspChar			;

; ───────────────────────────────────────────────────────────────────────────
;
;

loc_FD5F:
		lxi		h, 0400h
		shld	word_F6DE
		mvi		a, 0FFh
		sta		FlagKey
DspChar:					;
		mov		a, c		; Символ для вывода
		pop		b			; восстановливаем регистры
		pop		h
		ret
; 
;
;
loc_FD6E:
		push	b
		mvi		b, 4
		mov		c, a
loc_FD72:
		in		SysPrtC      ; 0C2h
		rlc
		ori		01Fh
		cmp		c
		jnz		loc_FD82
		dcr		b
		jnz		loc_FD72
		jmp		loc_FCC9
; 
loc_FD82:
		pop		b
		jmp		loc_FC91
;
;  Вывод графический
;
ExtFD86:					;
		lhld	word_F600	; стоит E800 знакогенератор
		lxi		b, 0x9E00	; Адрес в памяти для формирования
i_111:						; новый адрес E800
;		mov		a, b
;		rrc
;		add		a
;		mov		d, a		; Получим тот же адрес
		mov		a, c		; Выделение 8 бит
		rar
		rar
		rar
		mov		e, a		; Будет записан каждый 8 байт
;		mov		a, d		;
;		ral
;		ori		0F8h		; получим адрес F8 при старом расположении
							; и при новом расположении получим FC что не правильно
;		mov		d, a		; Получим FС00 так что писать будем неправильно
		mov		a, m		; Читаем знакогенератор
		stax	d			; Пишем данные до
		inx		h
		inx		b
		mov		a, b
		cpi		0A2h		; адреса FC
		jnz		i_111
		ret
;
; Вывод на дисплей в символьном режиме
;
ExtFDA5:					;
		lxi		h, Sub_FE5F
		push	h			; Для возврата
		lhld	word_F66A	; Адрес буфера экрана
		mov		e, m		;
		inx		h
		mov		d, m
		lhld	XYCur		; Адрес курсора
		xchg				; Адрес курсора в DE
		lda		byte_F67E	; Флаг для ESC
		dcr		a
		jm		Ds_3		; 0
		jz		loc_FE45	; 1
		jpo		loc_FE4D	; 2 и более
		mov		a, c		; символ для вывода
		sui		020h
		mov		c, a
Ds_1:						;loc_FDC4:
		dcr		c
		jm		Ds_2		;loc_FDD0	; Выводить пока с != 0
		push	b
		call	sub_FE1A
		pop		b
		jmp		Ds_1		;loc_FDC4
; 
Ds_2:						;loc_FDD0:
		xra		a
loc_FDD1:
		sta		byte_F67E
		ret
		
; 
Ds_3:						;loc_FDD5:
		mov		a, c
		ani		07Fh
		cpi		01Fh			; Забой
		jz		loc_FE79
		cpi		0Ch				; В начало экрана
		jz		sub_FE91
		cpi		0Dh				; ВК
		jz		sub_FEC6
		cpi		0Ah				; ПС
		jz		loc_FE23
		cpi		8				; влево
		jz		loc_FEA9
		cpi		018h			; вправо
		jz		sub_FE1A
		cpi		019h			; Вверх
		jz		loc_FEB5
		cpi		01Ah			; Вниз
		jz		sub_FE98
		cpi		01Bh			; ESC
		jz		loc_FE74
		cpi		7				; Bell
		jnz		loc_FE19
;
; Выдает звуковой сигнал нажатия клавиши
;
ExtFE0A:
		xra		a
		out		Tim1      ; 0D1h
		mvi		a, 0Ah
		out		Tim1      ; 0D1h
		xra		a
		out		Tim2      ; 0D2h
		mvi		a, 4
		out		Tim2      ; 0D2h
		ret
; 
;Звуковой сигнал по коду 07
;
loc_FE19:
		mov		m, a
sub_FE1A:
		mov		a, e
		inx		h
		inr		e
		cpi		047h
		rnz
		call	sub_FEC6
loc_FE23:
		mov		a, d
		cpi		01Bh
		jnz		sub_FE98
		push	h
		push	d
		lhld	word_F6DC	; Начало текущего буфера экрана
		push	h
		lxi		b, 04Eh
		dad		b
		xchg
		pop		h
		lxi		b, 079Eh
loc_FE38:
		ldax	d
		mov		m, a
		inx		h
		inx		d
		dcx		b
		mov		a, c
		ora		b
		jnz		loc_FE38
		pop		d
		pop		h
		ret

;
;
;
loc_FE45:
		call	sub_FE91
		mvi		a, 2
		jmp		loc_FDD1
; 
;
;
loc_FE4D:
		mov		a, c
		sui		020h
		mov		c, a
loc_FE51:
		dcr		c
		mvi		a, 4
		jm		loc_FDD1
		push	b
		call	sub_FE98
		pop		b
		jmp		loc_FE51
; 
; Установить позицию курсора по HL
;
Sub_FE5F:
		xchg				; FE5Fh
		mvi		a, 080h
		out		BB75Comm    ; Команда позиция курсора
		mov		a, l
		out		BB75Dat     ;
		mov		a, h
		out		BB75Dat     ;
		shld	XYCur		; Сохранить
		lhld	word_F66A	; Сохранить регистр DE
		mov		m, e
		inx		h
		mov		m, d
		ret

; 
loc_FE74:
		mvi		a, 1
		jmp		loc_FDD1

; 
loc_FE79:
		lhld	word_F6DC	; Начало текущего буфера экрана
		lxi		d, 0832h
		dad		d
		lxi		d, 0925h
loc_FE83:
		xra		a
		mov		m, a
		dcx		h
		dcx		d
		mov		a, e
		ora		d
		jnz		loc_FE83
		mvi		m, 09Dh
		dcx		h
		mvi		m, 0F3h

sub_FE91:
		lxi		d, 0308h
		lhld	word_F6DC	; Начало текущего буфера экрана
		ret

sub_FE98:
		mov		a, d
		cpi		1Bh
		lxi		b, 04Eh
		jnz		loc_FEA6
		mvi		d, 2
		lxi		b, 0F8B0h
loc_FEA6:
		inr		d
		dad		b
		ret
loc_FEA9:
		mov		a, e
		dcx		h
		dcr		e
		cpi		8
		rnz
		mvi		e, 047h
		lxi		b, 040h
		dad		b
loc_FEB5:
		mov		a, d
		cpi		3
		lxi		b, 0FFB2h
		jnz		loc_FEC3
		mvi		d, 01Ch
		lxi		b, 0750
loc_FEC3:
		dcr		d
		dad		b
		ret

sub_FEC6:
		mov		a, l
		sub		e
		jnc		i_211			; loc_FECC
		dcr		h
i_211:							; loc_FECC:
		mov		l, a
		mvi		e, 8
		lxi		b, 8
		dad		b
		ret
; 
; Настройка дисплея
; Переписать для 2ВГ75
; Эта программа устанавливает адрес ОЗУ 09000H
;
ExtFED4:					; Настройка дисплея
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

; Устанавливаем курсор
		mvi		a, 080h 	; Команда загрузить курсор
		out		BB75Comm    ;
		dcr		a			; Позиция курсора
		out		BB75Dat     ; 79h
		out		BB75Dat     ; 79h

; В области ОЗУ формируем команды
		lxi		d, 0A200h	; Начало области ОЗУ
		mvi		a, 0F1h		; Конец знакоряда - прекращение ПДП
		stax	d
		inx		d
		stax	d
		inx		d
		stax	d
		inx		d
		stax	d			; 4 байта F1h
		mvi		a, 7
i_121:							; loc_FF18:
		push	psw
		mvi		b, 040h		; байт в строке
		call	sub_FF64	; Сформировать строку
		mvi		b, 0
		call	sub_FF64	; Сформировать строку
		pop		psw
		dcr		a
		jnz		i_121		; записываем 7 строк
		lda		Conf		; Конфигурация
		mov		c, a		; Сохранить
		rrc
		rrc
		mvi		a, 2		; страница
		ral
		out		SysPrtCtl   ; Переключить на 1
		mov		a, c		; Восстановить
		ani		010h		; Выделить 2 бит в конфигурации
		
; Настройка фонта		
ExtFF36:
		lxi		h, 0A600h	; Начало основного буфера экрана
		lxi		b, Tbl5		; Начало данных
		jz		i_122		; 2 бит не установлен основной экран
		lxi		h, 8400h	; Начало дополнительного буфера экрана
		lxi		b, Tbl6		; Начало данных
i_122:						;
		shld	word_F6DC	; Начало текущего буфера экрана
		lxi		h, 0E904h	; Видеоозу
		lxi		d, 046h 	; Количество
		ldax	b			; читать данные из таблицы
		mov		m, a		; Сохранить в ОЗУ знакогенератора (F800 только запись)
;		jmp		loc_FF5B
		inx 	b
i_123:						; loc_FF53:
		ldax	b
		ora		a			; Проверяем на конец таблицы
		jz		i_124		; loc_FF5F
		dad		d			; Новый адрес + 70 байт
		mov		m, a		; Записать данные
		dad		d			; Прибавить смещение + 70 байт
							;loc_FF5B:
		inx		b			; Следующий байт таблицы
		jmp		i_123		; Повторить
i_124:						; loc_FF5F:
		dcx		h
		dcx		h			; Уменьшить адрес на 2
		mvi		m, 0F3h		; ЗаписатьКонец кадра - прекращение ПДП
		ret
;
;Формирует строку с байтами в В сначала
;
sub_FF64:
		lxi		h, 0
		dad		sp			; HL равен стэку
		shld	TmpStk		; Временно  сохраняем стэк
		inx		d			; Адрес куда записываем
		mov		a, b		; Байт для записи
		stax	d
		inx		d
		stax	d
		inx		d
		stax	d			; 3 байта из B
		mvi		a, 03Eh 	; Длина строки
i_131:						; loc_FF74:
		pop		h			; 7 со столбца 7 выводим
		inx		d
		ora		b
		stax	d
		inr		a
		ani		03Fh		; Проверка на конец строки
		cpi		03Eh
		jnz		i_131		; loc_FF74
		inx		d
		ora		b
		stax	d
		inx		d
		mvi		a, 0F1h		; Конец знакоряда - прекращение ПДП
		stax	d
		inx		d
		stax	d
		lhld	TmpStk		; Возвращаем стэк на место
		sphl
		ret
		
; Программа перемещения фонта
ExtFF8E:
		lxi		b, 0400h	; Размер перемещаемой области
; Программа перемещения	области	памяти
; DE откуда, HL	куда и BC сколько
Move:
		ldax	d		
		mov		m, a
		inx		h
		inx		d
		dcx		b
		mov		a, b
		ora		c
		jnz		Move
		ret

; FF9Ch Основной буфер
Tbl5:	db  8Dh, 90h, 94h, 98h, 9Ch, 91h, 95h, 099h, 0

; FFA5h Альтернативный буфер
Tbl6:	db  80h, 84h, 88h, 8Ch, 81h, 85h, 89h, 8Dh, 0

;*************************************************************************		
		DEFM "Юрий  24-01-2024"
;	.org 	FE95h
wwww:
	rept 0x800 - ASMPC -2
		db	0x00
	endr
		db 0F0h,0
		ASSERT	ASMPC == 0x800
