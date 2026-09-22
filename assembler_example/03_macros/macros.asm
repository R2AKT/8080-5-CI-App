; ============================================================
;  macros.asm — макросы, REPT, условная сборка
;
;  Демонстрирует: MACRO/ENDM с параметрами, вложенные макросы,
;  префиксы параметров (&), REPT/ENDM, #if/#else/#endif.
; ============================================================
        ORG 0x0100

        #define PORT 0x01

; --- Макрос с параметром: вывод символа в порт ---
        PUTCHAR MACRO CH
                MVI A, CH
                OUT PORT
        ENDM

; --- Макрос: записать 16-битное значение по адресу ---
        STORE16 MACRO ADDR, VAL
                LXI H, ADDR
                LXI D, VAL
                MOV M, E
                INX H
                MOV M, D
        ENDM

; --- Вложенные макросы (OUTER вызывает INNER) ---
        INNER MACRO
                NOP
        ENDM
        OUTER MACRO
                INNER
                NOP
        ENDM

; --- Макрос с префиксом параметра & ---
        DBPAIR MACRO V
                DB &V, &V
        ENDM

; --- Вызовы макросов ---
        PUTCHAR 'X'
        PUTCHAR 'Y'
        STORE16 0x0200, 0x1234
        OUTER
        DBPAIR 0x55

; --- REPT: повторение блока (3 одинаковые копии) ---
        REPT 3
                NOP
        ENDM

; --- Условная сборка ---
        #define DEBUG 1
        #if DEBUG
        DB "DEBUG"
        #else
        DB "RELEASE"
        #endif

        HLT
