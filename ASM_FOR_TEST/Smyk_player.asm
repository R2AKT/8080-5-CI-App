#target rom
#charset ascii
.asm8080

#include "definition.inc"

Smyk_Clk		EQU		1000000		; 8253 CLK
;;
;//
;typedef struct {
;	uint16_t Ch0_tone[Ch_len];
;	uint16_t Ch0_duration[Ch_len];
;	uint16_t Ch1_tone[Ch_len];
;	uint16_t Ch1_duration[Ch_len];
;	uint16_t Ch2_tone[Ch_len];
;	uint16_t Ch2_duration[Ch_len];
;} CHANNEL_DATA;
;//
;typedef struct {
;	uint8_t Ch_mask;
;	uint16_t Ch_clock;
;	uint16_t Ch_len;
;	string Description[];
;} SETUP;
;//
;typedef struct {
;	SETUP SmykSetup;
;	CHANNEL_DATA SmykData;
;} SMYK;
;//
;;

#code CODE, 0000h
		CALL	Smyk_Init


		HLT
;;
;
#include "Smyk.asm"