;;
; Definitions
ROM0			EQU		 0000h			; ROM0 range 0000h - 07FFh
ROM0_Size		EQU		 0800h			; ROM0 size 800h (2048b = 2k = 800h)
;
FLASH0			EQU		 0800h			; FLASH0 range 0800h - 0FFFh (2048b = 2k = 800h)
FLASH0_Size		EQU		 0800h			; FLASH0 size 800h (2048b = 2k = 800h)
;
RAM0			EQU		 1000h			; RAM1 range 1000h - 17FFh (2048b = 2k = 800h)
RAM0_Size		EQU		 0800h			; RAM1 size 800h (2048b = 2k = 800h)
;
RAM1			EQU		 1800h			; RAM2 range 1800h - 1FFFh (2048b = 2k = 800h)
RAM1_Size		EQU		 0800h			; RAM2 size 800h (2048b = 2k = 800h)
;
RAM_TOP 		EQU		RAM1+RAM1_Size-1; TOP RAM (1FFFh)
SP_TOP			EQU		RAM1+RAM1_Size	; Stack pointer = top RAM+1
;
BootStart		EQU		0080h			; Main boot
MainStart		EQU		FLASH0			; User programm 0800h - 0FFFh
IVTStart		EQU		BOOT_end+16		; Skeep 16 byte from main boot code
;
LibCode			EQU		ROM0+0200h		; Library section
;
MessageBlock	EQU		ROM0+0300h		; Message section
