        PAGE 0                ;SUPPRESS FF ADDED IN LIST FILE
;*************************************************************
;
;                 TINY BASIC FOR INTEL 8085
;                       VERSION 2.X
;                     BY LI-CHEN WANG
;                  MODIFIED AND TRANSLATED
;                    TO INTEL MNEMONICS
;                     BY ROGER RAUSKOLB
;                      10 OCTOBER,1976
;                        @COPYLEFT
;                   ALL WRONGS RESERVED
;              ADDITIONS BY ANDERS HJELM 2020
;
;*************************************************************
;
; *** 8085 ADDITIONAL INSTRUCTIONS ***
;
; UNDOCUMENTED INSTRUCTIONS FOR THE 8085 CPU SUPPLIED AS MACROS
;
DSUB    MACRO                 ;16-BIT SUBTRACT: HL = HL - BC
        DB    08H
        ENDM
;
ARHL    MACRO                 ;ARITHMETIC SHIFT RIGHT OF HL
        DB    10H
        ENDM
;
RDEL    MACRO                 ;ROTATE LEFT THROUGH CARRY OF DE
        DB    18H
        ENDM
;
LDHI    MACRO BARG1           ;LOAD DE WITH HL + IMMEDIATE BYTE
        DB    28H
        DB    BARG1
        ENDM
;
LDSI    MACRO BARG2           ;LOAD DE WITH SP + IMMEDIATE BYTE
        DB    38H
        DB    BARG2
        ENDM
;
RSTV    MACRO                 ;RESTART ON OVERFLOW ("CV 0040H")
        DB    0CBH
        ENDM
;
SHLX    MACRO                 ;STORE HL INDIRECT THROUGH (DE)
        DB    0D9H
        ENDM
;
LHLX    MACRO                 ;LOAD HL INDIRECT THROUGH (DE)
        DB    0EDH
        ENDM
;
JNK     MACRO WARG1           ;JUMP ON NOT K-FLAG
        DB    0DDH
        DB    (WARG1 & 0FFH)
        DB    (WARG1 >> 8)
        ENDM
;
JK      MACRO WARG2           ;JUMP ON K-FLAG
        DB    0FDH
        DB    (WARG2 & 0FFH)
        DB    (WARG2 >> 8)
        ENDM
;
; *** TABLE/ADDRESSING MACRO ***
;
; USING TWO BYTE ADDRESS WITH MOST SIGNIFICANT BIT SET TO 1
;
DWA     MACRO WHERE
        DB   (WHERE >> 8) + 128
        DB   WHERE & 0FFH
        ENDM
;
;*************************************************************
;
; *** ZERO PAGE SUBROUTINES ***
;
; THE 8080 INSTRUCTION SET LETS YOU HAVE 8 ROUTINES IN LOW
; MEMORY THAT MAY BE CALLED BY RST N, N BEING 0 THROUGH 7.
; THIS IS A ONE BYTE INSTRUCTION AND HAS THE SAME POWER AS
; THE THREE BYTE INSTRUCTION CALL LLHH.  TINY BASIC WILL
; USE RST 0 AS START AND RST 1 THROUGH RST 7 FOR
; THE SEVEN MOST FREQUENTLY USED SUBROUTINES.
; TWO OTHER SUBROUTINES (CRLF AND TSTNUM) ARE ALSO IN THIS
; SECTION.  THEY CAN BE REACHED ONLY BY 3-BYTE CALLS.
; BY USING RST CALLS, ROM CODE IS REDUCED BY ABOUT 200 BYTES.
;
        ORG  0H
START:  LXI  SP,STACK           ;*** COLD START ***
        MVI  A,80H
        JMP  INIT
;
TSTC:   XTHL                    ;*** TSTC OR RST 1 *** (24x)
        RST  5                  ;IGNORE BLANKS AND
        CMP  M                  ;TEST CHARACTER
        JMP  TC1                ;REST OF THIS IS AT TC1
;
CRLF:   MVI  A,CR               ;*** CRLF ***
;
OUTC:   PUSH PSW                ;*** OUTC OR RST 2 *** (22x)
        JMP  OC3                ;REST OF THIS IS AT OC3
;
RIMSK:  RIM                     ;*** READ INTERRUPT MASK ***
        MOV  L,A                ;PLACE RESULT IN L
        RET                     ;THAT'S ALL
        NOP                     ;DUMMY FILL BYTE
;
EXPR:   CALL EXPR0              ;*** EXPR OR RST 3 *** (11x)
        PUSH H                  ;EVALUATE AN EXPRESSION
        JMP  RELOP              ;REST OF IT AT RELOP
        DB   'W'
;
COMP:   MOV  A,H                ;*** COMP OR RST 4 *** (16x)
        CMP  D                  ;COMPARE HL WITH DE
        RNZ                     ;RETURN CORRECT C AND
        MOV  A,L                ;Z FLAGS
        CMP  E                  ;BUT OLD A IS LOST
        RET
        DB   "AN"
;
IGNBLK: LDAX D                  ;*** IGNBLK/RST 5 *** (7x)
        CPI  ' '                ;IGNORE BLANKS
        RNZ                     ;IN TEXT (WHERE DE->)
        INX  D                  ;AND RETURN THE FIRST
        JMP  IGNBLK             ;NON-BLANK CHAR. IN A
;
FINISH: POP  PSW                ;*** FINISH/RST 6 *** (16x)
        CALL FIN                ;CHECK END OF COMMAND
        CALL QWHAT              ;PRINT "WHAT?" IF WRONG
        DB   'G'
;
XPR40:  JMP  XP40               ;*** XP40 OR RST 7 *** (24x)
        NOP                     ;DUMMY FILL BYTE
;
TIMINT: DI                      ;*** TIMER/RST 7.5 ***
        PUSH H                  ;DURATION 40us EVERY 1ms
        PUSH PSW                ;ONLY ABOUT 2.5% OVERHEAD
        LHLD TIMCNT             ;GET TIMER COUNT
        INX  H                  ;AND INCREMENT IT
        SHLD TIMCNT
        MVI  A,10H              ;RESET THE RST 7.5 F/F
        SIM
        POP  PSW
        POP  H
        EI
        RET
;
TSTV:   RST  5                  ;*** TSTV ***
        SUI  '@'                ;TEST VARIABLES
        RC                      ;C:NOT A VARIABLE
        JNZ  TV1                ;NOT "@" ARRAY
        INX  D                  ;IT IS THE "@" ARRAY
        CALL PARN               ;@ SHOULD BE FOLLOWED
        DAD  H                  ;BY (EXPR) AS ITS INDEX
        CC   QHOW               ;IS INDEX TOO BIG?
        PUSH D                  ;WILL IT OVERWRITE
        XCHG                    ;TEXT?
        CALL FREE               ;FIND SIZE OF FREE MEM
        RST  4                  ;AND CHECK THAT
        CC   ASORRY             ;IF SO, SAY "SORRY"
        LXI  H,VARBGN           ;IF NOT GET ADDRESS
        CALL SUBDE              ;OF @(EXPR) AND PUT IT
        POP  D                  ;IN HL
        RET                     ;C FLAG IS CLEARED
TV1:    CPI  1BH                ;NOT @, IS IT A TO Z?
        CMC                     ;IF NOT RETURN C FLAG
        RC
        INX  D                  ;IF A THROUGH Z
        LXI  H,VARBGN           ;COMPUTE ADDRESS OF
        RLC                     ;THAT VARIABLE
        ADD  L                  ;AND RETURN IT IN HL
        MOV  L,A                ;WITH C FLAG CLEARED
        MVI  A,0
        ADC  H
        MOV  H,A
        RET
;
;TSTC:  XTHL                    ;*** TSTC OR RST 1 ***
;       RST  5                  ;THIS IS AT LOC. 8
;       CMP  M                  ;AND THEN JUMP HERE
TC1:    INX  H                  ;COMPARE THE BYTE THAT
        JZ   TC2                ;FOLLOWS THE RST INST.
        PUSH B                  ;WITH THE TEXT (DE->)
        MOV  C,M                ;IF NOT =, ADD THE 2ND
        MVI  B,0                ;BYTE THAT FOLLOWS THE
        DAD  B                  ;RST TO THE OLD PC
        POP  B                  ;I.E., DO A RELATIVE
        DCX  D                  ;JUMP IF NOT =
TC2:    INX  D                  ;IF =, SKIP THOSE BYTES
        INX  H                  ;AND CONTINUE
        XTHL
        RET
;
TSTNUM: LXI  H,0                ;*** TSTNUM ***
        MOV  B,H                ;TEST IF THE TEXT IS
        RST  5                  ;A NUMBER
        CPI  27H                ;TEST FOR SINGLE QUOTE
        JNZ  TN0                ;NO, TRY HEXADECIMAL
        INX  D                  ;BUMP TXTPTR TO VALUE
        LDAX D                  ;GET IT
        MOV  L,A                ;RETURN IN (H)L
        INR  B                  ;INDICATE DIGIT FOUND
        INX  D                  ;BUMP PTR
        LDAX D                  ;AND TEST
        CPI  27H                ;CLOSING QUOTE
        CNZ QWHAT               ;IF NOT IT'S ERROR
        INX  D                  ;OTHERWISE BUMP TXTPTR
        RET                     ;AND RETURN
TN0:    CPI  '$'                ;TEST FOR HEXADECIMAL
        JNZ  TN1                ;NO, TRY DECIMAL
TN2:    INX  D                  ;YES, IT'S HEXADEC.
        LDAX D                  ;EVALUATE NEXT CHAR
        SUI  '0'                ;GO FROM ASCII TO HEX
        JC   TN4                ;QUIT IF ASCII BELOW '0'
        CPI  0AH                ;CHECK IF BELOW 0AH
        JC   TN3                ;OK, CONVERT
        SUI  'A'-'9'-1          ;ELSE SUB DIFF TO 'A'
        CPI  10H                ;CHECK IF BELOW 10H
        JNC  TN4                ;QUIT IF NOT
TN3:    DAD  H                  ;RIGHT SHIFT FOUR POS
        DAD  H                  ;EQUALS MULTIPLICATION
        DAD  H                  ;BY 16
        DAD  H
        CC   QHOW               ;CARRY MEANS OVERFLOW
        ORA  L                  ;ADD THE NEW DIGIT
        MOV  L,A                ;RESULT BACK IN L
        INR  B                  ;COUNT DIGITS
        JMP  TN2                ;AND CONTINUE
TN4:    XRA  A                  ;TEST VALUE OF B
        ORA  B                  ;AT LEAST ONE DIGIT
        RNZ                     ;MUST FOLLOW $ SIGN
        CALL  QHOW              ;ELSE IT'S ERROR
TN1:    CPI  '0'                ;IF NOT, RETURN 0 IN
        RC                      ;B AND HL
        CPI  '9'+1              ;IF NUMBERS, CONVERT
        RNC                     ;TO BINARY IN HL AND
        INX  D                  ;PREPARE FOR NEXT DIGIT
        INR  B                  ;B COUNTS # OF DIGITS
        PUSH B
        MOV  B,H                ;HL=10*HL+(NEW DIGIT)
        MOV  C,L
        DAD  H                  ;WHERE 10* IS DONE BY
        DAD  H                  ;SHIFT AND ADD
        DAD  B
        DAD  H
        ANI  0FH                ;STRIP THE ASCII CODE
        MOV  C,A                ;USE REG BC FOR ADD
        MVI  B,0
        DAD  B
        CC   QHOW               ;UNSIGNED, CY IS OVFLOW
        MOV  A,H                ;FOR SIGNED, CHECK
        ANI  80H                ;THE SIGN BIT
        POP  B
        LDAX D                  ;DO THIS DIGIT AFTER
        JP   TN1                ;DIGIT. S SAYS OVERFLOW
        LDA  USIGNF             ;CHECK IF IT'S UNSIGNED
        ORA  A                  ;OPERATION
        CZ   QHOW               ;ERROR IF NOT
        LDAX D                  ;ELSE LET'S CONTINUE
        JMP  TN1
;                               ;*** AHOW ***
AHOW:   POP  H                  ; PC TO HL,(DE)IS TOP OF STK
        XTHL                    ;(DE)TO HL, PC BACK ON STACK
        XCHG                    ;(DE)IS BACK IN DE, HL JUNK
QHOW:   PUSH D                  ;*** QHOW ***
        LXI  D,HOW
        JMP  ERROR
;
OK:     DB   "OK"    ,CR
HOW:    DB   "HOW? " ,CR
WHAT:   DB   "WHAT? ",CR
SORRY:  DB   "SORRY ",CR
;
;*************************************************************
;
; *** MAIN ***
;
; THIS IS THE MAIN LOOP THAT COLLECTS THE TINY BASIC PROGRAM
; AND STORES IT IN THE MEMORY.
;
; AT START, IT PRINTS OUT "(CR)OK(CR)", AND INITIALIZES THE
; STACK AND SOME OTHER INTERNAL VARIABLES.  THEN IT PROMPTS
; ">" AND READS A LINE.  IF THE LINE STARTS WITH A NON-ZERO
; NUMBER, THIS NUMBER IS THE LINE NUMBER.  THE LINE NUMBER
; (IN 16 BIT BINARY) AND THE REST OF THE LINE (INCLUDING CR)
; IS STORED IN THE MEMORY.  IF A LINE WITH THE SAME LINE
; NUMBER IS ALREADY THERE, IT IS REPLACED BY THE NEW ONE.  IF
; THE REST OF THE LINE CONSISTS OF A CR ONLY, IT IS NOT STORED
; AND ANY EXISTING LINE WITH THE SAME LINE NUMBER IS DELETED.
;
; AFTER A LINE IS INSERTED, REPLACED, OR DELETED, THE PROGRAM
; LOOPS BACK AND ASKS FOR ANOTHER LINE.  THIS LOOP WILL BE
; TERMINATED WHEN IT READS A LINE WITH ZERO OR NO LINE
; NUMBER; AND CONTROL IS TRANSFERED TO "DIRECT".
;
; TINY BASIC PROGRAM SAVE AREA STARTS AT THE MEMORY LOCATION
; LABELED "TXTBGN" AND ENDS AT "TXTEND".  WE ALWAYS FILL THIS
; AREA STARTING AT "TXTBGN", THE UNFILLED PORTION IS POINTED
; BY THE CONTENT OF A MEMORY LOCATION LABELED "TXTUNF".
;
; THE MEMORY LOCATION "CURRNT" POINTS TO THE LINE NUMBER
; THAT IS CURRENTLY BEING INTERPRETED.  WHILE WE ARE IN
; THIS LOOP OR WHILE WE ARE INTERPRETING A DIRECT COMMAND
; (SEE NEXT SECTION). "CURRNT" SHOULD POINT TO A 0.
;
ST1:    LXI  H,ST2+1            ;PTR TO MEM.LOC = 0
        SHLD CURRNT             ;CURRENT->LINE # = 0
ST2:    LXI  H,0
        SHLD LOPVAR
        SHLD STKGOS
        RET
;
CTRLC:  SUB  A                  ;FOR CTRL-C WE ALSO
        OUT  SELECT             ;RESET THE SELECT LINES
RSTART: LXI  SP,STACK           ;HERE WE COME AFTER
        CALL ST1                ;EXEC FINISH OR CTRL-C
ST0:    MVI  A,UENABL           ;MAKE SURE BEEP IS OFF
        OUT  UARTC              ;WRITE IT TO PORT
        CALL CRLF               ;AND JUMP TO HERE
        LXI  D,OK               ;DE->STRING
        SUB  A                  ;A=0
        CALL PRTSTG             ;PRINT STRING UNTIL CR
ST3:    MVI  A,'>'              ;PROMPT '>' AND
        CALL GETLN              ;READ A LINE
GLNRTN: PUSH D                  ;DE->END OF LINE
        LXI  D,BUFFER           ;DE->BEGINNING OF LINE
        CALL TSTNUM             ;TEST IF IT IS A NUMBER
        RST  5
        MOV  A,H                ;HL=VALUE OF THE # OR
        ORA  L                  ;0 IF NO # WAS FOUND
        POP  B                  ;BC->END OF LINE
        JZ   DIRECT
        DCX  D                  ;BACKUP DE AND SAVE
        MOV  A,H                ;VALUE OF LINE # THERE
        STAX D
        DCX  D
        MOV  A,L
        STAX D
        PUSH B                  ;BC,DE->BEGIN, END
        PUSH D
        MOV  A,C
        SUB  E
        PUSH PSW                ;A=# OF BYTES IN LINE
        CALL FNDLN              ;FIND THIS LINE IN SAVE
        PUSH D                  ;AREA, DE->SAVE AREA
        JNZ  ST4                ;NZ:NOT FOUND, INSERT
        PUSH D                  ;Z:FOUND, DELETE IT
        CALL FNDNXT             ;FIND NEXT LINE
                                ;DE->NEXT LINE
        POP  B                  ;BC->LINE TO BE DELETED
        LHLD TXTUNF             ;HL->UNFILLED SAVE AREA
        CALL MVUP               ;MOVE UP TO DELETE
        MOV  H,B                ;TXTUNF->UNFILLED AREA
        MOV  L,C
        SHLD TXTUNF             ;UPDATE
