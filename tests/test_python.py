from python import Python

def f1(x):
    return x

def test(func, arg_array):
    code = compile(str(Python(func)), "", "exec")
    namespace = {}
    eval(code, {}, namespace)
    func_py = namespace[func.__name__]
    for arg in arg_array:
        assert func(arg) == func_py(arg)

def test_f1():
    test(f1, [1, 2, 3, "x"])

test_f1()
