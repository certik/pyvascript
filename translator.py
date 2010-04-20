"""
Python to bytecode translator.

It is based on opcodes, that are well documented here:

http://docs.python.org/library/dis.html

It is dependent on the Python version, but the differences are minor (just
couple more opcodes have to be implemented for later versions of Python, and
some obsolete opcodes are not used anymore).
"""

import dis, opcode, struct

class Translator(object):
    varcount = 0

    def __init__(self, func, inClass=False, fname=None, anonymous=False):
        from pyvascript import JavaScript
        self.opcdmap = JavaScript.opcode.func_defaults[0]
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
            self.js = ''
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
            self.js = '\n'.join(line for line in outer if line != 'return;')
        else:
            self.js = \
'''
function%s(%s) {
%s%s
}
''' % (
                (not anonymous) and ' %s' % fname or '',
                ', '.join(self.code.co_varnames[inClass and 1 or 0:self.code.co_argcount]),
                defaults,
                '\n'.join('\t%s' % line for line in outer)
            )

    def execute(self, pc, block, stack, scope):
        if pc in self.hit:
            return -1
        self.hit.append(pc)

        opcd = _ord(self.co_code[pc])
        name = opcode.opname[opcd]
        pc += 1

        # build the arguments:
        args = [self, block, stack, scope]

        if opcd >= opcode.HAVE_ARGUMENT:
            arg, = struct.unpack('h', self.co_code[pc:pc+2])
            pc += 2

        if opcd in opcode.hasjrel:
            args.append(pc)
        elif opcd in opcode.hasjabs:
            # this is needed, because we call JUMP_IF_FALSE from there:
            if name == "POP_JUMP_IF_FALSE":
                args.append(pc)

        if opcd >= opcode.HAVE_ARGUMENT:
            if opcd in opcode.hasconst:
                arg = self.code.co_consts[arg]
            elif opcd in opcode.haslocal:
                arg = self.code.co_varnames[arg]
            elif opcd in opcode.hasname:
                arg = self.code.co_names[arg]
            args.append(arg)

        if name.startswith('INPLACE_'): # Why is this separate?  Just an optimization in the Py core?
            name = 'BINARY_' + name[len('INPLACE_'):]
        if name in self.opcdmap:
            #print(args)
            npc = self.opcdmap[name](*args)
            if npc != None:
                pc = npc
        elif name in self.binaryOpers:
            args.append(self.binaryOpers[name])
            self.binaryOp(*args[1:])
        else:
            raise Exception('Unknown opcode `%s\'' % name)

        return pc

    def __str__(self):
        return self.js

def _ord(x):
    if isinstance(x, str):
        return ord(x)
    else:
        return x
