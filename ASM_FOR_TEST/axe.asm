;this is a sample cold start loader, which, when 
;modified
;resides on track 00, sector 01 (the first sector on the 
;diskette), we assume that the controller has loaded 
;this sector into memory upon system start-up (this 
;program can be keyed-in, or can exist in read-only 
;memory
;beyond the address space of the cp/m version you are 
;running). the cold start loader brings the cp/m system 
;into memory at"loadp" (3400h +"bias"). in a 20k 
;memory system, the value of"bias" is 000h, with 
;large
;values for increased memory sizes (see section 2). 
;after
;loading the cp/m system, the cold start loader 
;branches
;to the "boot" entry point of the bios, which begins at
; "bios" +"bias". the cold start loader is not used un-
;til the system is powered up again, as long as the bios 
;is not overwritten. the origin is assumed at 0000h, and 
;must be changed if the controller brings the cold start 
;loader into another area, or if a read-only memory 
;area
;is used.
	org	0		;base of ram in
				;cp/m
msize	equ	20		;min mem size in
				;kbytes
bias	equ	(msize-20)*1024	;offset from 20k
				;system
ccp	equ	3400h+bias	;base of the ccp
bios	equ	ccp+1600h	;base of the bios
biosl	equ	0300h		;length of the bios
boot	equ	bios
size	equ	bios+biosl-ccp	;size of cp/m
				;system
sects	equ	size/128	;# of sectors to load
;
;	begin the load operation 

cold:
	lxi	b,2		;b=0, c=sector 2
	mvi	d,sects		;d=# sectors to
				;load
	lxi	h,ccp		;base transfer
				;address
lsect:	;load the next sector

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
	jmp	past$patch	;remove this
				;when patched
	ds	60h

past$patch:
;go to next sector if load is incomplete
	dcr	d		;sects=sects-1
	jz	boot		;head. for the bios

;	more sectors to load
;

;we aren't using a stack, so use <sp> as scratch
;register
;	to hold the load address increment
	lxi	sp,128		;128 bytes per
				;sector
	dad	sp		;<hl> = <hl> + 128
	inr	c		;sector=sector + 1
	mov	a,c
	cpi	27		;last sector of
				;track?
	jc	lsect		;no, go read
				;another

;end of track, increment to next track

	mvi	c,1		;sector = 1
	inr	b		;track = track + 1
	jmp	lsect		;for another group
	end			;of boot loader
