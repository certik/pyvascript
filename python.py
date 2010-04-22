import inspect
from ast import parse, iter_fields, AST, dump

def flatten(l):
    s = []
    if isinstance(l, list):
        for item in l:
            s.extend(flatten(item))
    else:
        s.append(l)
    return s


class NodeVisitor(object):

    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        s = []
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AST):
                        s.append(self.visit(item))
                    else:
                        raise NotImplementedError("Some problem.")
            elif isinstance(value, AST):
                s.append(self.visit(value))
            else:
                # I don't understand why we get here sometimes, but we need to
                # skip it:
                pass
        return node.__class__.__name__ + str(tuple(s))

class PythonVisitor(NodeVisitor):

    def __init__(self):
        self._scope = []

    def indent_block(self, l):
        s = []
        for statement in l:
            stat = self.visit(statement)
            if isinstance(stat, str):
                s.append("    %s" % stat)
            else:
                for item in stat:
                    s.append("    %s" % item)
        return s

    def visit_If(self, node):
        s = []
        s.append("if %s:" % self.visit(node.test))
        s.extend(self.indent_block(node.body))
        if len(node.orelse) > 0:
            s.append("else:")
            s.extend(self.indent_block(node.orelse))
        return s

    def visit_Assign(self, node):
        assert len(node.targets) == 1
        target = node.targets[0]
        return ["%s = %s" % (self.visit(target), self.visit(node.value))]

    def visit_AugAssign(self, node):
        return ["%s %s= %s" % (self.visit(node.target),
            self.visit(node.op),
            self.visit(node.value))]

    def visit_Num(self, node):
        return str(node.n)

    def visit_Gt(self, node):
        return ">"

    def visit_Add(self, node):
        return "+"

    def visit_Sub(self, node):
        return "-"

    def visit_Mult(self, node):
        return "*"

    def visit_Div(self, node):
        return "/"

    def visit_arguments(self, node):
        return [self.visit(arg) for arg in node.args]

    def visit_Return(self, node):
        return ["return %s" % self.visit(node.value)]

    def visit_FunctionDef(self, node):
        s = []
        args = ", ".join(self.visit(node.args))
        s.append("def %s(%s):" % (node.name, args))
        s.extend(self.indent_block(node.body))
        return s

    def visit_Compare(self, node):
        assert len(node.ops) == 1
        assert len(node.comparators) == 1
        op = node.ops[0]
        comp = node.comparators[0]
        return "%s %s %s" % (self.visit(node.left),
                self.visit(op),
                self.visit(comp)
                )

    def visit_BinOp(self, node):
        return "%s %s %s" % (self.visit(node.left),
                self.visit(node.op),
                self.visit(node.right)
                )

    def visit_Module(self, node):
        return flatten([self.visit(s) for s in node.body])

    def visit_Name(self, node):
        return node.id

    def generic_visit(self, node):
        print "Generic visit:", node.__class__.__name__, node._fields
        return super(PythonVisitor, self).generic_visit(node)

def transform_py(s):
    v = PythonVisitor()
    t = parse(s)
    return "\n".join(v.visit(t))

class Python(object):

    def __init__(self, obj):
        obj_source = inspect.getsource(obj)
        self._python = transform_py(obj_source)

    def __str__(self):
        return self._python

#################
# this is the obsolete old version:
import dis, struct
from translator import Translator, opcode

class JsDict(dict):
    def __repr__(self):
        return '{%s}' % ', '.join('%s : %s' % kv for kv in self.items())

class JsList(list):
    def __repr__(self):
        return '[%s]' % ', '.join(map(str, self))

class PyFunc(object):
    def __init__(self, name, args=()):
        self.name = name
        self.args = tuple(args)

    def __str__(self):
        return '%s(%s)' % (self.name, ', '.join(self.args))
    def __repr__(self):
        return str(self)

