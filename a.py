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

class Visitor(NodeVisitor):

    def __init__(self):
        self._scope = []

    def indent_block(self, l):
        s = []
        for statement in l:
            for item in self.visit(statement):
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

    def visit_Num(self, node):
        return str(node.n)

    def visit_Gt(self, node):
        return ">"

    def visit_Compare(self, node):
        assert len(node.ops) == 1
        assert len(node.comparators) == 1
        op = node.ops[0]
        comp = node.comparators[0]
        return "%s %s %s" % (self.visit(node.left),
                self.visit(op),
                self.visit(comp)
                )

    def visit_Module(self, node):
        return flatten([self.visit(s) for s in node.body])

    def visit_Name(self, node):
        return node.id

    def generic_visit(self, node):
        print "Generic visit:", node.__class__.__name__, node._fields
        return super(Visitor, self).generic_visit(node)

def transform_py(s):
    v = Visitor()
    t = parse(s)
    return "\n".join(v.visit(t))

t = """\
if x > 0:
    if x > 10:
        a = 3
    else:
        a = 4
    b = 7
    a = 7
b = 6
"""

print transform_py(t)
