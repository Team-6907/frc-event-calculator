import math


def erfinv(x: float) -> float:
    if x <= -1 or x >= 1:
        raise Exception
    if x == 0:
        return 0
    a = 0
    b = 4 * x
    if x < 0:
        a, b = b, a
    c = 0.0
    for _ in range(100):
        c = (a + b) / 2
        if math.erf(c) > x:
            b = c
        else:
            a = c
    return c

