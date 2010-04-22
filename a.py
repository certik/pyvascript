from python import transform_py

t = """\
def f(x):
    if x > 0:
        if x > 10:
            a = 3
        else:
            a = 4
        b = 7
        a -= 7
    b = 6
    return a
"""

print transform_py(t)
