STEC:   .equ     0F7FFH
EKRAN:  .equ     0E800H
CURSOR: .equ     0E000H
WRK:    .equ     0F750H
RWRK:   .equ     WRK+1FH
ABUF:   .equ     WRK+15H
BUF:    .equ     WRK+70H
WORK:   .equ     WRK+2BH
REGP:   .equ     0E77CH
SREG:   .equ     WRK+0ADH
PORT0:  .equ     0
PORT1:  .equ     1
PORT2:  .equ     2
PORT3:  .equ     3
PORT4:  .equ     4
PORT5:  .equ     5
PORT6:  .equ     6
PORT7:  .equ     7
CR:     .equ     0DH
LF:     .equ     0AH
        .org     0F800H
        JMP     START
        JMP     CI
        JMP     MI
        JMP     CO
        JMP     MO
        JMP     CO
        JMP     STAT
        JMP     D16
        JMP     DISSO
START:  LXI     H,BUF
        SHLD    ABUF
        LXI     SP,STEC
        MVI     A,1FH
        CALL    DIS
BEGIN:  MVI     A,8BH
        OUT     PORT4
        LXI     SP,STEC
        LXI     H,SOOB
        CALL    DISSO
        CALL    RADR
        LXI     H,BEGIN
        PUSH    H
BEG1:   LXI     H,WORK
        MOV     B,M
        LXI     H,TBL
LOOP:   MOV     A,M
        ANA     A
        JZ      ERROR
        CMP     B
        JZ      JOB
        INX     H
        INX     H
        INX     H
        JMP     LOOP
JOB:    INX     H
        SPHL
        POP     H
        LXI     SP,SREG
        PCHL
;
RADR:   LXI     H,WORK
RAD:    CALL    CI
        CPI     8
        JZ      DELE
        CNZ     DIS
        MOV     M,A
        CPI     CR
        JZ      BKK
        MVI     A,9AH
        CMP     L
        INX     H
        JNZ     RAD
ERROR:  MVI     A,3FH
        CALL    DIS
        JMP     BEGIN
BKK:    MVI     M,CR
        RET
;
DELE:   CALL    DELET
        JMP     RAD
;
DELET:  MVI     A,7BH
        CMP     L
        RZ
        MVI     A,8
        CALL    DIS
        DCX     H
        RET
;
PV:     CALL    PROB
        LXI     H,WORK
PVV0:   MVI     B,0
PVV:    CALL    CI
        CPI     8
        JZ      OGR
        CNZ     DIS
        MOV     M,A
        CPI     ' '
        JZ      SPACE
        CPI     CR
        JZ      BK
        MVI     B,0FFH
        MVI     A,9AH
        CMP     L
        JZ      ERROR
        INX     H
        JMP     PVV
;
SPACE:  MVI     M,CR
        MOV     A,B
        RAL
        LXI     D,WORK
        MVI     B,0
        RET
;
OGR:    CALL    DELET
        JZ      PVV0
        JMP     PVV
;
BK:     INX     SP
        INX     SP
        RET
;
DISSOOB:LXI     H,CRLF
DISSO:  MOV     A,M
        ANA     A
        RZ
        CALL    DIS
        INX     H
        JMP     DISSO
;
ADRES:  LXI     H,WRK+1
        MVI     B,6
        XRA     A
LIP:    MOV     M,A
        DCR     B
        JNZ     LIP
        LXI     D,RWRK+0DH
        CALL    OBADR
        SHLD    WRK+1
        SHLD    WRK+3
        RC
        CALL    OBADR
        SHLD    WRK+3
        PUSH    PSW
        PUSH    D
        XCHG
        LHLD    WRK+1
        XCHG
        CALL    HILO1
        JC      ERROR
        POP     D
        POP     PSW
        RC
        CALL    OBADR
        SHLD    WRK+5
        RC
        JMP     ERROR
;
OBADR:  LXI     H,0
FSP:    LDAX    D
        INX     D
        CPI     CR
        JZ      FBK
        CPI     ','
        RZ
        CPI     ' '
        JZ      FSP
        SUI     '0'
        JM      ERROR
        CPI     LF
        JM      FLF
        CPI     11H
        JM      ERROR
        CPI     17H
        JP      ERROR
        SUI     7