class Python2(Translator):
    """
    Python to Python translator.

    Based on the Translator() class, it just implements the opcodes -> js
    translation.
    """

    def handle_class(self, cls, *args, **kwargs):
        super_class = object
        super_dir = dir(super_class)
        subdir = [elem for elem in dir(cls) if elem not in super_dir]
        subdir = [elem for elem in subdir if elem not in [
            '__dict__', '__module__', '__weakref__']]

        if cls.__init__ is not super_class.__init__:
            code = str(Python(cls.__init__, inClass=True, fname=cls.__name__)).rstrip()[:-1].rstrip() + '\n'
        else:
            code = 'def %s():\n' % cls.__name__

        for key in subdir:
            val = getattr(cls, key)
            if callable(val):
                continue

            code += '\tthis.%s = %s;\n' % (key, val)

        code += '}\n'

        for func in subdir:
            func = getattr(cls, func)
            if not callable(func):
                continue

            code += '%s.prototype.%s = %s' % (
                cls.__name__,
                func.__name__,
                str(Python(func, inClass=True, anonymous=True))
            )

        return code

    def handle_function(self, func, inClass=False, fname=None, anonymous=False):
        self.code = func.func_code
        self.co_code = self.code.co_code

        self.hit = []
        pc = 0
        outer = []
        stack = []
        scope = [name for name in self.code.co_varnames[:self.code.co_argcount]]
        try:
            while pc != -1 and pc < len(self.co_code):
                pc = self.execute(pc, block=outer, stack=stack, scope=scope)
        except Exception:
            print
            dis.dis(func)
            raise

        if func.func_defaults:
            defaults = ''

            off = self.code.co_argcount - len(func.func_defaults)
            for i in range(len(func.func_defaults)):
                var = self.code.co_varnames[off+i]
                val = func.func_defaults[i]
                if val == None:
                    val = 'null'
                else:
                    if val is True:
                        val = 'true'
                    elif val is False:
                        val = 'false'
                    elif val is None:
                        val = 'None'
                    else:
                        val = repr(val)
                defaults += '\t%s = (typeof(%s) != \'undefined\' && %s != null) ? %s : %s;\n' % (
                        var, var, var, var, val
                    )
        else:
            defaults = ''

        if fname == None:
            fname = func.__name__

        if fname == '__top__':
            return '\n'.join(line for line in outer if line != 'return;')
        else:
            return \
'''
def%s(%s):
%s%s
''' % (
                (not anonymous) and ' %s' % fname or '',
                ', '.join(self.code.co_varnames[inClass and 1 or 0:self.code.co_argcount]),
                defaults,
                '\n'.join('\t%s' % line for line in outer)
            )

    @opcode
    def POP_TOP(self, block, stack, _scope):
        top = stack.pop()

        if isinstance(top, tuple) and len(top) == 2:
            use, top = top
        else:
            use = True

        if use:
            block.append('%s' % top)

    @opcode
    def LOAD_CONST(self, _block, stack, _scope, const):
        if const == None:
            stack.append('null')
        else:
            stack.append(repr(const))

    @opcode
    def LOAD_FAST(self, _block, stack, _scope, var):
        stack.append(var)

    @opcode
    def STORE_FAST(self, block, stack, scope, var):
        if not (var in scope):
            scope.append(var)

        if stack[-1] == 'for':
            block.append(var)
            stack.pop()
        else:
            block.append('%s = %s' % (var, stack.pop()))

    def binaryOp(self, _block, stack, _scope, oper):
        a, b = stack.pop(), stack.pop()
        stack.append('(%s) %s (%s)' % (b, oper, a))
    @opcode
    def RETURN_VALUE(self, block, stack, _scope):
        val = stack.pop()
        if val != 'null':
            block.append('return %s' % val)
        else:
            block.append('return')

    def addSemicolon(self, line):
        return ''

    @opcode
    def JUMP_IF_FALSE(self, block, stack, scope, pc, delta):
        cond = stack.pop()
        stack.append((False, cond))
        nblock = [('if', pc + delta)]
        nstack = [elem for elem in stack]
        nscope = [var for var in scope]
        tpc = pc
        while tpc != -1 and tpc < pc + delta and tpc < len(self.co_code):
            tpc = self.execute(tpc, block=nblock, stack=nstack, scope=nscope)

        block.append('if %s:' % cond)
        hasElse = False
        for line in nblock:
            if isinstance(line, tuple):
                if line[0] == 'else':
                    hasElse = True
                    pc += delta
                    delta = line[1] - pc
                    break
                else:
                    continue
            block.append('\t%s%s' % (line, self.addSemicolon(line)))

        if hasElse:
            nblock = []
            nstack = [elem for elem in stack]
            nscope = [var for var in scope]
            tpc = pc
            while tpc != -1 and tpc < pc + delta and tpc < len(self.co_code):
                tpc = self.execute(tpc, block=nblock, stack=nstack, scope=nscope)
            if len(nblock) != 0:
                block.append('else:')
                for line in nblock:
                    block.append('\t%s%s' % (line, self.addSemicolon(line)))

        return pc + delta

    @opcode
    def JUMP_FORWARD(self, block, _stack, _scope, pc, delta):
        if isinstance(block[0], tuple) and block[0][0] == 'if':
            del block[0]
            block.append(('else', pc + delta))
        return pc + delta

    @opcode
    def JUMP_ABSOLUTE(self, block, _stack, _scope, pc):
        if len(block) > 0 and isinstance(block[0], tuple) and \
                block[0][0] == 'if':
            del block[0]
            block.append(('else', pc))
        return pc

    @opcode
    def STOP_CODE(self, _block, _stack, _scope):
        pass

    @opcode
    def COMPARE_OP(self, _block, stack, _scope, opname):
        a, b = stack.pop(), stack.pop()
        import opcode
        stack.append('%s %s %s' % (b, opcode.cmp_op[opname], a))
