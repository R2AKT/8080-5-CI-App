;;
; Definitions
ROM0			EQU		0F800h			; ROM0 range 0000h - 07FF (2048b = 2k = 800h), relocated to F800h - FFFFh
ROM1			EQU		0E800h			; ROM1 range 0800h - 17FF (4096b = 4k = 1000h), relocated to E800h - F7FFh
ROM2			EQU		01800h			; ROM2 range 1800h - 19FF (2048b = 2k = 800h), relocated to E000h - E7FFh

;;
;
RAM_BUF			EQU		0081h			; Buffer RAM range 0081h - 01FFh
RAM_0			EQU		0200h			; RAM range 0200h - 1FFFh
RAM_Banked		EQU		2000h			; Banked RAM range 2000h - 5FFFh
RAM_TOP 		EQU		8000h			; TOP RAM range 8000h - FFFFh
SP_TOP			EQU		ROM2			; Stack pointer top = start ROM2

; ;;
; ; RST0-RST7 address table (Internal interrupt vector table (8080))
; RST0Addr		EQU		ROM0+0000h
; RST1Addr		EQU		ROM0+0008h
; RST2Addr		EQU		ROM0+0010h
; RST3Addr		EQU		ROM0+0018h
; RST4Addr		EQU		ROM0+0020h
; RST5Addr		EQU		ROM0+0028h
; RST6Addr		EQU		ROM0+0030h
; RST7Addr		EQU		ROM0+0038h

;;
;
ExtVecTable0	EQU		ROM0+0040h		; External interrupt vector table (8259 - IRQ0-IRQ6)
ExtVecTable1	EQU		ROM0+0060h		; External interrupt vector table (8259 - IRQ7-IRQ14)

;;
;
MainStart  		EQU 	ROM0+0080h		; Main Code section
InitCode   		EQU 	ROM0+0200h		; Initialize Subroutines
LibCode			EQU		ROM0+0300h		; Library section
