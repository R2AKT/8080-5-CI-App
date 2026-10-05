; ============================================================
;  directives.asm — демонстрация всех директив ассемблера
;
;  Показывает: ORG, EQU, #define, #include, #path,
;  #if/#elif/#else/#endif, MACRO/ENDM, REPT/ENDM,
;  DB, DW, DS, метки (локальные и глобальные), HLT.
; ============================================================
        ORG 0x0100

; --- #define: константы препроцессора (подстановка текста) ---
        #define PORT_OUT 0x01
        #define VERSION  2

; --- EQU: константы ассемблера (вычисляются, могут ссылаться на другие) ---
        BASE      EQU 0x0200
        BUF_SIZE  EQU 16
        BUF_END   EQU BASE + BUF_SIZE

; --- #include: подключение файла из того же каталога ---
        #include "defs.inc"

; --- #path: добавить каталог поиска, затем #include из него ---
        #path "inc"
        #include "extra.inc"

; --- #if / #elif / #else / #endif: условная сборка ---
        #if VERSION >= 2
        DB "v2"
        #elif VERSION >= 1
        DB "v1"
        #else
        DB "v0"
        #endif

; --- MACRO / ENDM: параметризованный макрос ---
        PUTCHAR MACRO CH
                MVI A, CH
                OUT PORT_OUT
        ENDM

        PUTCHAR 'A'
        PUTCHAR 'B'

; --- REPT / ENDM: повторение блока ---
        REPT 3
                DB 0xAA
        ENDM

; --- DB: байты, строки, выражения ---
        DB 0x11, 0x22, 0x33
        DB "DATA"
        DB 1 + 2, 4 * 5

; --- DW: 16-битные слова (little-endian) ---
        DW 0x1234, 0x5678

; --- DS: зарезервировать пространство (заполняется 0) ---
        DS 8

; --- метки: локальная (:) и глобальная (::) ---
local_label:
        NOP
global_label::
        NOP

        HLT
