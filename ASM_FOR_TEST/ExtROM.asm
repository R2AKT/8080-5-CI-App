#target rom
#charset ascii
.asm8080
SectorSize		EQU		0x200	; Sector size

BootOffset		EQU		0x0800 	; 0x0800 - 2k, 0x1000 - 4k, 0x2000 - 8k

Boot_Start		EQU		0x0		; Base address boot code
Boot_Size		EQU		0x1B8	; Boot code size

ID_Start		EQU		0x1B8

Partition_Start	EQU		0x1BE	; Base address partition table
Partition_Size	EQU		0x40	; Partition table size

Sing_Start		EQU		0x1FE

;;
;
#code MBR_Boot, Boot_Start+BootOffset, Boot_Size
;	CALL		GetPC			; HL - new pointer to 'LABEL'
;LABEL:
;	LXI			D,LABEL			; DE - old pointer to 'LABEL'
;	;
;	MOV			A,L
;	SUB			E
;	MOV			C,A
;	MOV			A,H
;	SBB			D
;	MOV			B,A				; BC - offset from old to new pointer to 'LABEL' (-!!!- HL >= DE -!!!-)
;	;
;	DB			0x55,0xAA,0x00,0xFF
;;
	DW			MBR_Boot
	JMP			MBR_Boot+16
;;
#include "GetPC.asm"
#include "SW_IO.asm"
;;
	LXI			H,MBR_Sign+BootOffset
;;
; Allocate 512 byte in stack memory
	LXI			D,SectorSize	; Load to DE sector size (512 byte)
	LXI			H,00h			; Load to HL 0x0000
	DAD			SP				; HL = HL + SP
	MOV			A,L				; Copy L to A
	SUB			E				; A = A - E
	MOV			L,A				; Copy A to L
	MOV			A,H				; Copy H to A
	SBB			D				; A = A - D+carry
	MOV			H,A				; Copy A to H
	SPHL						; Copy HL to SP
;
	PUSH		H				; Store HL (SP) to stack
;

;;
; Remove allocated 512 byte in stack memory
	LXI			H,SectorSize	; Load to HL sector size (512 byte)
	DAD			SP				; HL = HL + SP
	SPHL						; Copy HL to SP
;;
;
#code MBR_ID, ID_Start, *
	DW		0x55C0, 0xFF00, 0xC0AA

;;
;
#code MBR_Partition, Partition_Start, Partition_Size
;;
; Partition 0 table
	DB		0x80			; 0x80 - bootable (selected), 0x00 - not bootable (not selected)
	DB		0x00			; Head (Start)
	DB		0x02			; Sector (Start)
	DB		0x00			; Cylinder (Start)
	DB		0xCD			; FS type:
							; 0x00 - blank,
							; 0x7F - research or education,
							; 0xA5 - hibernation,
							; 0xCD - memory dump,
							; 0xDA - data (not FS),
							; 0xDD - hide memory dump.
	DB		0x00			; Head (End)
	DB		0x1F			; Sector (End)
	DB		0x00			; Cylinder (End)	
	DW		0x0000, 0x0000	; LBA partition start
	DW		0x0000, 0x001F	; LBA partition size

;;
; Partition 1 table
	DB		0x00			; 0x80 - bootable (selected), 0x00 - not bootable (not selected)
	DB		0x00			; Head (Start)
	DB		0x20			; Sector (Start)
	DB		0x00			; Cylinder (Start)
	DB		0xCD			; FS type:
							; 0x00 - blank,
							; 0x7F - research or education,
							; 0xA5 - hibernation,
							; 0xCD - memory dump,
							; 0xDA - data (not FS),
							; 0xDD - hide memory dump.
	DB		0x00			; Head (End)
	DB		0x3F			; Sector (End)
	DB		0x00			; Cylinder (End)	
	DW		0x0000, 0x0000	; LBA partition start
	DW		0x0000, 0x0020	; LBA partition size

;;
; Partition 2 table
	DB		0x00			; 0x80 - bootable (selected), 0x00 - not bootable (not selected)
	DB		0x00			; Head (Start)
	DB		0x00			; Sector (Start)
	DB		0x01			; Cylinder (Start)
	DB		0x7F			; FS type:
							; 0x00 - blank,
							; 0x7F - research or education,
							; 0xA5 - hibernation,
							; 0xCD - memory dump,
							; 0xDA - data (not FS),
							; 0xDD - hide memory dump.
	DB		0x00			; Head (End)
	DB		0x1F			; Sector (End)
	DB		0x01			; Cylinder (End)	
	DW		0x0000, 0x0000	; LBA partition start
	DW		0x0000, 0x0020	; LBA partition size

;;
; Partition 3 table
	DB		0x00			; 0x80 - bootable (selected), 0x00 - not bootable (not selected)
	DB		0x00			; Head (Start)
	DB		0x20			; Sector (Start)
	DB		0x01			; Cylinder (Start)
	DB		0x7F			; FS type:
							; 0x00 - blank,
							; 0x7F - research or education,
							; 0xA5 - hibernation,
							; 0xCD - memory dump,
							; 0xDA - data (not FS),
							; 0xDD - hide memory dump.
	DB		0x00			; Head (End)
	DB		0x3F			; Sector (End)
	DB		0x01			; Cylinder (End)	
	DW		0x0000, 0x0000	; LBA partition start
	DW		0x0000, 0x0020	; LBA partition size

;;
;
#code MBR_Sign, Sing_Start, *
	DW		0xAA55

;;
;	
#code Data_P0, *, (16384 - (MBR_Boot_Size + MBR_ID_Size + MBR_Partition_Size + MBR_Sign_Size))
Address_P0:			DW		0x4000			; DUMP load start address
Size_P0:			DW		Data_P0_Size	; DUMP size
	DM				'-!!!- Partition 0 data (BIOS DUMP) -!!!-'

#code Data_P1, *, 16384
Address_P1:			DW		0x8000			; DUMP load start address
Size_P1:			DW		Data_P1_Size	; DUMP size
	DM				'-!!!- Partition 1 data (LIB DUMP) -!!!-'

#code Data_P2, *, 16384
SectorCount_P2:		DW		(Data_P2_Size/SectorSize)
Name_P2:			DM		'DATA'
 
	DM		'-!!!- Partition 2 data -!!!-'

#code Data_P3, *, 16384
SectorCount_P3:		DW		(Data_P3_Size/SectorSize)
Name_P3:			DM		'USER'
 
	DM		'-!!!- Partition 3 data -!!!-'

.end
