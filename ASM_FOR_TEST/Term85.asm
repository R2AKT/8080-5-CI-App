PUBLIC	BRID, COR, CIR, CIN_T, STRPS


;TITLE('8085 Вывод/ввод на терминал и кассетный магнитофон')
;    .area   PG0
    SECTION   kp04_DOP
module     Terminal

;Эта программа и подпрограммы подробно описаны в приложении
;АР-29 "Использование в 8085 выводов последовательного ввода/вывода"
;В первой секции главная программа интерфейса с дисплеем с автоматическим
;определением скорости обмена. Во второй секции интерфейс с магнитной лентой
;для запминания данных на кассетной ленте. Коды начинаются с 800Н и
;являются частью ПЗУ расширения в SDK-85.
;
BitSO       equ   11   ;Данные битов для вывода включая 2 стоповых
BitSI       equ   9   ;Даные битов для приема включая 1 стоповый
;
;
;BRID подпрограмма определения скорости
BRID:
   RIM                  ;Монитор SID состояние
   ORA      A
   JP       BRID
BRI1:
   RIM
   ORA      A
   JM       BRI1
   LXI      H,-6           ;для использования счетчиком
BRI3:
   MVI      E,04
BRI4:
   DCR      E
   JNZ      BRI4
   INX      H
   RIM
   ORA      A
   JP       BRI3
   PUSH     H
   INR      H
   INR      L
   SHLD     BitTime
   POP      H
   ORA      A
   MOV      A,H
   RAR                  ;делим на 2
   MOV      H,A
   MOV      A,L
   RAR
   MOV      L,A
   INR      H
   INR      L
   SHLD     HalfBit
   RET
;
;COUT программа вывода на консоль
; Выводимый символ в C
;
COR:
    mov     c,a
COUT_T::
   DI
   PUSH     B
   PUSH     H
   MVI      B,BitSO          ;Устанавливает число бит для передачи
   XRA      A
co1:
   MVI     A,80h           ;Установит разарешение бита
   RAR
   SIM
   LHLD     BitTime
co2:
   DCR      L
   JNZ      co2
   DCR      H
   JNZ      co2
   STC
   MOV      A,C
   RAR
   MOV      C,A
   DCR      B
   JNZ      co1
   POP      H
   POP      B
   EI
   RET
;
;CIN   Подпрограмма ввода с консоли
; Введенный символ в C
;
CIR:
CIN_T:
   DI
   PUSH     H
   MVI      B,BitSI
ci1:
   RIM
   ORA      A
   JM       ci1
   LHLD     HalfBit
ci2:
   DCR      L
   JNZ      ci2
   DCR      H
   JNZ      ci2
ci3:
   LHLD     BitTime
ci4:
   DCR      L
   JNZ      ci4
   DCR      H
   JNZ      ci4
   RIM
   RAL
   DCR      B
   JZ       ci5
   MOV      A,C
   RAR
   MOV      C,A
   NOP
   JMP      ci3
ci5:
   POP      H
   mov      a,c
   EI   
   RET

STRPS:
	mvi 	a,0ffh
	ret

BitTime:           DEFS    2      ; Адрес для вычисления задержки бита
HalfBit:           DEFS    2      ; Адрес для задерки половина бита


