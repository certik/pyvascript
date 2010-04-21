from python import Python

def f1(x):
    return x

def f2(x):
    return x + 5

def f3(x):
    a = x + 1
    return a - 5

def test(func, arg_array):
    code = compile(str(Python(func)), "", "exec")
    namespace = {}
    eval(code, {}, namespace)
    func_py = namespace[func.__name__]
    for arg in arg_array:
        assert func(arg) == func_py(arg)

def test_basic():
    test(f1, [1, 2, 3, "x"])
    test(f2, [1, 2, 3, -5])
    test(f3, [1, 2, 3, -5])

test_basic()