ST4:    POP  B                  ;GET READY TO INSERT
        LHLD TXTUNF             ;BUT FIRST CHECK IF
        POP  PSW                ;THE LENGTH OF NEW LINE
        PUSH H                  ;IS 3 (LINE # AND CR)
        CPI  3                  ;THEN DO NOT INSERT
        JZ   RSTART             ;MUST CLEAR THE STACK
        ADD  L                  ;COMPUTE NEW TXTUNF
        MOV  L,A
        MVI  A,0
        ADC  H
        MOV  H,A                ;HL->NEW UNFILLED AREA
        LXI  D,TXTEND           ;CHECK TO SEE IF THERE
        RST  4                  ;IS ENOUGH SPACE
        CNC  QSORRY             ;SORRY, NO ROOM FOR IT
        SHLD TXTUNF             ;OK, UPDATE TXTUNF
        POP  D                  ;DE->OLD UNFILLED AREA
        CALL MVDOWN
        POP  D                  ;DE->BEGIN, HL->END
        POP  H
        CALL MVUP               ;MOVE NEW LINE TO SAVE
        JMP  ST3                ;AREA
;
;*************************************************************
;
; WHAT FOLLOWS IS THE CODE TO EXECUTE DIRECT AND STATEMENT
; COMMANDS.  CONTROL IS TRANSFERED TO THESE POINTS VIA THE
; COMMAND TABLE LOOKUP CODE OF 'DIRECT' AND 'EXEC' IN LAST
; SECTION.  AFTER THE COMMAND IS EXECUTED, CONTROL IS
; TRANSFERED TO OTHERS SECTIONS AS FOLLOWS:
;
; FOR 'LIST', 'NEW', AND 'STOP': GO BACK TO 'RSTART'
; FOR 'RUN': GO EXECUTE THE FIRST STORED LINE IF ANY, ELSE
; GO BACK TO 'RSTART'.
; FOR 'GOTO' AND 'GOSUB': GO EXECUTE THE TARGET LINE.
; FOR 'RETURN' AND 'NEXT': GO BACK TO SAVED RETURN LINE.
; FOR ALL OTHERS: IF 'CURRENT' -> 0, GO TO 'RSTART', ELSE
; GO EXECUTE NEXT COMMAND.  (THIS IS DONE IN 'FINISH'.)
;*************************************************************
;
; *** NEW *** STOP *** RUN (& FRIENDS) *** & GOTO ***
;
; 'NEW(CR)' SETS 'TXTUNF' TO POINT TO 'TXTBGN'
;
; 'STOP(CR)' GOES BACK TO 'RSTART'
;
; 'RUN(CR)' FINDS THE FIRST STORED LINE, STORE ITS ADDRESS (IN
; 'CURRENT'), AND START EXECUTE IT.  NOTE THAT ONLY THOSE
; COMMANDS IN TAB2 ARE LEGAL FOR STORED PROGRAM.
;
; THERE ARE 3 MORE ENTRIES IN 'RUN':
; 'RUNNXL' FINDS NEXT LINE, STORES ITS ADDR. AND EXECUTES IT.
; 'RUNTSL' STORES THE ADDRESS OF THIS LINE AND EXECUTES IT.
; 'RUNSML' CONTINUES THE EXECUTION ON SAME LINE.
;
; 'GOTO EXPR(CR)' EVALUATES THE EXPRESSION, FIND THE TARGET
; LINE, AND JUMP TO 'RUNTSL' TO DO IT.
;
NEW:    CALL ENDCHK             ;*** NEW(CR) ***
        LXI  H,TXTBGN
        SHLD TXTUNF
;
STOP:   CALL ENDCHK             ;*** STOP(CR) ***
        JMP  RSTART
;
RUN:    CALL ENDCHK             ;*** RUN(CR) ***
        XRA  A                  ;RESET THE
        STA  RCVCHR             ;RCVD CHAR VAR
        LXI  D,TXTBGN           ;FIRST SAVED LINE
;
RUNNXL: LXI  H,0                ;*** RUNNXL ***
        CALL FNDLP              ;FIND WHATEVER LINE #
        JC   RSTART             ;C:PASSED TXTUNF, QUIT
;
RUNTSL: XCHG                    ;*** RUNTSL ***
        SHLD CURRNT             ;SET 'CURRENT'->LINE #
        XCHG
        INX  D                  ;BUMP PASS LINE #
        INX  D
;
RUNSML: CALL CHKIO              ;*** RUNSML ***
        JZ   RUNS1              ;NO CHARACTER, JUMP
        STA  RCVCHR             ;ELSE STORE IT
RUNS1:  LXI  H,TAB2-1           ;FIND COMMAND IN TAB2
        JMP  EXEC               ;AND EXECUTE IT
;
GOTO:   RST  3                  ;*** GOTO EXPR ***
        PUSH D                  ;SAVE FOR ERROR ROUTINE
        CALL ENDCHK             ;MUST FIND A CR
        CALL FNDLN              ;FIND THE TARGET LINE
        CNZ  AHOW               ;NO SUCH LINE #
        POP  PSW                ;CLEAR THE PUSH DE
        JMP  RUNTSL             ;GO DO IT
;
SAVE:   LHLD TXTUNF             ;*** SAVE PGM ***
        LXI  B,TXTBGN           ;CALC ACTUAL LENGTH
        DSUB                    ;USING TXTUNF-TXTBGN
        LXI  D,2                ;HL IS NOW LENGTH OF PGM
        DAD  D                  ;ADD TWO FOR LEN ITSELF
        XCHG                    ;PUT IT IN DE
        LXI  B,EESTRT+2         ;BC IS START IN EEPROM
        LXI  H,TXTUNF           ;START SAVING AT LENGTH
        CALL EEWR               ;WRITE TO EEPROM
        JMP  RSTART
;
LOAD:   CALL LD0                ;*** LOAD PGM ***
        JMP  RSTART
;
LD0:    LXI  B,EESTRT+2         ;START ADR IN EEPROM
        LXI  D,2                ;FIND THE LEN IN EEPROM
        LXI  H,TXTUNF           ;STORE TEMPORARY
        CALL EERD               ;READ EEPROM
        LHLD TXTUNF             ;GET THE LENGTH VARIABLE
        LXI  B,TXTBGN           ;CALC ACTUAL LENGTH
        DSUB                    ;USING TXTUNF-TXTBGN
        XCHG                    ;CHECK THAT LENGTH IS
        LXI  H,VARBGN-TXTBGN    ;LESS THAN AVAILABLE
        RST  4                  ;COMPARE HL - DE
        JNC  LD1                ;NO CARRY = WILL FIT
        LXI  H,TXTBGN           ;ELSE REINIT TEXT PTR
        SHLD TXTUNF             ;BECAUSE READ LENGTH
        CALL QSORRY             ;WILL NOT FIT RAM
LD1:    LXI  B,EESTRT+4         ;OK READ EERPOM
        LXI  H,TXTBGN           ;TO TEXT AREA
        CALL EERD
        RET
;
EDIT:   PUSH D                  ;SAVE PTR FOR THE ASCII NUM
        CALL TSTNUM             ;LOOK FOR A LINE NUMBER
        MOV  A,L                ;RETURN ZERO (HL) IF NO NUM
        ORA  H                  ;CHECK FOR ABSENCE OF NUM
        CZ   AHOW               ;THEN ASK HOW?
        CALL ENDCHK             ;MAKE SURE NO GARBAGE
        CALL FNDLN              ;RETURN LINE PTR IN (DE)
        JC   RSTART             ;OR, NO SUCH LINE
        POP  H                  ;GET PTR TO ASCII BACK
        XCHG                    ;SWAP WITH LINE PTR
        RST  5                  ;SKIP BLANKS TO NUMBER
        LXI  B,BUFFER           ;START FILL INPUT BUFFER
ED1:    LDAX D                  ;PULL ASCII NUMBER CHARS
        CPI  CR                 ;UNTIL 'CR' FOUND
        JZ   ED2
        STAX B                  ;MOVE NUMBER TO BUF START
        INX  D                  ;BUMP POINTERS
        INX  B                  ;AND CONTINUE
        JMP  ED1
ED2:    MVI  A,' '              ;INSERT A SPACE AFTER
        STAX B                  ;THE LINE NUMBER
        INX  H                  ;BUMP PAST THE INTEGER
ED3:    INX  H                  ;LINE NUMBER IN MEMORY
        INX  B
        MOV  A,M                ;PULL REST OF LINE
        STAX B                  ;COPY TO INPUT BUF
        CPI  CR                 ;UNTIL AND INCLUDING 'CR'
        JNZ  ED3
        LXI  D,BUFFER           ;BEGIN AT BUFFER START
        MVI  A,CR               ;STOP WHEN 'CR' FOUND
        CALL PRTSTG             ;PRINT BUFFER
        DCX  D                  ;BACK UP, POINT TO CR
        LXI  H,GLNRTN           ;FIND RETURN ADDR
        PUSH H                  ;AND PUT IT ON STACK
        JMP  EDITLN             ;GOTO GETLINE FOR EDIT
;
HELP:   LXI  H,MSGHLP           ;*** SHORT HELP ***
        JMP  MA1                ;PRINT THE TEXT UNTIL NULL
;
MAN:    LXI  H,MSGMAN           ;*** MANUAL ***
MA1:    CALL PSTR               ;PRINT THE TEXT UNTIL NULL
        JMP  RSTART
;
;*************************************************************
;
; *** LIST *** & PRINT *** ETC. ***
;
; LIST HAS TWO FORMS:
; 'LIST(CR)' LISTS ALL SAVED LINES
; 'LIST #(CR)' START LIST AT THIS LINE #
; YOU CAN STOP THE LISTING BY CONTROL C KEY
;
; PRINT COMMAND IS 'PRINT ....:' OR 'PRINT ....(CR)'
; WHERE '....' IS A LIST OF EXPRESIONS, FORMATS, BACK-
; ARROWS, AND STRINGS.  THESE ITEMS ARE SEPERATED BY COMMAS.
;
; A FORMAT IS A POUND SIGN FOLLOWED BY A NUMBER.  IT CONTROLS
; THE NUMBER OF SPACES THE VALUE OF A EXPRESION IS GOING TO
; BE PRINTED.  IT STAYS EFFECTIVE FOR THE REST OF THE PRINT
; COMMAND UNLESS CHANGED BY ANOTHER FORMAT.  IF NO FORMAT IS
; SPECIFIED, 6 POSITIONS WILL BE USED.
;
; A STRING IS QUOTED IN A PAIR OF SINGLE QUOTES OR A PAIR OF
; DOUBLE QUOTES.
;
; A BACK-SLASH MEANS PRINT THE ASCII CHAR OF FOLLOWING NUMBER.
;
; A (CRLF) IS GENERATED AFTER THE ENTIRE LIST HAS BEEN
; PRINTED OR IF THE LIST IS A NULL LIST.  HOWEVER IF THE LIST
; ENDED WITH A COMMA, NO (CRLF) IS GENERATED.
;
LIST:   CALL TSTNUM             ;TEST IF THERE IS A #
        CALL ENDCHK             ;IF NO # WE GET A 0
        CALL FNDLN              ;FIND THIS OR NEXT LINE
LS1:    JC   RSTART             ;C:PASSED TXTUNF
        CALL PRTLN              ;PRINT THE LINE
        CALL CHKIO              ;STOP IF HIT CONTROL-C
        CALL FNDLP              ;FIND NEXT LINE
        JMP  LS1                ;AND LOOP BACK
;
PRINT:  MVI  C,6                ;C = # OF SPACES
        RST  1                  ;IF NULL LIST & ":"
        DB   ':'
        DB   PR2-$-1
        CALL CRLF               ;GIVE CR-LF AND
        JMP  RUNSML             ;CONTINUE SAME LINE
PR2:    RST  1                  ;IF NULL LIST (CR)
        DB   CR
        DB   PR0-$-1
        CALL CRLF               ;ALSO GIVE CR-LF AND
        JMP  RUNNXL             ;GO TO NEXT LINE
PR0:    RST  1                  ;ELSE IS IT FORMAT?
        DB   '#'
        DB   PR4-$-1
        RST  3                  ;YES, EVALUATE EXPR.
        MOV  C,L                ;AND SAVE IT IN C
        JMP  PR3                ;LOOK FOR MORE TO PRINT
PR4:    RST  1                  ;ELSE IS IT HEXADECIMAL?
        DB   '$'
        DB   PR1-$-1
        RST  3                  ;YES, EVALUATE EXPR.
        MOV  A,L                ;HEXADECIMAL FORMAT
        CMA                     ;CHANGE SIGN
        INR  A                  ;AS A FLAG
        MOV  C,A
        JMP  PR3                ;LOOK FOR MORE TO PRINT
PR1:    CALL QTSTG              ;OR IS IT A STRING?
        JMP  PR8                ;IF NOT, MUST BE EXPR.
PR3:    RST  1                  ;IF ",", GO FIND NEXT
        DB   ','
        DB   PR6-$-1
        CALL FIN                ;IN THE LIST.
        JMP  PR0                ;LIST CONTINUES
PR6:    CALL CRLF               ;LIST ENDS
        RST  6
PR8:    RST  3                  ;EVALUATE THE EXPR
        PUSH B
        CALL PRTNUM             ;PRINT THE VALUE
        POP  B
        JMP  PR3                ;MORE TO PRINT?
;
PUTC:   RST  7                  ;*** PUTC(EXPR) ***
        MOV  A,H
        ORA  A                  ;CHECK HL < 256
        CNZ  QHOW               ;ELSE CAN'T PRINT CHAR
PC1:    IN   UARTC              ;COME HERE TO DO OUTPUT
        ANI  1H                 ;STATUS BIT
        JZ   PC1                ;NOT READY, WAIT
        MOV  A,L                ;READY, GET CHAR
        OUT  UARTD              ;AND SEND IT OUT
        RST  6
;
WAIT:   RST  7                  ;*** WAIT(EXPR) ***
        JMP  BP0                ;SAME AS BEEP BUT NO SOUND
;
BEEP:   RST  7                  ;*** BEEP(EXPR) ***
        MVI  A,UENABL+URTS      ;BITPATTERN FOR BEEP ON
        OUT  UARTC              ;WRITE IT TO PORT
BP0:    XCHG                    ;ARG TO DE AND TXPTR TO HL
        PUSH H                  ;SAVE TXTPTR
        CALL TCNT               ;GET A START TIMESTAMP
        MOV  B,H                ;TRANSFER START
        MOV  C,L                ;TIMESTAMP TO BC
BP1:    CALL CHKIO              ;ACCEPT CTRL-C TO QUIT
        JZ   BP2                ;JUMP IF NO CHAR RCVD
        STA  RCVCHR             ;ELSE STORE IT FOR GETC
BP2:    CALL TCNT               ;GET NEW TIMESTAMP
        DSUB                    ;SUBTRACT ORIG STAMP IN BC
        RST  4                  ;CMPR WITH ARGUMENT IN DE
        JC   BP1                ;CARRY LESS THAN ARGUMENT
        MVI  A,UENABL           ;BITPATTERN FOR BEEP OFF
        OUT  UARTC              ;WRITE IT TO PORT
        POP  D                  ;RESTORE TXTPTR
        RST  6
;
XTAL:   RST  7                  ;*** XTAL(EXPR) ***
        PUSH D                  ;USE DE TO CHECK MAX AND MIN
        LXI  D,19662            ;DOUBLE XTAL OF 8085-2 CHIP
        RST  4                  ;COMPARE HL - DE
        CNC  AHOW               ;NUMBER TOO LARGE
        LXI  D,1536             ;ONE 4TH OF NOMINAL XTAL
        RST  4                  ;COMPARE AGAIN
        CC   AHOW               ;NUMBER TOO SMALL
        POP  D                  ;RESTORE TXT PTR
        CALL SETXTL             ;USE DEDICATED SUB ROUTINE
        RST  6
;
SIGNED: XRA  A                  ;SET SIGNED OPERATION
        STA  USIGNF
        RST  6
;
UNSIGN: MVI  A,1                ;SET UNSIGNED OPERATION
        STA  USIGNF
        RST  6
;
POUT:   RST  7                  ;GET FIRST ARGUMENT (ADDR)
        MOV  A,H                ;HI BYTE OF ARGUMENT
        ORA  A                  ;MUST BE ZERO
        CNZ  QHOW               ;ELSE CAN'T CONTINUTE
        PUSH H                  ;SAVE IT
        CALL SKPCOM             ;COMMA MAY SEPARATE ARGS
        RST  7                  ;GET NEXT ARGUMENT (VALUE)
        XTHL                    ;SWAP VAL TO STK, ADDR TO HL
        MOV  A,L                ;LOW BYTE IS THE IO ADDR
        ORA  A                  ;IS IT ADDR 0? (8155 CMDREG)
        LHLD TXTUNF             ;POINT AT MEM.LOC AFTER PGM
        MVI  M,0D3H             ;PLACE THE "OUT" INSTRUCTION
        INX  H                  ;NEXT LOCATION
        MOV  M,A                ;PLACE THE OUT PORT NUMBER
        INX  H                  ;NEXT LOCATION
        MVI  M,0C9H             ;PLACE THE "RET" INSTRUCTION
        POP  H                  ;POP BACK THE VALUE ARGUMENT
        MOV  A,L                ;OUT INSTR.ONLY USE LOW BYTE
        JNZ  POU1               ;JUMP/SKIP SAVE IF NOT ZERO
        STA  PCMCPY             ;SAVE CTRLBYTE IN SHADOW REG
POU1:   CALL RAMEXC             ;CALL SUBROUTINE IN RAM
        RST  6
;
SOD:    RST  7                  ;GET ARGUMENT (DATA)
        MOV  A,L                ;GET LO BYTE
        CALL SDOUT              ;AND SEND IT
        RST  6
;
POKE:   RST  7                  ;GET FIRST ARGUMENT (ADDR)
        PUSH H                  ;SAVE IT
        CALL SKPCOM             ;COMMA MAY SEPARATE ARGS
        RST  7                  ;GET NEXT ARGUMENT (VALUE)
        MOV  A,L                ;VALUE LOW BYTE TO ACC
        POP  H                  ;RESTORE ADDRESS
        MOV  M,A                ;COPY TO MEM LOC.(HL)
        RST  6
;
SETXTL: ARHL                    ;DIV BY 2 TO GET TIMER COUNT
        MOV  A,L                ;LOW BYTE OF COUNT
        OUT  PTIML              ;SEND TO TIMER LOW REGISTER
        MOV  A,H                ;COUNTER IN 8155 IS 14 BIT
        ANI  3FH                ;MAKE SURE BITS 6,7 ARE ZERO
        ORI  40H                ;SET MODE CONT. SQUARE WAVE
        OUT  PTIMH              ;SEND TO TIMER HI REGISTER
        LDA  PCMCPY             ;GET THE PORT COMMAND SHADOW
        ANI  0FH                ;REMOVE ANY UNWANTED CFGBITS
        ORI  0C0H               ;ISSUE START COMMAND
        OUT  PCMD               ;SEND TO 8155 CONFIG REG
        RET
;
;*************************************************************
;
; *** GOSUB *** & RETURN ***
;
; 'GOSUB EXPR;' OR 'GOSUB EXPR (CR)' IS LIKE THE 'GOTO'
; COMMAND, EXCEPT THAT THE CURRENT TEXT POINTER, STACK POINTER
; ETC. ARE SAVE SO THAT EXECUTION CAN BE CONTINUED AFTER THE
; SUBROUTINE 'RETURN'.  IN ORDER THAT 'GOSUB' CAN BE NESTED
; (AND EVEN RECURSIVE), THE SAVE AREA MUST BE STACKED.
; THE STACK POINTER IS SAVED IN 'STKGOS', THE OLD 'STKGOS' IS
; SAVED IN THE STACK.  IF WE ARE IN THE MAIN ROUTINE, 'STKGOS'
; IS ZERO (THIS WAS DONE BY THE "MAIN" SECTION OF THE CODE),
; BUT WE STILL SAVE IT AS A FLAG FOR NO FURTHER 'RETURN'S.
;
; 'RETURN(CR)' UNDOS EVERYTHING THAT 'GOSUB' DID, AND THUS
; RETURN THE EXECUTION TO THE COMMAND AFTER THE MOST RECENT
; 'GOSUB'.  IF 'STKGOS' IS ZERO, IT INDICATES THAT WE
; NEVER HAD A 'GOSUB' AND IS THUS AN ERROR.
;
GOSUB:  CALL PUSHA              ;SAVE THE CURRENT "FOR"
        RST  3                  ;PARAMETERS
        PUSH D                  ;AND TEXT POINTER
        CALL FNDLN              ;FIND THE TARGET LINE
        CNZ  AHOW               ;NOT THERE. SAY "HOW?"
        LHLD CURRNT             ;FOUND IT, SAVE OLD
        PUSH H                  ;'CURRNT' OLD 'STKGOS'
        LHLD STKGOS
        PUSH H
        LXI  H,0                ;AND LOAD NEW ONES
        SHLD LOPVAR
        DAD  SP
        SHLD STKGOS
        JMP  RUNTSL             ;THEN RUN THAT LINE
RETURN: CALL ENDCHK             ;THERE MUST BE A CR
        LHLD STKGOS             ;OLD STACK POINTER
        MOV  A,H                ;0 MEANS NOT EXIST
        ORA  L
        CZ   QWHAT              ;SO, WE SAY: "WHAT?"
        SPHL                    ;ELSE, RESTORE IT
        POP  H
        SHLD STKGOS             ;AND THE OLD 'STKGOS'
        POP  H
        SHLD CURRNT             ;AND THE OLD 'CURRNT'
        POP  D                  ;OLD TEXT POINTER
        CALL POPA               ;OLD "FOR" PARAMETERS
        RST  6                  ;AND WE ARE BACK HOME
;
;*************************************************************
;
; *** FOR *** & NEXT ***
;
; 'FOR' HAS TWO FORMS:
; 'FOR VAR=EXP1 TO EXP2 STEP EXP3' AND 'FOR VAR=EXP1 TO EXP2'
; THE SECOND FORM MEANS THE SAME THING AS THE FIRST FORM WITH
; EXP3=1.  (I.E., WITH A STEP OF +1.)
; TBI WILL FIND THE VARIABLE VAR, AND SET ITS VALUE TO THE
; CURRENT VALUE OF EXP1.  IT ALSO EVALUATES EXP2 AND EXP3
; AND SAVE ALL THESE TOGETHER WITH THE TEXT POINTER ETC. IN
; THE 'FOR' SAVE AREA, WHICH CONSISTS OF 'LOPVAR', 'LOPINC',
; 'LOPLMT', 'LOPLN', AND 'LOPPT'.  IF THERE IS ALREADY SOME-
; THING IN THE SAVE AREA (THIS IS INDICATED BY A NON-ZERO
; 'LOPVAR'), THEN THE OLD SAVE AREA IS SAVED IN THE STACK
; BEFORE THE NEW ONE OVERWRITES IT.
; TBI WILL THEN DIG IN THE STACK AND FIND OUT IF THIS SAME
; VARIABLE WAS USED IN ANOTHER CURRENTLY ACTIVE 'FOR' LOOP.
; IF THAT IS THE CASE, THEN THE OLD 'FOR' LOOP IS DEACTIVATED.
; (PURGED FROM THE STACK..)
;
; 'NEXT VAR' SERVES AS THE LOGICAL (NOT NECESSARILLY PHYSICAL)
; END OF THE 'FOR' LOOP.  THE CONTROL VARIABLE VAR. IS CHECKED
; WITH THE 'LOPVAR'.  IF THEY ARE NOT THE SAME, TBI DIGS IN
; THE STACK TO FIND THE RIGHT ONE AND PURGES ALL THOSE THAT
; DID NOT MATCH.  EITHER WAY, TBI THEN ADDS THE 'STEP' TO
; THAT VARIABLE AND CHECK THE RESULT WITH THE LIMIT.  IF IT
; IS WITHIN THE LIMIT, CONTROL LOOPS BACK TO THE COMMAND
; FOLLOWING THE 'FOR'.  IF OUTSIDE THE LIMIT, THE SAVE AREA
; IS PURGED AND EXECUTION CONTINUES.
;
FOR:    CALL PUSHA              ;SAVE THE OLD SAVE AREA
        CALL SETVAL             ;SET THE CONTROL VAR.
        DCX  H                  ;HL IS ITS ADDRESS
        SHLD LOPVAR             ;SAVE THAT
        LXI  H,TAB5-1           ;USE 'EXEC' TO LOOK
        JMP  EXEC               ;FOR THE WORD 'TO'
FR1:    RST  3                  ;EVALUATE THE LIMIT
        SHLD LOPLMT             ;SAVE THAT
        LXI  H,TAB6-1           ;USE 'EXEC' TO LOOK
        JMP EXEC                ;FOR THE WORD 'STEP'
FR2:    RST  3                  ;FOUND IT, GET STEP
        JMP  FR4
FR3:    LXI  H,1H               ;NOT FOUND, SET TO 1
FR4:    SHLD LOPINC             ;SAVE THAT TOO
FR5:    LHLD CURRNT             ;SAVE CURRENT LINE #
        SHLD LOPLN
        XCHG                    ;AND TEXT POINTER
        SHLD LOPPT
        LXI  B,0AH              ;DIG INTO STACK TO
        LHLD LOPVAR             ;FIND 'LOPVAR'
        XCHG
        MOV  H,B
        MOV  L,B                ;HL=0 NOW
        DAD  SP                 ;HERE IS THE STACK
        DB   3EH
FR7:    DAD  B                  ;EACH LEVEL IS 10 DEEP
        MOV  A,M                ;GET THAT OLD 'LOPVAR'
        INX  H
        ORA  M
        JZ   FR8                ;0 SAYS NO MORE IN IT
        MOV  A,M
        DCX  H
        CMP  D                  ;SAME AS THIS ONE?
        JNZ  FR7
        MOV  A,M                ;THE OTHER HALF?
        CMP  E
        JNZ  FR7
        XCHG                    ;YES, FOUND ONE
        LXI  H,0H
        DAD  SP                 ;TRY TO MOVE SP
        MOV  B,H
        MOV  C,L
        LXI  H,0AH
        DAD  D
        CALL MVDOWN             ;AND PURGE 10 WORDS
        SPHL                    ;IN THE STACK
FR8:    LHLD LOPPT              ;JOB DONE, RESTORE DE
        XCHG
        RST  6                  ;AND CONTINUE
FR9:    CALL QWHAT
;
NEXT:   CALL TSTV               ;GET ADDRESS OF VAR.
        CC   QWHAT              ;NO VARIABLE, "WHAT?"
        SHLD VARNXT             ;YES, SAVE IT
NX0:    PUSH D                  ;SAVE TEXT POINTER
        XCHG
        LHLD LOPVAR             ;GET VAR. IN 'FOR'
        MOV  A,H
        ORA  L                  ;0 SAYS NEVER HAD ONE
        CZ   AWHAT              ;SO WE ASK: "WHAT?"
        RST  4                  ;ELSE WE CHECK THEM
        JZ   NX3                ;OK, THEY AGREE
        POP  D                  ;NO, LET'S SEE
        CALL POPA               ;PURGE CURRENT LOOP
        LHLD VARNXT             ;AND POP ONE LEVEL
        JMP  NX0                ;GO CHECK AGAIN
NX3:    MOV  E,M                ;COME HERE WHEN AGREED
        INX  H
        MOV  D,M                ;DE=VALUE OF VAR.
        LHLD LOPINC
        PUSH H
        MOV  A,H
        XRA  D
        MOV  A,D
        DAD  D                  ;ADD ONE STEP
        JM   NX4
        XRA  H
        JM   NX5
NX4:    XCHG
        LHLD LOPVAR             ;PUT IT BACK
        MOV  M,E
        INX  H
        MOV  M,D
        LHLD LOPLMT             ;HL->LIMIT
        POP  PSW                ;OLD HL
        ORA  A
        JP   NX1                ;STEP > 0
        XCHG                    ;STEP < 0
NX1:    CALL CKHLDE             ;COMPARE WITH LIMIT
        POP  D                  ;RESTORE TEXT POINTER
        JC   NX2                ;OUTSIDE LIMIT
        LHLD LOPLN              ;WITHIN LIMIT, GO
        SHLD CURRNT             ;BACK TO THE SAVED
        LHLD LOPPT              ;'CURRNT' AND TEXT
        XCHG                    ;POINTER
        RST  6
NX5:    POP  H
        POP  D
NX2:    CALL POPA               ;PURGE THIS LOOP
        RST  6
;
;*************************************************************
;
; *** REM *** IF *** INPUT *** & LET (& DEFLT) ***
;
; 'REM' CAN BE FOLLOWED BY ANYTHING AND IS IGNORED BY TBI.
; TBI TREATS IT LIKE AN 'IF' WITH A FALSE CONDITION.
;
; 'IF' IS FOLLOWED BY AN EXPR. AS A CONDITION AND ONE OR MORE
; COMMANDS (INCLUDING OTHER 'IF'S) SEPERATED BY SEMI-COLONS.
; NOTE THAT THE WORD 'THEN' IS NOT USED.  TBI EVALUATES THE
; EXPR. IF IT IS NON-ZERO, EXECUTION CONTINUES.  IF THE
; EXPR. IS ZERO, THE COMMANDS THAT FOLLOWS ARE IGNORED AND
; EXECUTION CONTINUES AT THE NEXT LINE.
;
; 'INPUT' COMMAND IS LIKE THE 'PRINT' COMMAND, AND IS FOLLOWED
; BY A LIST OF ITEMS.  IF THE ITEM IS A STRING IN SINGLE OR
; DOUBLE QUOTES, OR IS A BACK-ARROW, IT HAS THE SAME EFFECT AS
; IN 'PRINT'.  IF AN ITEM IS A VARIABLE, THIS VARIABLE NAME IS
; PRINTED OUT FOLLOWED BY A COLON.  THEN TBI WAITS FOR AN
; EXPR. TO BE TYPED IN.  THE VARIABLE IS THEN SET TO THE
; VALUE OF THIS EXPR.  IF THE VARIABLE IS PROCEDED BY A STRING
; (AGAIN IN SINGLE OR DOUBLE QUOTES), THE STRING WILL BE
; PRINTED FOLLOWED BY A COLON.  TBI THEN WAITS FOR INPUT EXPR.
; AND SET THE VARIABLE TO THE VALUE OF THE EXPR.
;
; IF THE INPUT EXPR. IS INVALID, TBI WILL PRINT "WHAT?",
; "HOW?" OR "SORRY" AND REPRINT THE PROMPT AND REDO THE INPUT.
; THE EXECUTION WILL NOT TERMINATE UNLESS YOU TYPE CONTROL-C.
; THIS IS HANDLED IN 'INPERR'.
;
; 'LET' IS FOLLOWED BY A LIST OF ITEMS SEPERATED BY COMMAS.
; EACH ITEM CONSISTS OF A VARIABLE, AN EQUAL SIGN, AND AN EXPR.
; TBI EVALUATES THE EXPR. AND SET THE VARIABLE TO THAT VALUE.
; TBI WILL ALSO HANDLE 'LET' COMMAND WITHOUT THE WORD 'LET'.
; THIS IS DONE BY 'DEFLT'.
;
; 'REM' PUTS ZERO IN HL TO MAKE A FALSE IF STATEMENT. THEN COMES
; 3EH WHICH GETS EXECUTED AS OPCODE 3EH (MVI A,_). NEXT INSTR.
; IS 'RST 3' (OPCODE DFH) WHICH BECOMES DATA FOR THE MVI A,_
; SO 3EH +'RST 3' FORMS A DUMMY INSTRUCTION (MVI A,DFH) TO REACH
; THE NEXT INTENDED USEFUL INSTRUCTION WHICH IS MOV A,H AND THEN
; 'IF' STATEMENT CONTINUES. INTERSTING WAY TO MAKE A NON-JUMP..
;
REM:    LXI  H,0H               ;*** REM ***
        DB   3EH                ;THIS IS LIKE 'IF 0'
;
IFF:    RST  3                  ;*** IF ***
        MOV  A,H                ;IS THE EXPR.=0?
        ORA  L
        JNZ  RUNSML             ;NO, CONTINUE
        CALL FNDSKP             ;YES, SKIP REST OF LINE
        JNC  RUNTSL             ;AND RUN THE NEXT LINE
        JMP  RSTART             ;IF NO NEXT, RE-START
;
INPERR: LHLD STKINP             ;*** INPERR ***
        SPHL                    ;RESTORE OLD SP
        POP  H                  ;AND OLD 'CURRNT'
        SHLD CURRNT
        POP  D                  ;AND OLD TEXT POINTER
        POP  D                  ;REDO INPUT
;
INPUT:                          ;*** INPUT ***
IP1:    PUSH D                  ;SAVE IN CASE OF ERROR
        CALL QTSTG              ;IS NEXT ITEM A STRING?
        JMP  IP2                ;NO
        CALL TSTV               ;YES, BUT FOLLOWED BY A
        JC   IP4                ;VARIABLE?   NO.
        JMP  IP3                ;YES.  INPUT VARIABLE
IP2:    PUSH D                  ;SAVE FOR 'PRTSTG'
        CALL TSTV               ;MUST BE VARIABLE NOW
        CC   QWHAT              ;"WHAT?" IT IS NOT?
        LDAX D                  ;GET READY FOR 'PRTSTR'
        MOV  C,A
        SUB  A
        STAX D
        POP  D
        CALL PRTSTG             ;PRINT STRING AS PROMPT
        MOV  A,C                ;RESTORE TEXT
        DCX  D
        STAX D
IP3:    PUSH D                  ;SAVE TEXT POINTER
        XCHG
        LHLD CURRNT             ;ALSO SAVE 'CURRNT'
        PUSH H
        LXI  H,IP1              ;PTR TO A NEG.NUMBER
        SHLD CURRNT             ;AS A FLAG
        LXI  H,0H               ;SAVE SP TOO
        DAD  SP
        SHLD STKINP
        PUSH D                  ;OLD HL
        MVI  A,':'              ;PRINT THIS TOO
        CALL GETLN              ;AND GET A LINE
        LXI  D,BUFFER           ;POINTS TO BUFFER
        RST  3                  ;EVALUATE INPUT
        POP  D                  ;OK, GET OLD HL
        XCHG
        MOV  M,E                ;SAVE VALUE IN VAR.
        INX  H
        MOV  M,D
        POP  H                  ;GET OLD 'CURRNT'
        SHLD CURRNT
        POP  D                  ;AND OLD TEXT POINTER
IP4:    POP  PSW                ;PURGE JUNK IN STACK
        RST  1                  ;IS NEXT CH. ','?
        DB   ','
        DB   IP5-$-1
        JMP  IP1                ;YES, MORE ITEMS.
IP5:    RST  6
;
DEFLT:  LDAX D                  ;***  DEFLT ***
        CPI  CR                 ;EMPTY LINE IS OK
        JZ   LT1                ;ELSE IT IS 'LET'
;
LET:    CALL SETVAL             ;*** LET ***
        RST  1                  ;SET VALUE TO VAR.
        DB   ','
        DB   LT1-$-1
        JMP  LET                ;ITEM BY ITEM
LT1:    RST  6                  ;UNTIL FINISH
;
;*************************************************************
;
; *** EXPR ***
;
; 'EXPR' EVALUATES ARITHMETICAL OR LOGICAL EXPRESSIONS.
; <EXPR>::<EXPR0>
;         <EXPR0><REL.OP.><EXPR0>
; WHERE <REL.OP.> IS ONE OF THE OPERATORS IN TAB8 AND THE
; RESULT OF THESE OPERATIONS IS 1 IF TRUE AND 0 IF FALSE.
; <EXPR0>::=<EXPR1>(|, ^ OR &)<EXPR1>(....)
; <EXPR1>::=<EXPR2>(<< OR >>)<EXPR2>(....)
; <EXPR2>::=(+ OR -)<EXPR3>(+ OR -)<EXPR3>(....)
; WHERE () ARE OPTIONAL AND (....) ARE OPTIONAL REPEATS.
; <EXPR3>::=<EXPR4>(*, % OR /><EXPR4>)(....)
; <EXPR4>::=<VARIABLE>, <FUNCTION> OR (<EXPR>)
; <EXPR> IS RECURSIVE SO THAT VARIABLE '@' CAN HAVE AN <EXPR>
; AS INDEX, FUNCTIONS CAN HAVE AN <EXPR> AS ARGUMENTS, AND
; <EXPR4> CAN BE AN <EXPR> IN PARANTHESE.
;
;EXPR:  CALL EXPR0              ;THIS IS AT LOC. 18
;       PUSH H                  ;SAVE <EXPR0> VALUE
RELOP:  LXI  H,TAB8-1           ;LOOKUP REL.OP.
        JMP  EXEC               ;GO DO IT
ROP1:   CALL ROP8               ;REL.OP.">="
        RC                      ;NO, RETURN HL=0
        MOV  L,A                ;YES, RETURN HL=1
        RET
ROP2:   CALL ROP8               ;REL.OP."!="
        RZ                      ;FALSE, RETURN HL=0
        MOV  L,A                ;TRUE, RETURN HL=1
        RET
ROP3:   CALL ROP8               ;REL.OP.">"
        RZ                      ;FALSE
        RC                      ;ALSO FALSE, HL=0
        MOV  L,A                ;TRUE, HL=1
        RET
ROP4:   CALL ROP8               ;REL.OP."<="
        MOV  L,A                ;SET HL=1
        RZ                      ;REL. TRUE, RETURN
        RC
        MOV  L,H                ;ELSE SET HL=0
        RET
ROP5:   CALL ROP8               ;REL.OP."=="
        RNZ                     ;FALSE, RETURN HL=0
        MOV  L,A                ;ELSE SET HL=1
        RET
ROP6:   CALL ROP8               ;REL.OP."<"
        RNC                     ;FALSE, RETURN HL=0
        MOV  L,A                ;ELSE SET HL=1
        RET
ROP7:   POP  H                  ;NOT .REL.OP
        RET                     ;RETURN HL=<EXPR0>
ROP8:   MOV  A,C                ;SUBROUTINE FOR ALL
        POP  H                  ;REL.OP.'S
        POP  B
        PUSH H                  ;REVERSE TOP OF STACK
        PUSH B
        MOV  C,A
        CALL EXPR0              ;GET 2ND <EXPR0>
        XCHG                    ;VALUE IN DE NOW
        XTHL                    ;1ST <EXPR0> IN HL
        CALL CKHLDE             ;COMPARE 1ST WITH 2ND
        POP  D                  ;RESTORE TEXT POINTER
        LXI  H,0H               ;SET HL=0, A=1
        MVI  A,1
        RET
;
EXPR0:  CALL EXPR1              ;GET 1ST <EXPR1>
XP01:   RST  1                  ;BITWISE OR?
        DB   '|'
        DB   XP02-$-1
        PUSH H                  ;YES, SAVE VALUE
        CALL EXPR1              ;GET 2ND <EXPR1>
        XCHG                    ;2ND IN DE
        XTHL                    ;1ST IN HL
        MOV  A,H
        ORA  D
        MOV  H,A
        MOV  A,L
        ORA  E
        MOV  L,A
        POP  D                  ;RESTORE TEXT POINTER
        JMP  XP01
XP02:   RST  1                  ;BITWISE EXCLUSIVE OR?
        DB   '^'
        DB   XP03-$-1
        PUSH H                  ;YES, SAVE VALUE
        CALL EXPR1              ;GET 2ND <EXPR1>
        XCHG                    ;2ND IN DE
        XTHL                    ;1ST IN HL
        MOV  A,H
        XRA  D
        MOV  H,A
        MOV  A,L
        XRA  E
        MOV  L,A
        POP  D                  ;RESTORE TEXT POINTER
        JMP  XP01
XP03:   RST  1                  ;BITWISE AND?
        DB   '&'
        DB   XP04-$-1
        PUSH H                  ;YES, SAVE VALUE
        CALL EXPR1              ;GET 2ND <EXPR1>
        XCHG                    ;2ND IN DE
        XTHL                    ;1ST IN HL
        MOV  A,H
        ANA  D
        MOV  H,A
        MOV  A,L
        ANA  E
        MOV  L,A
        POP  D                  ;RESTORE TEXT POINTER
        JMP  XP01
XP04:   RET
;
EXPR1:  CALL EXPR2              ;GET 1ST <EXPR2>
        PUSH H                  ;SAVE <EXPR2> VALUE
        LXI  H,TAB9-1           ;LOOKUP SHIFT.OP.
        JMP  EXEC               ;IN TABLE
XP11:   CALL EXPR2              ;GET 2ND <EXPR2>
        XCHG                    ;2ND IN DE
        XTHL                    ;1ST IN HL
        CALL LSHIFT             ;SHIFT IT
        POP  D                  ;RESTORE TEXT POINTER
        RET
XP12:   CALL EXPR2              ;GET 2ND <EXPR2>
        XCHG                    ;2ND IN DE
        XTHL                    ;1ST IN HL
        CALL RSHIFT             ;SHIFT IT
        POP  D                  ;RESTORE TEXT POINTER
        RET
XP13:   POP  H                  ;NOT SHIFT, RESTORE
        RET                     ;<EXPR2> AND QUIT
;
LSHIFT: MVI  A,16               ;MAX SHIFT COUNTER
LSH1:   DCX  D                  ;DE IS NUMBER OF SHIFTS
        JK   LSH2               ;K-FLAG SET WHEN DONE
        DAD  H                  ;LEFT SHIFT IS SAME AS
        DCR  A                  ;MULTIPLICATION BY TWO
        JNZ  LSH1
LSH2:   RET
;
RSHIFT: MVI  A,16               ;MAX SHIFT COUNTER
RSH1:   DCX  D                  ;DE IS NUMBER OF SHIFTS
        JK   RSH2               ;K-FLAG SET WHEN DONE
        ARHL                    ;SHIFT RIGHT 16-BIT
        DCR  A
        JNZ  RSH1
RSH2:   RET
;
EXPR2:  CALL EXPR3              ;1ST <EXPR3>
XP23:   RST  1                  ;ADD?
        DB   '+'
        DB   XP25-$-1
        PUSH H                  ;YES, SAVE VALUE
        CALL EXPR3              ;GET 2ND <EXPR3>
XP24:   XCHG                    ;2ND IN DE
        XTHL                    ;1ST IN HL
        MOV  A,H                ;COMPARE SIGN
        XRA  D
        MOV  A,D
        DAD  D
        POP  D                  ;RESTORE TEXT POINTER
        JM   XP23               ;1ST AND 2ND SIGN DIFFER
        XRA  H                  ;1ST AND 2ND SIGN EQUAL
        JP   XP23               ;SO IS RESULT
        LDA  USIGNF             ;IF UNSIGNED
        ORA  A                  ;OPERATION
        JNZ  XP23               ;DON'T EVALUATE SIGN
        CALL QHOW               ;ELSE WE HAVE OVERFLOW
XP25:   RST  1                  ;SUBTRACT?
        DB   '-'
        DB   XP42-$-1
XP26:   PUSH H                  ;YES, SAVE 1ST <EXPR3>
        CALL EXPR3              ;GET 2ND <EXPR3>
        CALL CHGSGN             ;NEGATE
        JMP  XP24               ;AND ADD THEM
;
EXPR3:  CALL EXPR4              ;GET 1ST <EXPR4>
XP31:   RST  1                  ;MULTIPLY?
        DB   '*'
        DB   XP34-$-1
        PUSH H                  ;YES, SAVE 1ST
        CALL EXPR4              ;AND GET 2ND <EXPR4>
        MVI  B,0H               ;CLEAR B FOR SIGN
        CALL CHKSGN             ;CHECK SIGN
        XTHL                    ;1ST IN HL
        CALL CHKSGN             ;CHECK SIGN OF 1ST
        XCHG
        XTHL
        MOV  A,H                ;IS HL > 255 ?
        ORA  A
        JZ   XP32               ;NO
        XCHG                    ;YES, SWAP 2ND TO HL
        MOV  A,H                ;CHECK SIZE OF 2ND
        ORA  A
        CNZ  AHOW               ;ALSO >, WILL OVERFLOW
XP32:   MOV  A,L                ;THIS IS DUMB
        LXI  H,0H               ;CLEAR RESULT
        ORA  A                  ;ADD AND COUNT
        JZ   XP35
XP33:   DAD  D
        CC   AHOW               ;OVERFLOW
        DCR  A
        JNZ  XP33
        JMP  XP35               ;FINISHED
;
MULOVF: LDA  USIGNF             ;IF UNSIGNED
        ORA  A                  ;OPERATION DON'T
        RNZ                     ;EVALUATE OVFLOW
        JMP  QHOW               ;CALL ADR ALREADY ON STK
;
XP34:   RST  1                  ;MODULUS?
        DB   '%'
        DB   XP341-$-1
        JMP  XP342
XP341:  RST  1                  ;DIVIDE?
        DB   '/'
        DB   XP42-$-1
XP342:  PUSH H                  ;YES, SAVE 1ST <EXPR4>
        STA  DIVOPR             ;STORE OPERATION / OR %
        CALL EXPR4              ;AND GET THE SECOND ONE
        MVI  B,0H               ;CLEAR B FOR SIGN
        CALL CHKSGN             ;CHECK SIGN OF 2ND
        XTHL                    ;GET 1ST IN HL
        CALL CHKSGN             ;CHECK SIGN OF 1ST
        XCHG
        XTHL
        XCHG
        MOV  A,D                ;DIVIDE BY 0?
        ORA  E
        CZ   AHOW               ;SAY "HOW?"
        PUSH B                  ;ELSE SAVE SIGN
        CALL DIVIDE             ;USE SUBROUTINE
        LDA  DIVOPR             ;GET BACK ACTUAL OPERATION
        CPI  '%'                ;IF MODULUS
        JZ   XP343              ;THEN KEEP REMAINDER IN HL
        MOV  H,B                ;RESULT IN HL NOW
        MOV  L,C
XP343:  POP  B                  ;GET SIGN BACK
XP35:   POP  D                  ;AND TEXT POINTER
        MOV  A,H                ;HL MUST BE +
        ORA  A
        CM   MULOVF             ;ELSE IT IS OVERFLOW
        MOV  A,B
        ORA  A
        CM   CHGSGN             ;CHANGE SIGN IF NEEDED
        JMP  XP31               ;LOOK FOR MORE TERMS
;
EXPR4:  LXI  H,TAB4-1           ;FIND FUNCTION IN TAB4
        JMP  EXEC               ;AND GO DO IT
XP40:   CALL TSTV               ;NO, NOT A FUNCTION
        JC   XP41               ;NOR A VARIABLE
        MOV  A,M                ;VARIABLE
        INX  H
        MOV  H,M                ;VALUE IN HL
        MOV  L,A
        RET
XP41:   CALL TSTNUM             ;OR IS IT A NUMBER
        MOV  A,B                ;# OF DIGIT
        ORA  A
        RNZ                     ;OK
PARN:   RST  1
        DB   '('
        DB   XP43-$-1
        RST  3                  ;"(EXPR)"
        RST  1
        DB   ')'
        DB   XP43-$-1
XP42:   RET
XP43:   CALL QWHAT              ;ELSE SAY: "WHAT?"
;
;*************************************************************
;
; *** FUNCTIONS, MAY HAVE AN ARGUMENT, ALWAYS RETURN VALUE ***
;
; ** !(LOGICAL NOT) ** ~(BITWISE NOT) ** -(MINUS) ** +(PLUS) *
;
; ** RND *** ABS *** PEEK *** TIME *** GETC *** LEN *** FREE *
;
NOT:    RST  7                  ;*** !(EXPR) ***
        MOV  A,H                ;CHECK IF BOTH H
        ORA  L                  ;AND L WERE ZERO
        JNZ  NOT1               ;TEST THEM
        INR  L                  ;YES, RETURN 1
        RET
NOT1:   LXI  H,0                ;NO, RETURN 0
        RET
;
INV:    RST  7                  ;*** ~(EXPR) ***
        MOV  A,H                ;INVERT, OR TAKE
        CMA                     ;ONE'S COMPLEMENT
        MOV  H,A                ;OF H AND L
        MOV  A,L                ;RESPECTIVELY
        CMA
        MOV  L,A
        RET
;
MINUS:  CALL INV                ;*** -(EXPR) ***
        INX  H                  ;TWO'S COMPLIMENT
        RET
;
PLUS:   RST  7                  ;*** +(EXPR) ***
        RET
;
RND:    RST  7                  ;*** RND(EXPR) ***
        MOV  A,H                ;EXPR MUST BE +
        ORA  A
        CM   QHOW
        ORA  L                  ;AND NON-ZERO
        CZ   QHOW
        PUSH D                  ;SAVE BOTH
        PUSH B                  ;TXTPTR AND BC REG
        PUSH H                  ;SAVE ARGUMENT
        CALL PRNG               ;ROLL THE DICE
        POP  D                  ;GET BACK ARGUMENT
        CALL DIVIDE             ;RND(N)=MOD(M,N)+1
        POP  B
        POP  D
        INX  H
        RET
;
PRNG:   LHLD RNDNUM             ;PSEUDO RANDOM NUMBER
        MOV  A,H                ;GENERATOR. PUBLIC DOMAIN
        MOV  B,H                ;ALLEGEDLY ORIGINATING
        MOV  C,L                ;FROM ZX SPECTRUM GAME.
        MOV  H,L                ;TRANSLATED FROM Z80
        MVI  L,253              ;TO 8085 ASSEMBLER.
        DSUB                    ;VERIFIED PERIOD 65536
        SBI  0
        DSUB
        MVI  B,0
        SBB  B
        MOV  C,A
        DSUB
        JNC  PRNG1
        INX  H
PRNG1:  SHLD RNDNUM
        RET
;
ABS:    RST  7                  ;*** ABS(EXPR) ***
        MOV  A,H
        ORA  A                  ;CHECK SIGN OF HL
        RP                      ;IF +, WE'RE DONE
        PUSH PSW                ;ELSE CHANGE SIGN
        CALL CHGSGN
        POP  PSW                ;COMPARE SIGN BEFORE
        XRA  H                  ;AND AFTER
        CP   QHOW               ;IS SAME, IT'S ERROR
        RET
;
PIN:    RST  7                  ;*** IN(EXPR) ***
        MOV  A,H                ;HI BYTE OF ARGUMENT
        ORA  A                  ;MUST BE ZERO
        CNZ  QHOW               ;ELSE CAN'T CONTINUTE
        MOV  A,L                ;LOW BYTE IS THE IO ADDR
        LHLD TXTUNF             ;POINT AT MEM.LOC AFTER PGM
        MVI  M,0DBH             ;PLACE THE "IN" INSTRUCTION
        INX  H                  ;NEXT LOCATION
        MOV  M,A                ;PLACE THE IN PORT NUMBER
        INX  H                  ;NEXT LOCATION
        MVI  M,0C9H             ;PLACE THE "RET" INSTRUCTION
        CALL RAMEXC             ;CALL SUBROUTINE IN RAM
        MOV  L,A                ;FUNCTION RETURN VALUE IN HL
        MVI  H,0                ;HI BYTE ALWAYS ZERO
        RET
;
SID:    CALL SDIN               ;READ SERIAL INTERFACE
        MOV  L,A                ;FUNCTION RETURN VALUE IN HL
        MVI  H,0                ;HI BYTE ALWAYS ZERO
        RET
;
RAMEXC: LHLD TXTUNF             ;POINT AT MEM.LOC TO EXECUTE
        PCHL                    ;FORCE ADDR TO PGM.CNTR
;
PEEK:   RST  7                  ;*** PEEK(EXPR) ***
        MOV  A,M                ;MEM LOC. (HL) TO A
        MOV  L,A                ;RETURN VALUE IN HL
        MVI  H,0                ;HI BYTE ALWAYS ZERO
        RET
;
TCNT:   DI                      ;*** TIME ***
        LHLD TIMCNT             ;RETREIVE CURRENT COUNT
        EI
        RET
;
GETC:   MVI  H,0                ;*** GETC ***
        LDA  RCVCHR             ;GET LAST RCVD CHAR
        MOV  L,A                ;RETURN IN HL
        XRA  A                  ;RESET THE
        STA  RCVCHR             ;RCVD CHAR AFTER READ
        RET
;
USR:    RST  7                  ;** USR(EXPR)[,REGS..] **
        SHLD STKLMT+6           ;SAVE 1ST ARG, CALL ADDR
        CALL SKPCOM             ;COMMA MAY SEPARATE ARGS
        JZ   US1                ;WE HAVE MORE ARGUMENTS
        PUSH D                  ;ELSE SAVE TXTPTR
        JMP  US2                ;AND CONTINUE W/O ARGS
US1:    RST  7                  ;GET 2ND ARG WHICH IS HL
        PUSH H                  ;SAVE IT
        CALL SKPCOM             ;COMMA MAY SEPARATE ARGS
        RST  7                  ;GET 3RD ARG WICH IS DE
        PUSH H                  ;BUT DE IS TXTPTR SO SAVE
        CALL SKPCOM             ;COMMA MAY SEPARATE ARGS
        RST  7                  ;GET 4TH ARG
        MOV  B,H                ;WHICH IS
        MOV  C,L                ;REG BC
        CALL SKPCOM             ;COMMA MAY SEPARATE ARGS
        RST  7                  ;GET 5TH ARG WICH IS ACC
        MOV  A,L                ;MOVE ARG TO ITS POSITION
        POP  H                  ;RETURN ARG(DE) TO HL
        XCHG                    ;TXTPTR TO HL,(DE) TO DE
        XTHL                    ;TXTPTR TO STK,(HL) TO HL
US2:    PUSH H                  ;SAVE (HL)ARG (OR DUMMY)
        LXI  H,USRTN            ;FIND OUR RETURN ADDR
        XTHL                    ;SWAP WITH ARG ON STACK
        PUSH H                  ;SAVE ARGUMENT AGAIN
        LHLD STKLMT+6           ;GET THE CALL ADDRESS
        XTHL                    ;AGAIN SWAP WITH STACK
        RET                     ;CALL BY PULL FROM STACK
USRTN:  POP  D                  ;RESTORE TEXT PTR
        RET
;
LEN:    LXI  H,TXTBGN           ;*** LEN ***
        PUSH D                  ;GET THE NUMBER OF
        XCHG                    ;BYTES BETWEEN 'TXTBGN'
        LHLD TXTUNF             ;AND 'TXTUNF'
        CALL SUBDE
        POP  D
        RET
;
FREE:   LHLD TXTUNF             ;*** FREE ***
        PUSH D                  ;GET THE NUMBER OF FREE
        XCHG                    ;BYTES BETWEEN 'TXTUNF'
        LXI  H,VARBGN           ;AND 'VARBGN'
        CALL SUBDE
        POP  D
        RET
;
;*************************************************************
;
; *** DIVIDE *** SUBDE *** CHKSGN *** CHGSGN *** & CKHLDE ***
;
; 'DIVIDE' DIVIDES HL BY DE, RESULT IN BC, REMAINDER IN HL
;
; 'SUBDE' SUBSTRACTS DE FROM HL
;
; 'CHKSGN' CHECKS SIGN OF HL.  IF +, NO CHANGE.  IF -, CHANGE
; SIGN AND FLIP SIGN OF B.
;
; 'CHGSGN' CHANGES SIGN OF HL AND B UNCONDITIONALLY.
;
; 'CKHLDE' CHECKS SIGN OF HL AND DE.  IF DIFFERENT, HL AND DE
; ARE INTERCHANGED.  IF SAME SIGN, NOT INTERCHANGED.  EITHER
; CASE, HL DE ARE THEN COMPARED TO SET THE FLAGS.
;
DIVIDE: PUSH H                  ;*** DIVIDE ***
        MOV  L,H                ;DIVIDE H BY DE
        MVI  H,0
        CALL DV1
        MOV  B,C                ;SAVE RESULT IN B
        MOV  A,L                ;(REMINDER+L)/DE
        POP  H
        MOV  H,A
DV1:    MVI  C,0FFH             ;RESULT IN C
DV2:    INR  C                  ;DUMB ROUTINE
        CALL SUBDE              ;DIVIDE BY SUBTRACT
        JNC  DV2                ;AND COUNT
        DAD  D
        RET
;
SUBDE:  MOV  A,L                ;*** SUBDE ***
        SUB  E                  ;SUBSTRACT DE FROM
        MOV  L,A                ;HL
        MOV  A,H
        SBB  D
        MOV  H,A
        RET
;
CHKSGN: MOV  A,H                ;*** CHKSGN ***
        ORA  A                  ;CHECK SIGN OF HL
        RP                      ;IF -, CHANGE SIGN
        LDA  USIGNF             ;IF UNSIGNED
        ORA  A                  ;OPERATION
        RNZ                     ;DON'T FLIP SIGN
;
CHGSGN: MOV  A,H                ;*** CHGSGN ***
        CMA                     ;CHANGE SIGN OF HL
        MOV  H,A
        MOV  A,L
        CMA
        MOV  L,A
        INX  H
        MOV  A,B                ;AND ALSO FLIP B
        XRI  80H
        MOV  B,A
        RET
;
CKHLDE: MOV  A,H
        XRA  D                  ;SAME SIGN?
        JP   CK1                ;YES, COMPARE
        LDA  USIGNF             ;IF UNSIGNED
        ORA  A                  ;OPERATION
        JNZ  CK1                ;DON'T EXCHG
        XCHG                    ;NO, XCH AND COMP
CK1:    RST  4
        RET
;
;*************************************************************
;
; *** SETVAL *** FIN *** ENDCHK *** & ERROR (& FRIENDS) ***
;
; "SETVAL" EXPECTS A VARIABLE, FOLLOWED BY AN EQUAL SIGN AND
; THEN AN EXPR.  IT EVALUATES THE EXPR. AND SET THE VARIABLE
; TO THAT VALUE.
;
; "FIN" CHECKS THE END OF A COMMAND.  IF IT ENDED WITH ":",
; EXECUTION CONTINUES.  IF IT ENDED WITH A CR, IT FINDS THE
; NEXT LINE AND CONTINUE FROM THERE.
;
; "ENDCHK" CHECKS IF A COMMAND IS ENDED WITH CR.  THIS IS
; REQUIRED IN CERTAIN COMMANDS.  (GOTO, RETURN, AND STOP ETC.)
;
; "ERROR" PRINTS THE STRING POINTED BY DE (AND ENDS WITH CR).
; IT THEN PRINTS THE LINE POINTED BY 'CURRNT' WITH A "?"
; INSERTED AT WHERE THE OLD TEXT POINTER (SHOULD BE ON TOP
; OF THE STACK) POINTS TO.  EXECUTION OF TB IS STOPPED
; AND TBI IS RESTARTED.  HOWEVER, IF 'CURRNT' -> ZERO
; (INDICATING A DIRECT COMMAND), THE DIRECT COMMAND IS NOT
; PRINTED.  AND IF 'CURRNT' -> NEGATIVE # (INDICATING 'INPUT'
; COMMAND), THE INPUT LINE IS NOT PRINTED AND EXECUTION IS
; NOT TERMINATED BUT CONTINUED AT 'INPERR'.
;
; RELATED TO 'ERROR' ARE THE FOLLOWING:
; 'QWHAT' SAVES TEXT POINTER IN STACK AND GET MESSAGE "WHAT?"
; 'AWHAT' ASSUMES THAT TEXT PTR IS ALREADY PUSHED TO STACK BY
; WHATEVER CODE THAT EXECUTED IMMEDIATELY PRIOR ERROR OCCURRED.
; 'QSORRY' AND 'ASORRY' DO SAME KIND OF THING.
; 'AHOW' AND 'AHOW' IN THE ZERO PAGE SECTION ALSO DO THIS.
; ALL THE WHATS, HOWS AND SORRYS SHALL BE ACCESSED USING A
; SUBROUTINE CALL INSTEAD OF OLD VERSIONS OF TBI USING JUMP.
; 'ERRADR' RETREIVES CALL ADDRESS OF THE ASSEMBLY INSTRUCTION
; THAT CAUSED ERROR AND PRINTS THE LINE NUMBER AS HEXADECIMAL.
;
SETVAL: CALL TSTV               ;*** SETVAL ***
        CC   QWHAT              ;"WHAT?" NO VARIABLE
        PUSH H                  ;SAVE ADDRESS OF VAR.
        RST  1                  ;PASS "=" SIGN
        DB   '='
        DB   SV1-$-1
        RST  3                  ;EVALUATE EXPR.
        MOV  B,H                ;VALUE IS IN BC NOW
        MOV  C,L
        POP  H                  ;GET ADDRESS
        MOV  M,C                ;SAVE VALUE
        INX  H
        MOV  M,B
        RET