FLF:    MOV     C,A
        DAD     H
        DAD     H
        DAD     H
        DAD     H
        JC      ERROR
        DAD     B
        JMP     FSP
FBK:    STC
        RET
;
AD16:   LHLD    WRK+1
        MOV     A,M
D16:    MOV     B,A
        MOV     A,B
        RRC
        RRC
        RRC
        RRC
        CALL    CD16
        MOV     A,B
CD16:   ANI     0FH
        CPI     0AH
        JM      MD16
        ADI     7
MD16:   ADI     30H
        JMP     DIS
MD161:  CALL    DISSOOB
        LXI     H,WRK+2
ADR16:  MOV     A,M
        CALL    D16
        DCX     H
        MOV     A,M
        CALL    D16
PROB:   MVI     A,' '
        JMP     DIS
;
HILO:   PUSH    D
        LHLD    WRK+1
        XCHG
        LHLD    WRK+3
        CALL    HILO1
        POP     D
        JZ      BK
        LXI     H,WRK+1
HIL:    INR     M
        RNZ
        INX     H
        INR     M
        RET
;
HILO1:  MOV     A,H
        CMP     D
        RNZ
        MOV     A,L
        CMP     E
        RET
;
XREG:   LXI     H,RWRK+0DH
        MOV     A,M
        CPI     CR
        JZ      MBK
        CPI     'S'
        JZ      S
        LXI     D,DIR
        CALL    ADRS
        LXI     H,ABUF
        INX     D
        LDAX    D
        MOV     L,A
        PUSH    H
        CALL    PROB
        MOV     A,M
        CALL    D16
        CALL    PV
        JNC     BEGIN
        CALL    OBADR
        MOV     A,L
        POP     H
        MOV     M,A
        RET
S:      CALL    PROB
        LXI     H,ABUF+1
        CALL    ADR16
        CALL    PV
        JNC     BEGIN
        CALL    OBADR
        SHLD    ABUF
        RET
;
ADRS:   LDAX    D
        ANA     A
        JZ      ERROR
        CMP     M
        RZ
        INX     D
        INX     D
        JMP     ADRS
MBK:    LXI     D,DIR
        MVI     B,8
        CALL    DISSOOB
MB1:    LDAX    D
        MOV     C,A
        INX     D
        PUSH    B
        CALL    RAZD
        LDAX    D
        LXI     H,ABUF
        MOV     L,A
        MOV     A,M
        CALL    D16
        POP     B
        INX     D
        DCR     B
        JNZ     MB1
        LDAX    D
        MOV     C,A
        CALL    RAZD
        LHLD    ABUF
        SHLD    WRK+1
        CALL    ADR16-3
        MVI     C,'O'
        CALL    RAZD
        LXI     H,WRK+20H
        CALL    ADR16
        JMP     DISSOOB
;
RAZD:   CALL    PROB
        MOV     A,C
        CALL    DIS
        MVI     A,'-'
        JMP     DIS
;
DIR:    .db      'A',68H
        .db      'B',6AH
        .db      'C',69H
        .db      'D',6CH
        .db      'E',6BH
        .db      'F',67H
        .db      'H',6EH
        .db      'L',6DH
        .db      'S',65H,0
;
SBS:    .db      LF
	.text	"START-"
	.db	0
SBD:    .db      LF
	.text	"DIR. -"
	.db	0
BASTR:  CALL    ADRES
        CALL    OST
        LHLD    WRK+1
        MOV     A,M
        MVI     M,0FFH
        SHLD    RWRK+3
        STA     RWRK+5
        RET
;
OST:    MVI     A,0C3H
        STA     038H
        LXI     H,WOST
        SHLD    39H
        RET
