; Адреса ввода/вывода для КР04-85

; Основной ППА ВВ55  				0C0h-0C3h
SysPrtA		equ	0C0h	; Порт А
SysPrtB		equ	0C1h	; Порт В
SysPrtC		equ	0C2h	; Порт С
SysPrtCtl	equ	0C3h	; Порт управления

; Таймер ВИ53  					0D0h-0D3h
Tim0		equ	0D0h	;Счетчик 1
Tim1		equ	0D1h	;Счетчик 2
Tim2		equ	0D2h	;Счетчик 3
TimC    	equ	0D3h	;Регистр управления таймером

; Контроллер ЭЛТ ВГ75  			0E4h-0E5h
BB75Dat	    equ    0E4h	; Запись данных
BB75Stat	equ    0E5h	; Чтение состояния
BB75Comm	equ	   0E5h	; Запись команды

; Контроллер ПДП ВТ57  			0F0h-0F8h
DmaAdr0	equ	0F0h	; Адрес канала 0
DmaCkl0	equ	0F1h	; Количество циклов канала 0
DmaAdr1	equ	0F2h	; Адрес канала 1
DmaCkl1	equ	0F3h	; Количество циклов канала 1
DmaAdr2	equ	0F4h	; Адрес еанала 2
DmaCkl2	equ	0F5h	; Количество циклов канала 2
DmaAdr3	equ	0F6h	; Адрес еанала 3
DmaCkl3	equ	0F7h	; Количество циклов канала 3
DmaCtrl	equ 0F8h	; Устанока режимов только запись
DmaStat	equ	0F8h	; Состояние только чтение

; ППА блока цветности 			00h-03h
ColPrtA		equ	00	; Порт А
ColPrtB		equ	01	; Порт В
ColPrtC		equ	02	; Порт С
ColPrtCtl	equ	03	; Порт управления

; ППА ROM-диска/SD-контроллера	10h-13h
RomPrtA		equ	010h	; Порт А
RomPrtB		equ	011h	; Порт В
RomPrtC		equ	012h	; Порт С
RomPrtCtl	equ	013h	; Порт управления
SDcrdD		equ 010h	; Работа с SD данные
SDcrdK		equ 011h	; Работа с SD управление

; Контроллер ГМД					20h-2Fh
FDC_BASE	equ	020h
REG_DOR		equ FDC_BASE+0x02      ; цифровой выходной регистр
REG_MSR		equ FDC_BASE+0x04      ; адрес регистра основного статуса
REG_DSR		equ FDC_BASE+0x04      ; адрес регистра скорости передачи данных
REG_DATA	equ	FDC_BASE+0x05      ; регистр данных
REG_CCR		equ	FDC_BASE+0x07      ; регистр управления конфигурацией

; Программатор ПЗУ				30h-33h
PrgPrtA		equ	030h	; Порт А
PrgPrtB		equ	031h	; Порт В
PrgPrtC		equ	032h	; Порт С
PrgPrtCtl	equ	033h	; Порт управления

; Последовательный интерфейс		40h-41h
BB51Dat	   equ	    040h	; Порт данных
BB51Ctr	   equ	    041h	; Порт управления

; Параллельный интерфейс			50h-53h
PriPrtA		equ	050h	; Порт А
PriPrtB		equ	051h	; Порт В
PriPrtC		equ	052h	; Порт С
PriPrtCtl	equ	053h	; Порт управления

; Резерв							80р-BFh

; Порт C:
; 0-1	выбор карты распределения памяти, output
; 2		выбор черно-белого режима, output
; 3		вывод на магнитофон, output
; 4-6	матрица клавиатуры, input
; 7		ввод с магнитофона, input