SV1:    CALL QWHAT              ;NO "=" SIGN
;
FIN:    RST  1                  ;*** FIN ***
        DB   ':'
        DB   FI1-$-1
        POP  PSW                ;":", PURGE RET. ADDR.
        JMP  RUNSML             ;CONTINUE SAME LINE
FI1:    RST  1                  ;NOT ":", IS IT CR?
        DB   CR
        DB   FI2-$-1
        POP  PSW                ;YES, PURGE RET. ADDR.
        JMP  RUNNXL             ;RUN NEXT LINE
FI2:    RET                     ;ELSE RETURN TO CALLER
;
ENDCHK: RST  5                  ;*** ENDCHK ***
        CPI  CR                 ;END WITH CR?
        RZ                      ;OK, ELSE SAY: "WHAT?"
        CALL QWHAT
;
SKPCOM: RST  5                  ;*** SKPCOM ***
        CPI  ','                ;NEXT NON BLANK MAY BE COMMA
        RNZ                     ;IF NOT JUST RETURN, ELSE
        INX  D                  ;SKIP TO NEXT CHAR IN BUF
        RET
;                               ;*** AWHAT ***
AWHAT:  POP  H                  ; PC TO HL,(DE)IS TOP OF STK
        XTHL                    ;(DE)TO HL, PC BACK ON STACK
        XCHG                    ;(DE)IS BACK IN DE, HL JUNK