;
WOST:   SHLD    RWRK-2
        PUSH    PSW
        LXI     H,4
        DAD     SP
        SHLD    ABUF
        POP     PSW
        XTHL
        DCX     H
        XTHL
        LXI     SP,RWRK-2
        PUSH    D
        PUSH    B
        PUSH    PSW
        LXI     SP,STEC
        LHLD    ABUF
        DCX     H
        MOV     D,M
        DCX     H
        MOV     E,M
        MOV     L,E
        MOV     H,D
        SHLD    RWRK
        LHLD    RWRK+3
        CALL    HILO1
        JZ      WOS
        LHLD    RWRK+6
        CALL    HILO1
        JZ      POT
        LHLD    RWRK+09H
        CALL    HILO1
        JZ      POT1
        JMP     ERROR
WOS:    LDA     RWRK+5
        MOV     M,A
        LXI     H,0FFFFH
        SHLD    RWRK+3
        JMP     BEGIN
;
GO:     CALL    ADRES
        LDA     RWRK+0DH
        CPI     CR
        JNZ     GO1
        LHLD    RWRK
        SHLD    WRK+1
GO1:    MVI     A,0C3H
        STA     WRK
        LXI     SP,ABUF
        POP     H
        POP     PSW
        POP     B
        POP     D
        SPHL
        LHLD    RWRK-2
        JMP     WRK
;
POTL:   CALL    ADRES
        CALL    OST
        LHLD    WRK+1
        SHLD    RWRK+6
        MOV     A,M
        MVI     M,0FFH
        STA     RWRK+08H
        LHLD    WRK+3
        SHLD    RWRK+09H
        MOV     A,M
        MVI     M,0FFH
        STA     RWRK+0BH
        LDA     WRK+5
        STA     RWRK+2
        LXI     H,SBS
        CALL    DISSO
        LXI     H,RWRK+0DH
        CALL    RAD
        CALL    ADRES
        LXI     H,SBD
        CALL    DISSO
        CALL    RADR
        JMP     GO1
POT:    LDA     RWRK+8
        MOV     M,A
        LHLD    RWRK+09H
        MVI     A,0FFH
        CMP     M
        JZ      POT0
        MOV     B,M
        MOV     M,A
        MOV     A,B
        STA     RWRK+0BH
POT0:   CALL    MBK
        CALL    BEG1
        LHLD    RWRK
        SHLD    WRK+1
        JMP     GO1
POT1:   LDA     RWRK+0BH
        MOV     M,A
        LHLD    RWRK+6
        MVI     A,0FFH
        CMP     M
        JZ      POT0
        MOV     B,M
        MOV     M,A
        MOV     A,B
        STA     RWRK+8
        LXI     H,RWRK+2
        DCR     M
        JNZ     POT0
        LDA     RWRK+8
        LHLD    RWRK+6
        MOV     M,A
        JMP     BEGIN
;
DISPL:  CALL    ADRES
        CALL    DISSOOB
DIPL1:  CALL    MD161
IPL2:   CALL    PROB
        CALL    AD16
        CALL    HILO
        LDA     WRK+1
        ANI     0FH
        JZ      DIPL1
        JMP     IPL2
;
CREF:   CALL    ADRES
        LHLD    WRK+5
        XCHG
CRE:    LHLD    WRK+1
        LDAX    D
        CMP     M
        JZ      CRE1
        CALL    MD161
        CALL    PROB
        CALL    AD16
        CALL    PROB
        LDAX    D
        CALL    D16
CRE1:   INX     D
        CALL    HILO
        JMP     CRE
;
FMEM:   CALL    ADRES
        LDA     WRK+5
        MOV     B,A
FM:     LHLD    WRK+1
        MOV     M,B
        CALL    HILO
        JMP     FM
;
SBAIT:  CALL    ADRES
        MOV     C,L
SB:     LHLD    WRK+1
        MOV     A,C
        CMP     M
        CZ      MD161
        CALL    HILO
        JMP     SB
;
TMEM:   CALL    ADRES
        LHLD    WRK+5
        XCHG
TM:     LHLD    WRK+1
        MOV     A,M
        STAX    D
        INX     D
        CALL    HILO
        JMP     TM
