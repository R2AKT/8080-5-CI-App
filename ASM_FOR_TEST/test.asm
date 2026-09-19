.org 0
        
        call calc
	push d
        mvi a, 80h
        out 0f8h
        call calc
        push d
        call 0f82dh
        pop d
        call pr_d
        mvi c, 20h
        call 0f809h
        pop d
        call pr_d
        hlt

calc:
        lxi d, 0

        in 0e1h
w1:
        in 0e1h
        ani 20h
        jz w1
w2:
        in 0e1h
        inx d
        ani 20h
        jz w2

        ret

pr_d:
        mov a, d
        call 0f815h
        mov a, e
        call 0f815h

        ret
.end