QWHAT:  PUSH D                  ;*** QWHAT ***
        LXI  D,WHAT
ERROR:  MVI  A,CR               ;*** ERROR ***
        CALL PRTSTG             ;PRINT 'WHAT?', 'HOW?'
        POP  D                  ;OR 'SORRY'
;                               ;*** ERRADR ***
        POP  H                  ;GET CALLERS ADDR TO HL
        DCX  H                  ;WE WANT ADDRESS
        DCX  H                  ;OF THE CALL OPERAND
        DCX  H                  ;DIFF IS THREE BYTES
        MVI  A,'['              ;PRINT OPENING BRACE
        RST  2                  ;FOR READABILIY
        CALL PRTWD              ;PRINT THE ADDRESS
        MVI  A,']'              ;PRINT CLOSING BRACE
        RST  2                  ;AROUND ADDRESS
        MVI  A,CR               ;END WITH A CR+LF
        RST  2                  ;AND CONTINUE ERR HANDLER
;
        LDAX D                  ;SAVE THE CHARACTER
        PUSH PSW                ;AT WHERE OLD DE ->
        SUB  A                  ;AND PUT A 0 THERE
        STAX D
        LHLD CURRNT             ;GET CURRENT LINE #
        PUSH H
        MOV  A,M                ;CHECK THE VALUE
        INX  H
        ORA  M
        JZ   ERR1               ;IF ZERO IT'S DIRECT MODE
        POP  D                  ;DE -> CURRENT LINE
        MOV  A,M                ;IF NEGATIVE,
        ORA  A
        JM   INPERR             ;REDO INPUT
        CALL PRTLN              ;ELSE PRINT THE LINE
        DCX  D                  ;UPTO WHERE THE 0 IS
        POP  PSW                ;RESTORE THE CHARACTER
        STAX D
        MVI  A,'?'              ;PRINT A "?"
        RST  2
        SUB  A                  ;AND THE REST OF THE
        CALL PRTSTG             ;LINE
        JMP  RSTART             ;THEN RESTART