;
MEMOR:  CALL    ADRES
MEM:    CALL    PROB
        CALL    AD16
        CALL    PV
        JNC     MEM1
        CALL    OBADR
        MOV     A,L
        LHLD    WRK+1
        MOV     M,A
MEM1:   LXI     H,WRK+1
        CALL    HIL
        CALL    MD161
        JMP     MEM
;
JOBS:   CALL    ADRES
        LHLD    WRK+1
        PCHL
;
MA:     CALL    DISSOOB
        LDA     RWRK+0DH
        CALL    D16
        JMP     DISSOOB
;
KLB:    CALL    CI
        CPI     1
        JZ      BEGIN
        CALL    DIS
        JMP     KLB
;
QMEM:   CALL    ADRES
QM:     LHLD    WRK+1
        MOV     C,M
        MVI     A,55H
        MOV     M,A
        CMP     M
        CNZ     QM1
        MVI     A,0AAH
        MOV     M,A
        CMP     M
        CNZ     QM1
        MOV     M,C
        CALL    HILO
        JMP     QM
QM1:    PUSH    PSW
        CALL    MD161
        CALL    PROB
        CALL    AD16
        CALL    PROB
        POP     PSW
        CALL    D16
        RET
;
LMEM:   CALL    ADRES
        CALL    DISSOOB
LM0:    CALL    MD161
LM:     CALL    PROB
        LHLD    WRK+1
        MOV     A,M
        CPI     20H
        JC      LM1
        CPI     80H
        JNC     LM1
        JMP     LM2
LM1:    MVI     A,'.'
LM2:    CALL    DIS
        CALL    HILO
        LDA     WRK+1
        ANI     0FH
        JZ      LM0
        JMP     LM
;
HEX:    LXI     H,WRK+1
        MVI     B,6
        XRA     A
HE1:    MOV     M,A
        DCR     B
        JNZ     HE1
        LXI     D,RWRK+0DH
        CALL    OBADR
        SHLD    WRK+1
        CALL    OBADR
        SHLD    WRK+3
        CALL    DISSOOB
        LHLD    WRK+1
        SHLD    WRK+5
        XCHG
        LHLD    WRK+3
        DAD     D
        SHLD    WRK+1
        CALL    MD161+3
        LHLD    WRK+3
        XCHG
        LHLD    WRK+5
        MOV     A,E
        CMA
        MOV     E,A
        MOV     A,D
        CMA
        MOV     D,A
        INX     D
        DAD     D
        SHLD    WRK+1
        CALL    MD161+3
        JMP     DISSOOB
;
INPUT:  MVI     A,0FFH
        CALL    MI
        STA     WRK+2
        STA     WRK+0FH
        MVI     A,8
        CALL    MI
        STA     WRK+1
        STA     WRK+0EH
        MVI     A,8
        CALL    MI
        STA     WRK+4
        STA     WRK+11H
        MVI     A,8
        CALL    MI
        STA     WRK+3
        STA     WRK+10H
        MVI     A,8
        LXI     H,IN3
        PUSH    H
INP1:   LHLD    WRK+1
        CALL    MI
        MOV     M,A
        CALL    HILO
        MVI     A,8
        JMP     INP1
IN3:    LXI     H,WRK+0FH
        CALL    ADR16
        LXI     H,WRK+11H
        CALL    ADR16
        JMP     DISSOOB
;
OUTPUT: CALL    ADRES
        XRA     A
        MVI     B,0
OU1:    CALL    MO
        DCR     B
        JNZ     OU1
        MVI     A,0E6H
        CALL    MO
        LDA     WRK+2
        CALL    MO
        LDA     WRK+1
        CALL    MO
        LDA     WRK+4
        CALL    MO
        LDA     WRK+3
        CALL    MO
OU2:    LHLD    WRK+1
        MOV     A,M
        CALL    MO
        CALL    HILO
        JMP     OU2
;
VERIFI: MVI     A,0FFH
        CALL    MI
        STA     WRK+2
        MVI     A,8
        CALL    MI
        STA     WRK+1
        MVI     A,8
        CALL    MI
        STA     WRK+4
        MVI     A,8
        CALL    MI
        STA     WRK+3
