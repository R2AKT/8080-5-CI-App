;;;
;	Cold Start Loader
;;;
;this is a sample cold start loader, which, when modified
;resides on track 00, sector 01 (the first sector on the 
;diskette), we assume that the controller has loaded 
;this sector into memory upon system start-up (this 
;program can be keyed-in, or can exist in read-only memory
;beyond the address space of the cp/m version you are 
;running). the cold start loader brings the cp/m system 
;into memory at"loadp" (3400h +"bias"). in a 20k 
;memory system, the value of"bias" is 000h, with large
;values for increased memory sizes (see section 2). 
;after loading the cp/m system, the cold start loader branches
;to the "boot" entry point of the bios, which begins at
;"bios" +"bias". the cold start loader is not used until
;the system is powered up again, as long as the bios 
;is not overwritten. the origin is assumed at 0000h, and 
;must be changed if the controller brings the cold start 
;loader into another area, or if a read-only memory 
;area is used.

#target rom
#charset ascii
.asm8080

MSIZE		EQU		32				;min mem size in kbytes
BIAS		EQU		(MSIZE-20)*1024	;offset from 20k system
CCP			EQU		3400h+BIAS		;base of the ccp
BIOS		EQU		CCP+1600h		;base of the bios
BIOSL		EQU		0300h			;length of the bios
BOOT		EQU		BIOS
SIZE		EQU		BIOS+BIOSL-CCP	;size of cp/m system
SECTS		EQU		SIZE/128		;# of sectors to load

;;
;	begin the load operation
#code CODE, 0000h					;base of ram in cp/m

COLD:
	LXI		B,2						;b=0, c=sector 2
	MVI		D,SECTS					;d=# sectors to load
	LXI		H,CCP					;base transfer address
LSECT:	;load the next sector

;	insert inline code at this point to
;	read one 128 byte sector from the
;	track given in register b, sector
;	given in register c,
;	into the address given by <hl>
;branch	to location "cold" if a read error occurs
;
;
;
;
;	user supplied read operation goes
;	here...
;
;
;
;
	JMP		PAST_PATCH				;remove this when patched
	DS		60h

PAST_PATCH:
;go to next sector if load is incomplete
	DCR		D						;sects=sects-1
	JZ		BOOT					;head. for the bios

;	more sectors to load
;

;we aren't using a stack, so use <sp> as scratch
;register to hold the load address increment
	LXI		SP,128					;128 bytes per sector
	DAD		SP						;<hl> = <hl> + 128
	INR		C						;sector=sector + 1
	MOV		A,C
	CPI		27						;last sector of track?
	JC		LSECT					;no, go read another

;end of track, increment to next track

	MVI		C,1						;sector = 1
	INR		B						;track = track + 1
	JMP		LSECT					;for another group
	END								;of boot loader
