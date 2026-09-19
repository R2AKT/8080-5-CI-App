; Standalone absolute image using M80 source facilities.
        .8080
        ASEG
        ORG 100H

PUTCHAR MACRO CHAR
        MVI A,CHAR
        OUT 1
        ENDM

DELAY   MACRO COUNT
        LOCAL AGAIN
        MVI B,COUNT
AGAIN:  DCR B
        JNZ AGAIN
        ENDM

START:  PUTCHAR 'H'
        PUTCHAR 'i'
        DELAY 10
        HLT

TABLE:  IRP VALUE,<1,2,3,4>
        DB VALUE*VALUE
        ENDM

        IF TABLE-START GT 0
MESSAGE: DC 'Ready'
        ENDIF
        END START