VER0:   MVI     A,8
        CALL    MI
        LHLD    WRK+1
        CMP     M
        JZ      VER1
        PUSH    PSW
        CALL    MD161
        CALL    PROB
        CALL    AD16
        CALL    PROB
        POP     PSW
        CALL    D16
VER1:   CALL    HILO
        JMP     VER0
;
MI:     PUSH    B
        PUSH    D
        MVI     C,0
        MOV     D,A
        IN      PORT1
        MOV     E,A
MI0:    MOV     A,C
        ANI     7FH
        RLC
        MOV     C,A
MI1:    IN      PORT1
        CMP     E
        JZ      MI1
        ANI     1
        ORA     C
        MOV     C,A
        CALL    DELAY7
        IN      PORT1
        MOV     E,A
        MOV     A,D
        ORA     A
        JP      MI5
        MOV     A,C
        CPI     0E6H
        JNZ     MI4
        XRA     A
        STA     WRK+7
        JMP     MI3
MI4:    CPI     19H
        JNZ     MI0
        MVI     A,0FFH
        STA     WRK+7
MI3:    MVI     D,9
MI5:    DCR     D
        JNZ     MI0
        LDA     WRK+7
        XRA     C
        POP     D
        POP     B
        RET
;
DELAY7: PUSH    PSW
        LDA     WRK+0CH
DELY33: MOV     B,A
        POP     PSW
DELY:   DCR     B
        JNZ     DELY
        RET
;
MO:     PUSH    B
        PUSH    D
        PUSH    PSW
        MOV     D,A
        MVI     C,8
MO0:    MOV     A,D
        RLC
        MOV     D,A
        MVI     A,1
        XRA     D
        OUT     PORT1
        CALL    DELY5
        MVI     A,0
        XRA     D
        OUT     PORT1
        CALL    DELY5
        DCR     C
        JNZ     MO0
        POP     PSW
        POP     D
        POP     B
        RET
;
DELY5:  PUSH    PSW
        LDA     WRK+0DH
        JMP     DELY33
;
TBL:    .db      'M'
        .dw      MEMOR
        .db      'C'
        .dw      CREF
        .db      'D'
        .dw      DISPL
        .db      'B'
        .dw      BASTR
        .db      'G'
        .dw      GO
        .db      'P'
        .dw      POTL
        .db      'X'
        .dw      XREG
        .db      'F'
        .dw      FMEM
        .db      'S'
        .dw      SBAIT
        .db      'T'
        .dw      TMEM
        .db      'I'
        .dw      INPUT
        .db      'O'
        .dw      OUTPUT
        .db      'V'
        .dw      VERIFI
        .db      'J'
        .dw      JOBS
        .db      'A'
        .dw      MA
        .db      'K'
        .dw      KLB
        .db      'Q'
        .dw      QMEM
        .db      'L'
        .dw      LMEM
        .db      'H'
        .dw      HEX
        .db      0
SOOB:   .db      LF
	.text	"*åàäêé/80* åéçàíéê"
	.db	LF,3EH,0
CRLF:   .db      LF,0
DIS:    PUSH    H
        PUSH    B
        PUSH    D
        PUSH    PSW
        MOV     C,A
        JMP     DI1
CO:     PUSH    H
        PUSH    B
        PUSH    D
        PUSH    PSW
DI1:    LHLD    WRK+0AH
        LXI     D,0F801H
        DAD     D
        MVI     M,0
        LHLD    WRK+0AH
        MOV     A,C
        CPI     1FH
        JZ      CTR
        CPI     8
        JZ      LEV
        CPI     18H
        JZ      PRAV
        CPI     19H
        JZ      VERX
        CPI     1AH
        JZ      VNIZ
        CPI     LF
        JZ      DLF
        CPI     0CH
        JZ      HOME
        MOV     A,H
        CPI     0F0H
        JNZ     NEP
        CALL    STAT
        ORA     A
        JZ      ECT
        CALL    CI
ECT:    CALL    CLEAR
        LXI     H,EKRAN
