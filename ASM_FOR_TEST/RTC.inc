;;
; RTC RAM definition
RTC_Seconds			EQU		00h			;
RTC_Seconds_Alarm	EQU		01h			;
RTC_Minutes			EQU		02h			;
RTC_Minutes_Alarm	EQU		03h			;
RTC_Hours			EQU		04h			;
RTC_Hours_Alarm		EQU		05h			;
RTC_Week			EQU		06h			;
RTC_Day				EQU		07h			;
RTC_Month			EQU		08h			;
RTC_Year			EQU		09h			;
;
RTC_RegA			EQU		0Ah			;
RTC_RegB			EQU		0Bh			;
RTC_RegC			EQU		0Ch			; -!!!- READ ONLY -!!!-
RTC_RegD			EQU		0Dh			; -!!!- READ ONLY -!!!-
;
RTC_RegA_RS0		EQU		1
RTC_RegA_RS1		EQU		2
RTC_RegA_RS2		EQU		4
RTC_RegA_RS3		EQU		8
RTC_RegA_DV0		EQU		16
RTC_RegA_DV1		EQU		32
RTC_RegA_DV2		EQU		64
RTC_RegA_UIP		EQU		128
;
RTC_RegB_DSE		EQU		1			; Enable daylight saving
RTC_RegB_24hr		EQU		2			; RTC in 24 hour mode, overwise 12 hour
RTC_RegB_Binary		EQU		4			; RTC in binary mode, overwise BCD
RTC_RegB_SQWE		EQU		8			; Enable SQW output
RTC_RegB_UIE		EQU		16			; Enable update-end interrupt
RTC_RegB_AIE		EQU		32			; Enable alarm interrupt
RTC_RegB_PIE		EQU		64			; Enable periodic interrupt
RTC_RegB_SET		EQU		128			; Stop RTC
;
RTC_RegC_UF			EQU		16
RTC_RegC_AF			EQU		32
RTC_RegC_PF			EQU		64
RTC_RegC_IRQF		EQU		128
;
RTC_RegD_VRT		EQU		128
;
RTC_RAM_start		EQU		0Eh			; RTC RAM start address
RTC_RAM_end			EQU		3Fh			; RTC RAM end address
RTC_RAM_size		EQU		50			; RTC RAM size
