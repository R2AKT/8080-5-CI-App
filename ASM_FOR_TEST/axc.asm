;		combined getsys and putsys programs from
;		Sec 6.4
;
;	Start the programs at the base of the TPA
	org 0100h

msize	equ 20			;size of cp/m in Kbytes

;"bias" is the amount to add to addresses for > 20K
;	(referred to as"b" throughout the text)
bias	equ	(msize-20)*1024
ccp	equ	3400h+bias
bdos	equ	ccp+0800h
bios	equ	ccp+1600h

;	getsys programs tracks 0 and 1 to memory at 3880h + bias
;	register	     usage
;	a		(scratch register)
;	b		track count (0...76)
;	c		sector count (1...26)
;	d,e		(scratch register pair)
;	h,l		load address
;	sp		set to track address

gstart:	;start of getsys
	lxi	sp,ccp-0080h	;convenient place
	lxi	h,ccp-0080h	;set initial load
	mvi	b,0		;start with track
rd$trk:	;read next track
	mvi	c,1		;each track start
rd$sec:
	call	read$sec	;get the next sector
	lxi	d,128		;offset by one sector
	dad	d		; (hl=hl+128)
	inr	c		;next sector
	mov	a,c		;fetch sector number
	cpi	27		;and see if last
	jc	rdsec		;<, do one more

;arrive here at end of track, move to next track

	inr	b		;track = track+1
	mov	a,b		;check for last
	cpi	2		;track = 2 ?
	jc	rd$trk		;<, do another

;arrive here at end of load, halt for lack of anything 
;better

	ei
	hlt

;	putsys program, places memory image
;	starting at
;	3880h + bias back to tracks 0 and 1
;	start this program at the next page boundary
	org ($+0100h) and 0ff00h
put$sys:
	lxi 	sp,ccp-0080h 	;convenient place
	lxi 	h,ccp-0080h 	;start of dump
	mvi 	b,0 		;start with track
wr$trk:
	mvi 	b,l 		;start with sector
wr$sec:
	call	write$sec	;write one sector
	lxi 	d,128 		;length of each
	dad	d		;<hl>=<hl> + 128
	inr	c		; <c>=<c> + 1
	mov	a,c		;see if
	cpi 	27 		;past end of track
	jc  	wr$sec  	;no, do another

;arrive here at end of track, move to next track

	inr	b		;track = track+1
	mov	a,b		;see if
	cpi	2		;last track
	jc	wr$trk		;no, do another


;	done with putsys, halt for lack of anything
;	better
	ei
	hlt


;user supplied subroutines for sector read and write

;	move to next page boundary
	org ($+0100h) and 0ff00h

read$sec:
	;read the next sector 
	;track in <b>, 
	;sector in <c> 
	;dmaaddr in<hl>

	push	b
	push	h

;user defined read operation goes here
	ds	64
	pop	h
	pop	b
	ret

	org ($+100h) and 0ff00h ;another page 
				; boundary
write$sec:

	;same parameters as read$sec

	push 	b
	push	h

;user defined write operation goes here
	ds	64
	pop	h
	pop	b
	ret

;end of getsys/putsys program

	end
