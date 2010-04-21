from python import Python

@Python
def test1(x):
    x = x + 1
    return x + 1

@Python
def test2(x):
    if x:
        return 5
    else:
        return 6

print test1
print test2