ERR1:   POP  H
        POP  PSW                ;RESTORE THE CHARACTER
        STAX D                  ;WHERE THE NULL WAS PUT
        JMP  RSTART
;                               ;*** ASORRY ***
ASORRY: POP  H                  ; PC TO HL,(DE)IS TOP OF STK
        XTHL                    ;(DE)TO HL, PC BACK ON STACK
        XCHG                    ;(DE)IS BACK IN DE, HL JUNK
QSORRY: PUSH D                  ;*** QSORRY ***
        LXI  D,SORRY
        JMP  ERROR
;
;*************************************************************
;
; *** GETLN *** FNDLN (& FRIENDS) ***
;
; 'GETLN' READS A INPUT LINE INTO 'BUFFER'.  IT FIRST PROMPT
; THE CHARACTER IN A (GIVEN BY THE CALLER), THEN IT FILLS
; THE BUFFER AND ECHOS.  IT IGNORES LF'S AND NULLS, BUT STILL
; ECHOS THEM BACK.  BACKSPACE IS USED TO CAUSE IT TO DELETE
; THE LAST CHARACTER (IF THERE IS ONE).
; CR SIGNALS THE END OF A LINE, AND CAUSE 'GETLN' TO RETURN.
;
; 'FNDLN' FINDS A LINE WITH A GIVEN LINE # (IN HL) IN THE
; TEXT SAVE AREA.  DE IS USED AS THE TEXT POINTER.  IF THE
; LINE IS FOUND, DE WILL POINT TO THE BEGINNING OF THAT LINE
; (I.E., THE LOW BYTE OF THE LINE #), AND FLAGS ARE NC & Z.
; IF THAT LINE IS NOT THERE AND A LINE WITH A HIGHER LINE #
; IS FOUND, DE POINTS TO THERE AND FLAGS ARE NC & NZ.  IF
; WE REACHED THE END OF TEXT SAVE AREA AND CANNOT FIND THE
; LINE, FLAGS ARE C & NZ.
; 'FNDLN' WILL INITIALIZE DE TO THE BEGINNING OF THE TEXT SAVE
; AREA TO START THE SEARCH.  SOME OTHER ENTRIES OF THIS
; ROUTINE WILL NOT INITIALIZE DE AND DO THE SEARCH.
; 'FNDLNP' WILL START WITH DE AND SEARCH FOR THE LINE #.
; 'FNDNXT' WILL BUMP DE BY 2, FIND A CR AND THEN START SEARCH.
; 'FNDSKP' USE DE TO FIND A CR, AND THEN START SEARCH.
;
; Insert  ESC[1~
; Home    ESC[2~
; PgUp    ESC[3~
; Delete  ESC[4~
; End     ESC[5~
; PgDn    ESC[6~
; Arrow U ESC[A
; Arrow D ESC[B
; Arrow R ESC[C
; Arrow L ESC[D
;
GETLN:  RST  2                  ;*** GETLN ***
        LXI  D,BUFFER           ;PROMPT AND INIT.
EDITLN: MOV  B,D                ;USE (BC) AS INSERT PTR
        MOV  C,E                ;AND (DE) AS LENGTH PTR
GL1:    CALL INCHR              ;WAIT FOR CHR RCVD
        CPI  CR                 ;WAS IT CR?
        JNZ  GL2                ;NO, CHECK WHAT ELSE
        RST  2                  ;ECHO CR AND AUTO LF
        STAX D                  ;SAVE CR AT BUF.END
        INX  D                  ;AND BUMP POINTER
        RET                     ;END OF LINE
GL2:    CPI  BS                 ;DELETE LAST CHARACTER?
        JNZ  GL3                ;NO, CHECK WHAT ELSE
        PUSH H                  ;DUMMY SAVE HL
        LXI  H,GL1              ;GET DESIRED RETURN ADDR
        XTHL                    ;PUT IT ON STACK
        JMP  BACKSP             ;DO BACKSPACE
GL3:    CPI  ESC                ;ESCAPE SEQ?
        JNZ  GL4                ;NO, CHECK WHAT ELSE
        CALL INCHR              ;GET NEXT CHAR IN ESC SEQ.
        CPI  '['                ;SHOULD BE [
        JNZ  GL5                ;ELSE GO ON AND ECHO
        PUSH H                  ;DUMMY SAVE HL
        LXI  H,GL1              ;GET DESIRED RETURN ADDR
        XTHL                    ;PUT IT ON STACK
        CALL INCHR              ;GET NEXT CHAR
        CPI  'D'                ;LEFT ARROW?
        JZ   ALEFT              ;JMP AND RETURN TO GL1
        CPI  'C'                ;RIGHT ARROW?
        JZ   ARIGHT             ;JMP AND RETURN TO GL1
        CPI  'B'                ;DOWN ARROW?
        JZ   AUPDN              ;JMP AND RETURN TO GL1
        CPI  'A'                ;UP ARROW?
        JZ   AUPDN              ;JMP AND RETURN TO GL1
        CPI  '4'                ;POSSIBLE DELETE KEY?
        RNZ                     ;IF NOT RETURN TO GL1
        CALL INCHR              ;GET NEXT CHAR
        CPI  '~'                ;SHOULD BE ~ FOR DELETE
        RNZ                     ;IF NOT RETURN TO GL1
        JMP  DELETE             ;JMP AND RETURN TO GL1
GL4:    CPI  ' '                ;CHECK IF PRINTABLE CHAR
        JC   GL1                ;IF NOT GO BACK
GL5:    CPI  'a'                ;CHECK IF LOWER CASE
        JC   INSERT             ;IT WAS BELOW ASCII 'a'
        CPI  'z'+1              ;CHARACTERS a TO z
        JNC  INSERT             ;IT WAS ABOVE ASCII 'z'
        SUI  'a'-'A'            ;CONVERT LOWER TO UPPER
INSERT: MOV  H,B                ;COPY BUF.INSERT POS
        MOV  L,C                ;TO HL AS TMP.PTR
INS1:   PUSH PSW                ;SAVE OUR CHAR TO INSERT
        MOV  A,M                ;GET THE CHAR TO BUMP
        STAX D                  ;SAVE FOR NEXT LOOP
        POP  PSW                ;RESTORE CHAR FOR INSERT
        RST  2                  ;OUT TO TERMINAL
        MOV  M,A                ;AND PUT TO BUF
        RST  4                  ;COMP TMPPTR(HL) BUFLEN(DE)
        LDAX D                  ;RESTORE NEXT CHAR
        JZ   INS2               ;INSERT WAS ON LAST POS
        INX  H                  ;ELSE BUMP INSERT PTR
        JMP  INS1               ;AND LOOP THROUGH BUFFER
INS2:   PUSH H                  ;SAVE TMP.PTR
        DSUB                    ;COMP WITH INS.PTR(BC)
        POP  H                  ;RESTORE
        JZ   INS3               ;TMP.PTR IS AT INSERT POS
        MVI  A,08H              ;ELSE USE BACKSPACE TO
        RST  2                  ;BUMP BACK CURSOR
        DCX  H                  ;AND LET PTR FOLLOW
        JMP  INS2               ;LOOP UNTIL DONE
INS3:   INX  B                  ;BUMP INSERT PTR
        INX  D                  ;AND BUFLEN PTR
        LXI  H,BUFEND           ;END OF BUFFER IS LIMIT
        RST  4                  ;COMP LIMIT WITH BUFLEN(DE)
        JNZ  INS4               ;DID NOT HIT LIMIT
        DCX  D                  ;ELSE PULL BACK ONE STEP
INS4:   DSUB                    ;COMP LIMIT WITH INSERT(BC)
        JNZ  GL1                ;DID NOT HIT LIMIT
        DCX  B                  ;ELSE PULL BACK ONE STEP
        MVI  A,08H              ;AND USE BACKSPACE TO
        RST  2                  ;BUMP BACK CURSOR
        JMP  GL1
;
ALEFT:  LXI  H,BUFFER           ;TMP PTR TO START OF BUF
        DSUB                    ;COMPARE WITH INSERT PTR
        RZ                      ;QUIT IF PTR IS AT FIRST POS
        DCX  B                  ;ELSE DECREMENT INSERT PTR
        MVI  A,08H              ;BACKSPACE CURSOR ONE POS
        RST  2                  ;OUT TO TERMINAL
        RET
;
ARIGHT: MOV  H,D                ;COPY BUFLEN PTR
        MOV  L,E                ;TO HL AS TMP
        DSUB                    ;COMPARE WITH INSERT PTR
        RZ                      ;QUIT IF PTR IS AT LAST POS
        LDAX B                  ;ELSE MOVE CURSOR BY
        RST  2                  ;PRINTING CURRENT CHAR
        INX  B                  ;BUMP INSERT PTR ONE STEP
        RET
;
AUPDN:  LXI  H,BUFFER           ;TMP PTR TO START OF BUF
        RST  4                  ;COMP START WITH BUFLEN (DE)
        RNZ                     ;QUIT IF BUFFER NOT EMPTY
        MOV  A,M                ;GET FIRST CHAR OF OLD BUFF
        CPI  '@'                ;ONLY ALLOW REPETITION OF
        RC                      ;DIRECT CMDS AND STATEMENTS
        MVI  A,CR               ;STOP PRINT WHEN CR FOUND
        CALL PRTSTG             ;PRINT OLD BUF WITHOUT CR
        DCX  D                  ;BACK UP BUF PTR TO CR POS
        MOV  B,D                ;COPY BUFFER POSITION
        MOV  C,E                ;TO INSERT POINTER(BC)
        RET
;
BACKSP: CALL ALEFT              ;COMPARE WITH INSERT PTR
        RZ                      ;QUIT IF PTR IS AT FIRST POS
        JMP  DEL1               ;CONTINUE AS IF DELETE
DELETE: MOV  H,D                ;COPY BUFLEN
        MOV  L,E                ;TO HL
        DSUB                    ;COMPARE WITH INSERT PTR
        RZ                      ;QUIT IF PTR IS AT LAST POS
DEL1:   MOV  H,B                ;COPY BUF.INSERT
        MOV  L,C                ;TO HL AS TMP.PTR
DEL2:   INX  H                  ;BUMP ONE STEP AHEAD
        RST  4                  ;COMP TMPPTR(HL) BUFLEN(DE)
        JZ   DEL3               ;GO AND WRAP UP
        MOV  A,M                ;GET NEXT CHAR IN BUF
        DCX  H                  ;BUMP ONE STEP BACK
        MOV  M,A                ;AND OVERWRITE CHAR IN POS
        INX  H                  ;BUMP FWD AGAIN
        RST  2                  ;AND OUT TO TERMINAL
        JMP  DEL2               ;LOOP UNTIL READY
DEL3:   MVI  A,' '              ;PRINT SPACE TO ERASE
        RST  2                  ;WHATEVER CHAR IS ON TERM.
DEL4:   MVI  A,08H              ;USE BACKSPACE TO
        RST  2                  ;BUMP BACK CURSOR
        DCX  H                  ;AND LET PTR FOLLOW
        PUSH H                  ;SAVE TMP.PTR
        DSUB                    ;COMP WITH INS.PTR(BC)
        POP  H                  ;RESTORE
        JNZ  DEL4               ;LOOP UNTIL REACH POS
        DCX  D                  ;BUFLEN IS NOW ONE LESS
        RET                     ;DONE
;
FNDLN:  MOV  A,H                ;*** FNDLN ***
        ORA  A                  ;CHECK SIGN OF HL
        CM   QHOW               ;IT CANNOT BE -
        LXI  D,TXTBGN           ;INIT TEXT POINTER
;
FNDLP:                          ;*** FDLNP ***
FL1:    PUSH H                  ;SAVE LINE #
        LHLD TXTUNF             ;CHECK IF WE PASSED END
        DCX  H
        RST  4
        POP  H                  ;GET LINE # BACK
        RC                      ;C,NZ PASSED END
        LDAX D                  ;WE DID NOT, GET BYTE 1
        SUB  L                  ;IS THIS THE LINE?
        MOV  B,A                ;COMPARE LOW ORDER
        INX  D
        LDAX D                  ;GET BYTE 2
        SBB  H                  ;COMPARE HIGH ORDER
        JC   FL2                ;NO, NOT THERE YET
        DCX  D                  ;ELSE WE EITHER FOUND
        ORA  B                  ;IT, OR IT IS NOT THERE
        RET                     ;NC,Z:FOUND, NC,NZ:NO
;
FNDNXT:                         ;*** FNDNXT ***
        INX  D                  ;FIND NEXT LINE
FL2:    INX  D                  ;JUST PASSED BYTE 1 & 2
;
FNDSKP: LDAX D                  ;*** FNDSKP ***
        CPI  CR                 ;TRY TO FIND CR
        JNZ  FL2                ;KEEP LOOKING
        INX  D                  ;FOUND CR, SKIP OVER
        JMP  FL1                ;CHECK IF END OF TEXT
;
;*************************************************************
;
; *** PRTSTG *** QTSTG *** PRTNUM *** & PRTLN ***
;
; 'PRTSTG' PRINTS A STRING POINTED BY DE.  IT STOPS PRINTING
; AND RETURNS TO CALLER WHEN EITHER A CR IS PRINTED OR WHEN
; THE NEXT BYTE IS THE SAME AS WHAT WAS IN A (GIVEN BY THE
; CALLER).  OLD A IS STORED IN B, OLD B IS LOST.
;
; 'QTSTG' LOOKS FOR A BACK-SLASH, SINGLE QUOTE, OR DOUBLE
; QUOTE.  IF NONE OF THESE, RETURN TO CALLER.  IF BACK-SLASH,
; OUTPUT ASCII OF FOLLOWING NUMBER. IF SINGLE OR DOUBLE QUOTE,
; PRINT THE STRING IN THE QUOTE AND DEMAND A MATCHING UNQUOTE.
; AFTER THE PRINTING THE NEXT 3 BYTES OF THE CALLER IS SKIPPED
; OVER (USUALLY A JUMP INSTRUCTION.
;
; 'PRTNUM' PRINTS THE NUMBER IN HL.  LEADING BLANKS ARE ADDED
; IF NEEDED TO PAD THE NUMBER OF SPACES TO THE NUMBER IN C.
; HOWEVER, IF THE NUMBER OF DIGITS IS LARGER THAN THE # IN
; C, ALL DIGITS ARE PRINTED ANYWAY.  NEGATIVE SIGN IS ALSO
; PRINTED AND COUNTED IN, POSITIVE SIGN IS NOT.  IF REGISTER
; C IS NEGATIVE, NUMBER IS PRINTED IN HEXADECIMAL.
;
; 'PRTLN' PRINTS A SAVED TEXT LINE WITH LINE # AND ALL.
;
PRTSTG: MOV  B,A                ;*** PRTSTG ***
PS1:    LDAX D                  ;GET A CHARACTER
        INX  D                  ;BUMP POINTER
        CMP  B                  ;SAME AS OLD A?
        RZ                      ;YES, RETURN
        RST  2                  ;ELSE PRINT IT
        CPI  CR                 ;WAS IT A CR?
        JNZ  PS1                ;NO, NEXT
        RET                     ;YES, RETURN
;
QTSTG:  RST  1                  ;*** QTSTG ***
        DB   '"'
        DB   QT3-$-1
        MVI  A,'"'              ;IT IS A "
QT1:    CALL PRTSTG             ;PRINT UNTIL ANOTHER
        CPI  CR                 ;WAS LAST ONE A CR?
        POP  H                  ;RETURN ADDRESS
        JZ   RUNNXL             ;WAS CR, RUN NEXT LINE
QT2:    INX  H                  ;SKIP 3 BYTES ON RETURN
        INX  H
        INX  H
        PCHL                    ;RETURN
QT3:    RST  1                  ;IS IT A '
        DB   27H
        DB   QT4-$-1
        MVI  A,27H              ;YES, DO THE SAME
        JMP  QT1                ;AS IN "
QT4:    RST  1                  ;IS IT BACK-SLASH?
        DB   '\\'
        DB   QT5-$-1
QT6:    IN   UARTC              ;YES, CR WITHOUT LF
        ANI  1H                 ;STATUS BIT
        JZ   QT6                ;NOT READY, WAIT
        CALL TSTNUM             ;GET SUCCEEDING NUMBER
        MOV  A,B                ;B IS NUMBER OF DIGITS
        ORA  A                  ;DID WE GET ANY DIGITS
        CZ   QHOW               ;IF NOT, ERROR
        MOV  A,H                ;ACCEPT ONLY
        ORA  A                  ;ASCII 0..255
        CNZ  QHOW               ;ERROR IF HL > 255
        MOV  A,L                ;PUT CHAR IN ACC
        OUT  UARTD              ;AND SEND IT OUT
        POP  H                  ;RETURN ADDRESS
        JMP  QT2
QT5:    RET                     ;NONE OF ABOVE
;
PRTNUM: MVI  B,0                ;*** PRTNUM ***
        MOV  A,C                ;CHECK SIGN OF C
        ORA  A                  ;NEGATIVE MEANS
        JM  PRTHEX              ;HEXA, ELSE DECIMAL
        CALL CHKSGN             ;CHECK SIGN
        JP   PN1                ;NO SIGN
        MVI  B,'-'              ;B=SIGN
        DCR  C                  ;'-' TAKES SPACE
PN1:    PUSH D                  ;SAVE
        LXI  D,0AH              ;DECIMAL
        PUSH D                  ;SAVE AS A FLAG
        DCR  C                  ;C=SPACES
        PUSH B                  ;SAVE SIGN & SPACE
PN2:    CALL DIVIDE             ;DIVIDE HL BY 10
        MOV  A,B                ;RESULT 0?
        ORA  C
        JZ   PN3                ;YES, WE GOT ALL
        XTHL                    ;NO, SAVE REMAINDER
        DCR  L                  ;AND COUNT SPACE
        PUSH H                  ;HL IS OLD BC
        MOV  H,B                ;MOVE RESULT TO BC
        MOV  L,C
        JMP  PN2                ;AND DIVIDE BY 10
PN3:    POP  B                  ;WE GOT ALL DIGITS IN
PN4:    DCR  C                  ;THE STACK
        MOV  A,C                ;LOOK AT SPACE COUNT
        ORA  A
        JM   PN5                ;NO LEADING BLANKS
        MVI  A,' '              ;LEADING BLANKS
        RST  2
        JMP  PN4                ;MORE?
PN5:    MOV  A,B                ;PRINT SIGN
        ORA  A
        CNZ  OUTC
        MOV  E,L                ;LAST REMAINDER IN E
PN6:    MOV  A,E                ;CHECK DIGIT IN E
        CPI  0AH                ;10 IS FLAG FOR NO MORE
        POP  D
        RZ                      ;IF SO, RETURN
        ADI  '0'                ;ELSE CONVERT TO ASCII
        RST  2                  ;AND PRINT THE DIGIT
        JMP  PN6                ;GO BACK FOR MORE
;
PRTLN:  LDAX D                  ;*** PRTLN ***
        MOV  L,A                ;LOW ORDER LINE #
        INX  D
        LDAX D                  ;HIGH ORDER
        MOV  H,A
        INX  D
        MVI  C,4H               ;PRINT 4 DIGIT LINE #
        CALL PRTNUM
        MVI  A,' '              ;FOLLOWED BY A BLANK
        RST  2
        SUB  A                  ;AND THEN THE NEXT
        CALL PRTSTG
        RET
;
PRTHEX: MOV  A,C                ;*** PRTHEX ***
        CPI  0FEH               ;(-2) TWO DIGIT FORMAT
        JZ   PRTBY              ;ENDS WITH RET INSTR.
        CPI  0FCH               ;(-4) OR FOUR DIGITS
        JZ   PRTWD              ;ENDS WITH RET INSTR.
        MVI  A,' '              ;OR PRINT BLANKS
        RST  2
        INR  C                  ;AND COUNT BLANKS
        JM   PRTHEX             ;AS LONG AS NEGATIVE
        CALL QHOW
;
PRTWD:  MOV  A,H                ;PRINT WORD IN HL
        CALL PBY1               ;PUT OUT FIRST OF TWO
PRTBY:  MOV  A,L                ;PRINT BYTE IN HL(=L)
PBY1:   PUSH PSW                ;SAVE FOR NEXT NIBBLE
        RRC                     ;ROTATE TO RIGHT
        RRC
        RRC
        RRC
        CALL TOCHR              ;CONVERT TO ASCII
        RST  2                  ;PRINT CHAR
        POP  PSW                ;RESTORE AND
        CALL TOCHR              ;CONVERT AGAIN
        RST  2
        RET
;
TOCHR:  ANI  0FH                ;GET LOW NIBBLE
        ADI  '0'                ;FROM HEX TO ASCII
        CPI  '9'+1              ;MORE THAN '9'
        RC                      ;RETURN IF NOT
        ADI  'A'-'9'-1          ;ELSE ADD DIFF TO 'A'
        RET
;
;*************************************************************
;
; *** MVUP *** MVDOWN *** POPA *** & PUSHA ***
;
; 'MVUP' MOVES A BLOCK UP FROM WHERE DE-> TO WHERE BC-> UNTIL
; DE = HL
;
; 'MVDOWN' MOVES A BLOCK DOWN FROM WHERE DE-> TO WHERE HL->
; UNTIL DE = BC
;
; 'POPA' RESTORES THE 'FOR' LOOP VARIABLE SAVE AREA FROM THE
; STACK
;
; 'PUSHA' STACKS THE 'FOR' LOOP VARIABLE SAVE AREA INTO THE
; STACK
;
MVUP:   RST  4                  ;*** MVUP ***
        RZ                      ;DE = HL, RETURN
        LDAX D                  ;GET ONE BYTE
        STAX B                  ;MOVE IT
        INX  D                  ;INCREASE BOTH POINTERS
        INX  B
        JMP  MVUP               ;UNTIL DONE
;
MVDOWN: MOV  A,B                ;*** MVDOWN ***
        SUB  D                  ;TEST IF DE = BC
        JNZ  MD1                ;NO, GO MOVE
        MOV  A,C                ;MAYBE, OTHER BYTE?
        SUB  E
        RZ                      ;YES, RETURN
MD1:    DCX  D                  ;ELSE MOVE A BYTE
        DCX  H                  ;BUT FIRST DECREASE
        LDAX D                  ;BOTH POINTERS AND
        MOV  M,A                ;THEN DO IT
        JMP  MVDOWN             ;LOOP BACK
;
POPA:   POP  B                  ;BC = RETURN ADDR.
        POP  H                  ;RESTORE LOPVAR, BUT
        SHLD LOPVAR             ;=0 MEANS NO MORE
        MOV  A,H
        ORA  L
        JZ   PP1                ;YEP, GO RETURN
        POP  H                  ;NOP, RESTORE OTHERS
        SHLD LOPINC
        POP  H
        SHLD LOPLMT
        POP  H
        SHLD LOPLN
        POP  H
        SHLD LOPPT
PP1:    PUSH B                  ;BC = RETURN ADDR.
        RET
;
PUSHA:  LXI  H,STKLMT           ;*** PUSHA ***
        CALL CHGSGN
        POP  B                  ;BC=RETURN ADDRESS
        DAD  SP                 ;IS STACK NEAR THE TOP?
        CNC  QSORRY             ;YES, SORRY FOR THAT
        LHLD LOPVAR             ;ELSE SAVE LOOP VAR'S
        MOV  A,H                ;BUT IF LOPVAR IS 0
        ORA  L                  ;THAT WILL BE ALL
        JZ   PU1
        LHLD LOPPT              ;ELSE, MORE TO SAVE
        PUSH H
        LHLD LOPLN
        PUSH H
        LHLD LOPLMT
        PUSH H
        LHLD LOPINC
        PUSH H
        LHLD LOPVAR
PU1:    PUSH H
        PUSH B                  ;BC = RETURN ADDR.
        RET
;
;*************************************************************
;
; *** INIT ***
;
; INITIALIZE REQUIRED PERIPHERALS, MEMORY AND OTHER FUNCTIONS
;
;START:  LXI  SP,STACK          ;THIS IS AT LOC. 0
;        MVI  A,80H
INIT:   OUT  DAC                ;PUT OUT HALF VCC ON DAC
        SUB  A                  ;RESET A
        OUT  SELECT             ;RESET D F/F SELECT LINES
        OUT  UARTC              ;PUT 8251 IN COMMAND MODE
        OUT  UARTC              ;WRITE 0 THREE TIMES
        OUT  UARTC
        MVI  A,URESET           ;RESET COMMAND
        OUT  UARTC              ;WRITE IT TO 8251 USART
        MVI  A,USETUP           ;8 DATA, 1 STOP, X16
        OUT  UARTC              ;WRITE IT TO 8251 USART
        MVI  A,UENABL           ;ERRST, RXEN, TXEN
        OUT  UARTC              ;WRITE IT TO 8251 USART
;
ZMEM:   LXI  H,RAMBGN           ;ZERO OUT MEMORY FROM
        LXI  D,STKLMT           ;RAMBEGIN TO STACKLIMIT
ZMEM1:  MVI  M,0
        INX  H
        RST  4                  ;USE RST 4 TO COMPARE
        JNZ  ZMEM1              ;16k LOOP TAKES 305ms
;
        LXI  H,6144             ;INITIATE DEFAULT XTAL[kHz]
        CALL SETXTL             ;START TIMER TO GET INT7.5
        MVI  A,1BH              ;RST F/F & ENABLE INT7.5
        SIM                     ;SET THE NEW MASK
        EI                      ;ENABLE INTERRUPT
;
        LXI  B,EESTRT           ;START ADR IN EEPROM
        LXI  D,2                ;LENGTH TO READ
        LXI  H,RNDNUM           ;WHERE TO STORE IT
        CALL EERD               ;READ THE EEPROM
        LHLD RNDNUM             ;GET THE VALUE AGAIN
        INX  H                  ;INCREMENT AND SAVE
        SHLD RNDNUM             ;THIS VALUE AS NEXT
        LXI  B,EESTRT           ;RANDOM NUMBER SEED
        LXI  D,2                ;IN THIS WAY THE RANDOM
        LXI  H,RNDNUM           ;SEQUENCE WILL NOT
        CALL EEWR               ;REPEAT EVERY POWER ON
;
        CALL ST1                ;MAKE RSTART INITALIZATION
        IN   PORTC              ;BACK DOOR TO ESCAPE FROM
        ANI  18H                ;ROUGE AUTORUN PRG EEPROM
        JZ   CONT               ;BY PRESSING BTNS PC3+PC4
        CALL LD0                ;TRY READ PGM FROM EEPROM
        LXI  D,TXTBGN+6         ;AFTER 2 BYTE LINE NUM
                                ;AND STATEMENT "REM " WE
        LXI  H,TAB10-1          ;MAY FIND TEXT 'AUTORUN'
        JMP  EXEC               ;IF SO RUN THE PROGRAM
;
CONT:   LXI  H,TXTBGN           ;ELSE, DISCARD WHATEVER
        SHLD TXTUNF             ;PGM READ FROM EEPROM
        MVI  A,UENABL+URTS      ;MAKE SHORT BEEP AT START
        OUT  UARTC              ;GETS TURNED OFF AT ST0
        LXI  H,MSG0             ;PRINT THE START MESSAGE
        CALL PSTR
        JMP  ST0
;
PSTR:   MOV  A,M                ;GET A CHARACTER
        INX  H                  ;BUMP POINTER
        ORA  A                  ;CHR IS ZERO?
        RZ                      ;YES, RETURN
        RST  2                  ;ELSE PRINT IT
        JMP  PSTR               ;GET NEXT
;
;*************************************************************
;
; *** OUTC *** & CHKIO ***
;
; THESE ARE THE ONLY I/O ROUTINES IN TBI.
; IT WILL OUTPUT THE BYTE IN A.  IF THAT IS A CR, A LF IS ALSO
; SEND OUT.  ONLY THE FLAGS MAY BE CHANGED AT RETURN. ALL REG.
; ARE RESTORED.
;
; 'CHKIO' CHECKS THE INPUT.  IF NO INPUT, IT WILL RETURN TO
; THE CALLER WITH THE Z FLAG SET.  IF THERE IS INPUT, Z FLAG
; IS CLEARED AND THE INPUT BYTE IS IN A. IF A CONTROL-C IS READ,
; 'CHKIO' WILL RESTART TBI AND DO NOT RETURN TO THE CALLER.
;
;OUTC:  PUSH PSW                ;THIS IS AT LOC. 10
OC3:    IN   UARTC              ;COME HERE TO DO OUTPUT
        ANI  1H                 ;STATUS BIT
        JZ   OC3                ;NOT READY, WAIT
        POP  PSW                ;READY, GET OLD A BACK
        OUT  UARTD              ;AND SEND IT OUT
        CPI  CR                 ;WAS IT CR?
        RNZ                     ;NO, FINISHED
        MVI  A,LF               ;YES, WE SEND LF TOO
        RST  2                  ;THIS IS RECURSIVE
        MVI  A,CR               ;GET CR BACK IN A
        RET
;
INCHR:  CALL CHKIO              ;CHECK IF CHAR RCVD
        JZ   INCHR              ;IF NOT, CHECK AGAIN
        RET                     ;RETURN WITH CHAR
;
CHKIO:  IN   UARTC              ;*** CHKIO ***
        ANI  2H                 ;MASK STATUS BIT
        RZ                      ;NOT READY, RETURN "Z"
        IN   UARTD              ;READY, READ DATA
CI1:    CPI  3H                 ;IS IT CONTROL-C?
        RNZ                     ;NO, RETURN "NZ"
        JMP  CTRLC              ;YES, RESTART TBI
;
;*************************************************************
;
; *** TABLES *** DIRECT *** & EXEC ***
;
; THIS SECTION OF THE CODE TESTS A STRING AGAINST A TABLE.
; WHEN A MATCH IS FOUND, CONTROL IS TRANSFERED TO THE SECTION
; OF CODE ACCORDING TO THE TABLE.
;
; AT 'EXEC', DE SHOULD POINT TO THE STRING AND HL SHOULD POINT
; TO THE TABLE-1.  AT 'DIRECT', DE SHOULD POINT TO THE STRING.
; HL WILL BE SET UP TO POINT TO TAB1-1, WHICH IS THE TABLE OF
; ALL DIRECT AND STATEMENT COMMANDS.
;
; THE TABLE CONSISTS OF ANY NUMBER OF ITEMS.  EACH ITEM
; IS A STRING OF CHARACTERS WITH BIT 7 SET TO 0 AND
; A JUMP ADDRESS STORED HI-LOW WITH BIT 7 OF THE HIGH
; BYTE SET TO 1.
;
; END OF TABLE IS AN ITEM WITH A JUMP ADDRESS ONLY.  IF THE
; STRING DOES NOT MATCH ANY OF THE OTHER ITEMS, IT WILL
; MATCH THIS NULL ITEM AS DEFAULT.
;
TAB1:                           ;DIRECT COMMANDS
        DB   "LIST"
        DWA  LIST
        DB   "RUN"
        DWA  RUN
        DB   "NEW"
        DWA  NEW
        DB   "SAVE"
        DWA  SAVE
        DB   "LOAD"
        DWA  LOAD
        DB   "EDIT"
        DWA  EDIT
        DB   "MAN"
        DWA  MAN
        DB   "?"
        DWA  HELP
;
TAB2:                           ;DIRECT/STATEMENT
        DB   "NEXT"
        DWA  NEXT
        DB   "LET"
        DWA  LET
        DB   "IF"
        DWA  IFF
        DB   "GOTO"
        DWA  GOTO
        DB   "GOSUB"
        DWA  GOSUB
        DB   "RETURN"
        DWA  RETURN
        DB   "FOR"
        DWA  FOR
        DB   "INPUT"
        DWA  INPUT
        DB   "PRINT"
        DWA  PRINT
        DB   "PUTC"
        DWA  PUTC
        DB   "OUT"
        DWA  POUT
        DB   "SOD"
        DWA  SOD
        DB   "POKE"
        DWA  POKE
        DB   "WAIT"
        DWA  WAIT
        DB   "BEEP"
        DWA  BEEP
        DB   "XTAL"
        DWA  XTAL
        DB   "SIGNED"
        DWA  SIGNED
        DB   "UNSIGN"
        DWA  UNSIGN
        DB   "STOP"
        DWA  STOP
        DB   "REM"
        DWA  REM
        DWA  DEFLT
;
TAB4:                           ;FUNCTIONS
        DB   "!"
        DWA  NOT
        DB   "~"
        DWA  INV
        DB   "-"
        DWA  MINUS
        DB   "+"
        DWA  PLUS
        DB   "IN"
        DWA  PIN
        DB   "SID"
        DWA  SID
        DB   "PEEK"
        DWA  PEEK
        DB   "GETC"
        DWA  GETC
        DB   "TIME"
        DWA  TCNT
        DB   "USR"
        DWA  USR
        DB   "RND"
        DWA  RND
        DB   "ABS"
        DWA  ABS
        DB   "LEN"
        DWA  LEN
        DB   "FREE"
        DWA  FREE
        DWA  XP40
;
TAB5:                           ;"TO" IN "FOR"
        DB   "TO"
        DWA  FR1
        DWA  FR9
;
TAB6:                           ;"STEP" IN "FOR"
        DB   "STEP"
        DWA  FR2
        DWA  FR3
;
TAB8:                           ;RELATION OPERATORS
        DB   ">="
        DWA  ROP1
        DB   "!="
        DWA  ROP2
        DB   ">"
        DWA  ROP3
        DB   "<="
        DWA  ROP4
        DB   "=="
        DWA  ROP5
        DB   "<"
        DWA  ROP6
        DWA  ROP7
;
TAB9:                           ;SHIFT OPERATORS
        DB   "<<"
        DWA  XP11
        DB   ">>"
        DWA  XP12
        DWA  XP13
;
TAB10:                          ;FOR AUTORUN DETECT
        DB   "AUTORUN"
        DWA  RUN
        DWA  CONT
;
DIRECT: LXI  H,TAB1-1           ;*** DIRECT ***
;
EXEC:                           ;*** EXEC ***
EX0:    RST  5                  ;IGNORE LEADING BLANKS
        PUSH D                  ;SAVE POINTER
EX1:    LDAX D                  ;GET CAHACTER TO
        INX  D                  ;COMPARE FROM BUFFER
        INX  H                  ;HL->TABLE
        CMP  M                  ;IF MATCH, TEST NEXT
        JZ   EX1
        MVI  A,07FH             ;ELSE SEE IF BIT 7
        DCX  D                  ;OF TABLE IS SET, WHICH
        CMP  M                  ;IS THE JUMP ADDR. (HI)
        JC   EX5                ;C:YES, MATCHED
EX2:    INX  H                  ;NC:NO, FIND JUMP ADDR.
        CMP  M
        JNC  EX2
        INX  H                  ;BUMP TO NEXT TAB. ITEM
        POP  D                  ;RESTORE STRING POINTER
        JMP  EX0                ;TEST AGAINST NEXT ITEM
EX5:    MOV  A,M                ;LOAD HL WITH THE JUMP
        INX  H                  ;ADDRESS FROM THE TABLE
        MOV  L,M
        ANI  7FH                ;MASK OFF BIT 7
        MOV  H,A
        POP  PSW                ;CLEAN UP THE GABAGE
        PCHL                    ;AND WE GO DO IT
;
;*************************************************************
;
; *** SPI IMPLEMENTATION USING SID/SOD AND IO WRITE AS CLK ***
;
; SDOUT AND SDIN ARE SOFTWARE DRIVVEN SERIAL OUTPUT AND INPUT
; FUNCTIONS USING 8085 PINS SOD AND SID FOR DATA TRANSFER AND
; A DUMMY I/O WRITE TO GENERATE CLOCK PULSE. SERIAL DATA OUTPUT
; FREQUENCY IS ABOUT 64KBIT WHEN INCLUDING CALL AND RETURN
; YIELDS A CHARACTER BACK TO BACK TIME OF ABOUT 140 MICROSEC.
; SERIAL DATA INPUT IS SLIGHTLY FASTER. CLK PULSE IS GENERATED
; BY A DUMMY WRITE TO I/O ADDR WHERE THE CHIP SELECT IS NOR'D
; WITH THE WR STROBE TO GENERATE A 460 NANOSEC POSITIVE PULSE.
; CLOCK PULSE IS PROLONGED TO 1700 NANOSEC BY R/C AND LOGIC.
;
SDOUT:  PUSH B                  ;SAVE VALUES IN
        PUSH D                  ;WORKING REGISTERS
        LXI  D,8040H            ;AND & OR MASK IN DE
        MVI  C,8H               ;NUMBER OF BITS
        MOV  B,A                ;STORE BYTE IN B
SDO1:   ANA  D                  ;MASK THE CURRENT BIT
        ORA  E                  ;SET BIT FOR SOD ENABLE
        SIM                     ;WRITE IT TO PIN
        MOV  A,B                ;RESTORE BYTE
        RLC                     ;ROTATE ONE STEP
        MOV  B,A                ;AND SAVE IT
        OUT  SPICLK             ;ISSUE A CLOCK PULSE
        DCR  C                  ;COUNT ITERATIONS
        JNZ  SDO1               ;LOOP IF NOT READY
        MOV  A,E                ;FINISH WITH A '0'
        SIM                     ;WRITE TO PIN
        MOV  A,B                ;RESTORE BYTE
        POP  D
        POP  B
        RET                     ;AND WE'RE DONE
;
SDIN:   PUSH B                  ;SAVE VALUES IN
        PUSH D                  ;WORKING REGISTERS
        MVI  D,80H              ;AND MASK IN D
        LXI  B,0008H            ;TMP STORE & NBR OF BITS
SDI1:   RIM                     ;READ CURRRENT BIT
        OUT  SPICLK             ;ISSUE A CLOCK PULSE
        ANA  D                  ;MASK THE CURRENT BIT
        ORA  B                  ;MERGE WITH PREVIOUS
        RLC                     ;ROTATE ONE STEP
        MOV  B,A                ;AND SAVE IT
        DCR  C                  ;COUNT ITERATIONS
        JNZ  SDI1               ;LOOP IF NOT READY
        POP  D
        POP  B
        RET                     ;AND WE'RE DONE
;
;*************************************************************
;
; *** SPI EEPROM DRIVER ***
;
; ARGUMENTS: EEPROM START ADR [BC], LENGTH [DE], MEM DATAPTR [HL]
;
CSLOW:  MVI  A,UENABL+UDTR      ;** SELECT EEPROM **
        OUT  UARTC              ;WRITE TO PORT
        RET
;
CSHIGH: PUSH PSW                ;** DESELECT EEPROM **
        MVI  A,UENABL           ;MUST SAVE ACKUMULATOR
        OUT  UARTC              ;WHILE SETTING OUTPUT
        POP  PSW                ;RESTORE ACKUMULATOR
        RET
;
CHKWIP: LXI  B,128              ;** WRITE IN PROGRESS **
CHKW1:  CALL CSLOW              ;SELECT EEPROM
        MVI  A,EERDSR           ;OPCODE READ STATUS
        CALL SDOUT              ;TRANSMIT OPCODE
        CALL SDIN               ;READ STATUS
        CALL CSHIGH             ;DESELECT
        ANI  EEWIPB             ;MASK THE BIT
        RZ                      ;ZERO MEANS READY
        DCX  B                  ;ELSE COUNT LOOPS
        JNK  CHKW1              ;AND READ AGAIN
        CALL ASORRY             ;EEPROM NEVER GOT READY
;
EERD:   MOV  A,D                ;** READ EEPROM **
        ORA  E                  ;CHECK FOR ZERO LENGTH
        RZ                      ;SKIP IF SO
        PUSH B                  ;SAVE START ADDR (BC)
        CALL CHKWIP             ;DURING WR.IN.PROGRESS
        POP  B                  ;RESTORE IT
        CALL CSLOW              ;SELECT EEPROM
        MVI  A,EERDDA           ;OPCODE READ DATA
        CALL SDOUT              ;TRANSMIT OPCODE
        MOV  A,B                ;GET ADDRESS HIGH BYTE
        CALL SDOUT              ;TRANSMIT
        MOV  A,C                ;GET ADDRESS LOW BYTE
        CALL SDOUT              ;TRANSMIT
EERD1:  DCX  D                  ;DECREMENT LENGTH
        JK   EERD2              ;FINISH WHEN UNDERFLOW
        CALL SDIN               ;READ ONE BYTE
        MOV  M,A                ;STORE IN RAM
        INX  H                  ;BUMP RAM POINTER
        JMP  EERD1              ;AND LOOP
EERD2:  CALL CSHIGH             ;END OF READ SESSION
        RET
;
EEWRPG: MOV  A,D                ;** WRITE PAGE EEPROM **
        ORA  E                  ;CHECK FOR ZERO LENGTH
        RZ                      ;SKIP IF SO
        PUSH B                  ;SAVE START ADDR (BC)
        CALL CHKWIP             ;DURING WR.IN.PROGRESS
        POP  B                  ;RESTORE IT
        CALL CSLOW              ;SELECT EEPROM
        MVI  A,EEWREN           ;OPCODE WRITE ENABLE
        CALL SDOUT              ;TRANSMIT IT
        CALL CSHIGH             ;DESELECT
        CALL CSLOW              ;SELECT AGAIN
        MVI  A,EEWRDA           ;OPCODE WRITE DATA
        CALL SDOUT              ;TRANSMIT IT
        MOV  A,B                ;GET ADDRESS HIGH BYTE
        CALL SDOUT              ;TRANSMIT
        MOV  A,C                ;GET ADDRESS LOW BYTE
        CALL SDOUT              ;TRANSMIT
EEWR1:  DCX  D                  ;DECREMENT LENGTH
        JK   EEWR2              ;FINISH WHEN UNDERFLOW
        MOV  A,M                ;FETCH FROM RAM
        INX  H                  ;BUMP RAM POINTER
        INX  B                  ;AND NEXT START ADDR
        CALL SDOUT              ;TRANSMIT DATA
        JMP  EEWR1              ;AND LOOP
EEWR2:  CALL CSHIGH             ;END OF WRITE SESSION
        RET
;
EEWR:   PUSH B                  ;SAVE START ADDRESS
        XTHL                    ;SWAP WITH DATAPTR
        SHLD STKLMT+0           ;START ADDRESS @+0
        XCHG                    ;SWAP TOT LEN TO (HL)
        SHLD STKLMT+2           ;TOT LENGTH @+2
        POP  H                  ;GET DATAPTR BACK
        SHLD STKLMT+4           ;DATAPTR @+4
        XCHG                    ;SWAP BACK START ADR
        LXI  D,EEPGSZ           ;GET THE PAGE SIZE
        CALL DIVIDE             ;DIVIDE ADDR/PGSIZE
        XCHG                    ;REMAINDER TO (DE)
        LXI  H,EEPGSZ           ;GET THE PAGE SIZE
        CALL SUBDE              ;SUBTRACT PAGE OFFSET
        XCHG                    ;TO GET REMAINING MAX
        JMP  EEW2               ;LENGTH OF FIRST PAGE
EEW1:   LXI  D,EEPGSZ           ;GET THE PAGE SIZE
EEW2:   LHLD STKLMT+2           ;GET TOT LENGTH
        RST  4                  ;COMPARE (HL - DE)
        JNC  EEW3               ;JMP IF (HL) >= (DE)
        MOV  A,H                ;LESS THAN ONE PAGE
        ORA  L                  ;TO WRITE, SKIP
        RZ                      ;IF NOTHING AT ALL
        MOV  D,H                ;HAVE BYTES TO WRITE
        MOV  E,L                ;PUT LENGTH IN (DE)
EEW3:   CALL SUBDE              ;SUB CHUNK LEN FROM TOT
        SHLD STKLMT+2           ;SAVE REMAINING LENGTH
        LHLD STKLMT+0           ;GET ADDRESS
        MOV  B,H                ;AND TRANSFER
        MOV  C,L                ;IT TO (BC)
        LHLD STKLMT+4           ;GET DATAPTR
        CALL EEWRPG             ;WRITE THIS PAGE
        SHLD STKLMT+4           ;SAVE UPDATED DATAPTR
        MOV  H,B                ;MOVE ADDRESS
        MOV  L,C                ;BACK TO (HL)
        SHLD STKLMT+0           ;SAVE NEW ADDRESS
        JMP  EEW1               ;AND CONTINUE
;
MSG0:   DB   CR
        DB   "    TINY BASIC FOR INTEL 8085"    ,CR
        DB   " LI-CHEN WANG/ROGER RAUSKOLB 1976",CR
        DB   "        ANDERS HJELM 2020"        ,CR
        DB   0
;
MSGHLP: DB   CR
        DB   "CMDS| STATEMENTS  |FUNC|OPERANDS",CR
        DB   "----|-------------|----|--------",CR
        DB   "LIST|FOR TO [STEP]|RND | >   >=",CR
        DB   "RUN |NEXT  IF  LET|ABS | <   <=",CR
        DB   "NEW |INPUT    GOTO|PEEK| ==  !=",CR
        DB   "SAVE|PRINT   GOSUB|IN  |"       ,CR
        DB   "LOAD|PUTC   RETURN|SID |=  +  -",CR
        DB   "EDIT|POKE     WAIT|GETC|*  /  %",CR
        DB   "MAN |OUT      BEEP|TIME|<<   >>",CR
        DB   "?   |SOD      XTAL|USR |"       ,CR
        DB   "    |STOP   SIGNED|LEN | !   ~ ",CR
        DB   "    |REM    UNSIGN|FREE|&  |  ^",CR
        DB   0
;
MSGMAN: DB   CR
        DB   "Tiny Basic for Micro 8085 board"                                  ,CR
        DB   "-------------------------------"                                  ,CR
        DB   "This implementation is based on Palo Alto Tiny Basic."            ,CR
        DB   "Credits to Dr.Li-Chen Wang and Roger Rauskolb, 1976."             ,CR
        DB   "Additions and updates by Anders Hjelm, 2020."                     ,CR
        DB   CR
        DB   "Connect to PC using USB port. Open a terminal emulator, e.g."     ,CR
        DB   "TeraTerm using comm. setup 19200 bps, 8 data bits, no parity."    ,CR
        DB   "Setup a 50 ms delay at end of line for sending BASIC text files." ,CR
        DB   "Board is powered by USB cable. Alt. source is 5VDC from DC plug." ,CR
        DB   CR
        DB   "All numbers are integers. Range is -32768 to 32767 in signed"     ,CR
        DB   "mode, or 0 to 65535 in unsigned mode."                            ,CR
        DB   CR
        DB   "Variables are A through Z and array @(0)..@(N) where N"           ,CR
        DB   "depends on amount of free memory."                                ,CR
        DB   CR
        DB   "Direct commands (type direct at prompt)"                          ,CR
        DB   "---------------"                                                  ,CR
        DB   "LIST [n] Lists all statements (Option from line number)"          ,CR
        DB   "RUN      Execute the current program"                             ,CR
        DB   "NEW      Purge all lines of the current program"                  ,CR
        DB   "SAVE     Save current program to non volatile memory"             ,CR
        DB   "LOAD     Load program from non volatile memory"                   ,CR
        DB   "EDIT n   Edit or change program line with number n"               ,CR
        DB   "MAN      This manual"                                             ,CR
        DB   "?        Short help"                                              ,CR
        DB   CR
        DB   "Most recent typed command can be retrieved by pressing"           ,CR
        DB   "arrow up (or down). Use left/right arrow to move cursor,"         ,CR
        DB   "delete or backspace for corrections, and type new text"           ,CR
        DB   "where needed. EDIT session ends by pressing <Enter>."             ,CR
        DB   CR
        DB   "If the first line of a program which is saved in non volatile"    ,CR
        DB   "memory is 'nn REM AUTORUN', the program will automatically be"    ,CR
        DB   "loaded and executed after power on (nn is line number)."          ,CR
        DB   CR
        DB   "Program execution can be terminated by pressing <Ctrl><C>"        ,CR
        DB   CR
        DB   "Statements (type direct at prompt or put them on a numbered line)",CR
        DB   "----------"                                                       ,CR
        DB   "FOR v=expr TO expr [STEP expr]  Setup a repetitive loop, e.g."    ,CR
        DB   "                                FOR I=1 TO 10 (STEP is optional)" ,CR
        DB   "NEXT v       End delimiter of FOR loop"                           ,CR
        DB   "LET v=expr   Assign a value to a variable, e.g. LET A=2*B"        ,CR
        DB   "IF expr      If expr is true, execute rest of line"               ,CR
        DB   "GOTO expr    Jump to line number pointed out by expr"             ,CR
        DB   "GOSUB expr   Jump to subroutine on line pointed out by expr"      ,CR
        DB   "RETURN            Return from subroutine"                         ,CR
        DB   "INPUT [\"Text\",]v  Lets user input a value to a variable"        ,CR
        DB   "PRINT \"Text\",v    Prints text, values of variables, etc."       ,CR
        DB   "PUTC expr         Prints the ascii char of expr"                  ,CR
        DB   "POKE addr,value   Perform CPU memory write operation"             ,CR
        DB   "OUT addr,value    Perform CPU io write operation"                 ,CR
        DB   "SOD value         Serial output data, SPI bus transmit"           ,CR
        DB   "WAIT expr    Wait/halts execution for expr millisecs"             ,CR
        DB   "BEEP expr    Makes sound with duration expr millisecs"            ,CR
        DB   "XTAL expr    Manipulate the freq.division (default 6144)"         ,CR
        DB   "SIGNED       Set signed mode (default)"                           ,CR
        DB   "UNSIGN       Set unsigned mode (use for time calculations)"       ,CR
        DB   "STOP         Stop execution of program"                           ,CR
        DB   "REM          Use remark for comments"                             ,CR
        DB   CR
        DB   "Print options"                                                    ,CR
        DB   "-------------"                                                    ,CR
        DB   "\"_\" or '_'  Place text between double or single quotes"         ,CR
        DB   "#n  Numbers printed decimal using n positions (default #6)"       ,CR
        DB   "$n  Numbers printed hexadecimal using n pos (must be $2 or more)" ,CR
        DB   "\\b  Print the ascii char of value b"                             ,CR
        DB   " ,  (comma) Argument delimiter."                                  ,CR
        DB   CR
        DB   "e.g. PRINT \"DECIMAL=\",#5,A,\\10,\"HEX=\",$5,A"                  ,CR
        DB   CR
        DB   "Comma at end of PRINT statement means no new line generated"      ,CR
        DB   "$ also used for INPUT of hexadecimal values, e.g. $7FA"           ,CR
        DB   "Single quotes for assignment of ascii value, e.g. A='!'"          ,CR
        DB   "Colon for more statements on same line, e.g.30 PUTC(64) : GOTO 80",CR
        DB   "Parentheses around expressions are optional, use when necessary"  ,CR
        DB   CR
        DB   "Functions (always returns a value)"                               ,CR
        DB   "---------"                                                        ,CR
        DB   "RND expr   A random number between 1 and expr"                    ,CR
        DB   "ABS expr   Absolute value of expr"                                ,CR
        DB   "PEEK addr  Value of CPU memory at addr"                           ,CR
        DB   "IN addr    Value of CPU io read operation"                        ,CR
        DB   "SID        Serial input data, SPI bus read"                       ,CR
        DB   "GETC       ASCII value of most recent pressed key (or zero)"      ,CR
        DB   "TIME       Value of millisec counter (use UNSIGN mode)"           ,CR
        DB   "USR addr[,HL,DE,BC,A]  Call assembler routine on addr"            ,CR
        DB   "                       Option preload CPU registers"              ,CR
        DB   "LEN        Length of current program"                             ,CR
        DB   "FREE       Amount of free memory"                                 ,CR
        DB   CR
        DB   "Arithmetic operands Relational operands Logical operands"         ,CR
        DB   "------------------- ------------------- ----------------"         ,CR
        DB   "  +  Add            >  Greater than        !  Not"                ,CR
        DB   "  -  Subtract       >= Gr. than or equal   ~  Invert"             ,CR
        DB   "  *  Multiply       <  Less than           &  And"                ,CR
        DB   "  /  Division       <= Less than or equal  |  Or"                 ,CR
        DB   "  %  Modulus        == Equal               ^  Xor"                ,CR
        DB   " <<  Left shift     != Not equal"                                 ,CR
        DB   " >>  Right shift"                                                 ,CR
        DB   0
;
BDATE:  DB   "20201231",CR
        DB   0
;
LSTROM: DS   0                  ;ALL ABOVE CAN BE ROM
;
        ORG  8000H              ;HERE DOWN MUST BE RAM
RAMBGN: DS   0
RCVCHR: DS   1                  ;LAST RCVD CHAR IN RUN
DIVOPR: DS   1                  ;TMP STORE DIV OPERATION
PCMCPY: DS   1                  ;PORT COMMAND SHADOW REG
USIGNF: DS   1                  ;UNSIGNED OPERATION FLAG
TIMCNT: DS   2                  ;TIMER INTERRUPT COUNT
CURRNT: DS   2                  ;POINTS TO CURRENT LINE
STKGOS: DS   2                  ;SAVES SP IN 'GOSUB'
VARNXT: DS   2                  ;TEMP STORAGE
STKINP: DS   2                  ;SAVES SP IN 'INPUT'
LOPVAR: DS   2                  ;'FOR' LOOP SAVE AREA
LOPINC: DS   2                  ;INCREMENT
LOPLMT: DS   2                  ;LIMIT
LOPLN:  DS   2                  ;LINE NUMBER
LOPPT:  DS   2                  ;TEXT POINTER
RNDNUM: DS   2                  ;RANDOM NUMBER
TXTUNF: DS   2                  ;->UNFILLED TEXT AREA
TXTBGN: DS   0                  ;TEXT SAVE AREA BEGINS
;                               ;WHERE BASIC PGM IS STORED
;                               ;MEMORY ABOVE TXTUNF HOLDS
;                               ;@(n),@(n-1),..,@(2),@(1)
        ORG  0BF00H             ;RESERVE 54+74+128 BYTE
TXTEND: DS   0                  ;TEXT SAVE AREA ENDS
VARBGN: DS   54                 ;VARIABLE @(0),A,B,..,Z
BUFFER: DS   74                 ;INPUT BUFFER
BUFEND: DS   0                  ;BUFFER ENDS
STKLMT: DS   0                  ;AND MEETS STACK LIMIT
;                               ;MAKES ROOM FOR 128 BYTE
        ORG  0C000H             ;STACK STARTS HERE AND
STACK:  DS   0                  ;GROWS TOWARDS LOWER ADDR
XRAM:   DS   16384              ;NOT HANDLED BY TINY BASIC
;
; *** COMMUNICATION ASCII CONSTATNTS ***
CR      EQU  0DH
LF      EQU  0AH
BS      EQU  08H
ESC     EQU  1BH
;
; *** IO PORT MAP AND RELATED DEFINES ***
PCMD    EQU  00H
PORTA   EQU  01H
PORTB   EQU  02H
PORTC   EQU  03H
PTIML   EQU  04H
PTIMH   EQU  05H
;
UARTD   EQU  10H
UARTC   EQU  11H
URESET  EQU  01000000b          ;RESET COMMAND
USETUP  EQU  01001110b          ;8 DATA, 1 STOP, X16
UENABL  EQU  00010101b          ; - ,ERRST,RXEN, - ,TXEN
UDTR    EQU  00000010b          ; - ,  -  , -  ,DTR, -
URTS    EQU  00100000b          ;RTS,  -  , -  , - , -
;
SPICLK  EQU  20H
SELECT  EQU  30H
;
ADC1    EQU  40H                ;ADC CONV.TIME 140 MICROSEC
ADC2    EQU  50H                ;OK TO USE CONSECUTIVE BASIC
DAC     EQU  60H                ;OUT(WRITE/START) THEN IN(READ)
;
; *** SERIAL EEPROM COMMANDS AND SIZE ***
EEWREN  EQU  6H
EERDSR  EQU  5H
EEWRDI  EQU  4H
EERDDA  EQU  3H
EEWRDA  EQU  2H
EEWRSR  EQU  1H
EEWIPB  EQU  1H
EESTRT  EQU  0
EEPGSZ  EQU  64
EESIZE  EQU  32768
;
        END
