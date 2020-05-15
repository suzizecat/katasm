$LIM = 2
$CNT = 1
nop
wrl $CNT 0
wrl $LIM 2
:start
    incr $CNT
    atr  $CNT
    nger $CNT $LIM
cjmpl :start
wrl $LIM 0
:part2
    decr $CNT
    atr  $CNT
    gtr  $CNT $LIM
cjmpl :part2
halt
nop 