NEP:    MOV     M,C
        INX     H
OKON:   SHLD       WRK+0AH
        LXI     D,0F801H
        DAD     D
        MVI     M,80H
        POP     PSW
        POP     D
        POP     B
        POP     H
        RET
CTR:    CALL    CLEAR
HOME:   LXI     H,EKRAN
        JMP     OKON
CLEAR:  LXI     H,EKRAN
        LXI     D,CURSOR
CLE1:   MVI     M,' '
        INX     H
        MVI     A,0
        STAX    D
        INX     D
        MOV     A,H
        CPI     0F0H
        RZ
        JMP     CLE1
PRAV:   INX     H
        MOV     A,H
        CPI     0F0H
        JNZ     OKON
        JZ      HOME
LEV:    DCX     H
        MOV     A,H
        CPI     0E7H
        JNZ     OKON
        LXI     H,0EFFFH
        JMP     OKON
VNIZ:   LXI     D,40H
        DAD     D
        MOV     A,H
        CPI     0F0H
        JNZ     OKON
        MVI     H,0E8H
        JMP     OKON
VERX:   LXI     D,0FFC0H
        DAD     D
        MOV     A,H
        CPI     0E7H
        JNZ     OKON
        LXI     D,800H
        DAD     D
        JMP     OKON
DLF:    INX     H
        MOV     A,L
        ORA     A
        JZ      DLF1
        CPI     40H
        JZ      DLF1
        CPI     80H
        JZ      DLF1
        CPI     0C0H
        JZ      DLF1
        JMP     DLF
DLF1:   MOV     A,H
        CPI     0F0H
        JNZ     OKON
        CALL    STAT
        ORA     A
        JZ      CTR
        CALL    CI
        JMP     CTR
;
CI:     PUSH    B
        PUSH    D
        PUSH    H
CI0:    MVI     B,0
        MVI     C,0FEH
        MVI     D,8
CI2:    MOV     A,C
        OUT     PORT7
        RLC
        MOV     C,A
        IN      PORT6
        ANI     7FH
        CPI     7FH
        JNZ     CI1
        MOV     A,B
        ADI     7
        MOV     B,A
        DCR     D
        JNZ     CI2
        JMP     CI0
CI1:    STA     WRK+14H
        RAR
        JNC     CI3
        INR     B
        JMP     CI1+3
CI3:    MOV     A,B
        CPI     '0'
        JNC     CI4
        ADI     '0'
        CPI     3CH
        JC      CI5
        CPI     40H
        JNC     CI5
        ANI     2FH
CI5:    MOV     C,A
        JMP     CI6
CI4:    LXI     H,TBLK
        SUI     30H
        MOV     C,A
        MVI     B,0
        DAD     B
        MOV     A,M
        JMP     CI7
CI6:    IN      PORT5
        ANI     7H
        CPI     7
        JZ      CI8
        RAR     
        RAR
        JNC     CI9
        RAR
        JNC     CI10
        MOV     A,C
        ORI     20H
        JMP     CI7
CI9:    MOV     A,C
        ANI     1FH
        JMP     CI7
CI10:   MOV     A,C
        CPI     40H
        JNC     CI7
        CPI     30H
        JNC     CI11
        ORI     10H
        JMP     CI7
CI11:   ANI     2FH
        JMP     CI7
CI8:    MOV     A,C
CI7:    MOV     C,A
        CALL    CDELY
        LXI     H,WRK+14H
CI12:   IN      PORT6
        CMP     M
        JZ      CI12
        CALL    CDELY
        MOV     A,C
        POP     H
        POP     D
        POP     B
        RET
;
CDELY:  LXI     D,1000H
CDE:    DCX     D
        MOV     A,D
        ORA     E
        RZ
        JMP     CDE
;
TBLK:   .db      20H,18H,8,19H,1AH,CR,1FH,0CH
;
STAT:   MVI     A,0
        OUT     PORT7
        IN      PORT6
        ANI     7FH
        CPI     7FH
        JNZ     MIMO
        XRA     A
        RET
MIMO:   MVI     A,0FFH
        RET
	.end
