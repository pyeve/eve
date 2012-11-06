import ast
from datetime import datetime
from bson import ObjectId


def parse(expression):
    v = MongoVisitor()
    v.visit(ast.parse(expression))
    return v.mongo_query


class ParseError(ValueError):
    pass


class MongoVisitor(ast.NodeVisitor):

    def visit_Module(self, node):
        self.mongo_query = {}
        self.ops = []
        self.current_value = None
        self.generic_visit(node)

    def visit_Expr(self, node):
        if not (isinstance(node.value, ast.Compare) or
                isinstance(node.value, ast.BoolOp)):
            raise ParseError("Will only parse conditional statements")
        self.generic_visit(node)

    def visit_Compare(self, node):

        self.visit(node.left)
        left = self.current_value

        operator = None
        if node.ops:
            op = node.ops[0]
            if isinstance(op, ast.Eq):
                operator = ''
            elif isinstance(op, ast.Gt):
                operator = '$gt'
            elif isinstance(op, ast.GtE):
                operator = '$gte'
            elif isinstance(op, ast.Lt):
                operator = '$lt'
            elif isinstance(op, ast.LtE):
                operator = '$lte'
            elif isinstance(op, ast.NotEq):
                operator = '$ne'

        value = None
        if node.comparators:
            comparator = node.comparators[0]
            self.visit(comparator)
            #if isinstance(comparator, ast.Num):
            #    value = comparator.n

        if operator != '':
            value = {operator: self.current_value}
        else:
            value = self.current_value

        if self.ops:
            self.ops[-1].append({left: value})
        else:
            self.mongo_query[left] = value

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.Or):
            op = '$or'
        elif isinstance(node.op, ast.And):
            op = '$and'
        self.ops.append([])
        for value in node.values:
            self.visit(value)

        c = self.ops.pop()
        if self.ops:
            self.ops[-1].append({op: c})
        else:
            self.mongo_query[op] = c

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            expr = None
            if node.func.id == 'ObjectId':
                expr = "('" + node.args[0].s + "')"
            elif node.func.id == 'datetime':
                values = []
                for arg in node.args:
                    values.append(str(arg.n))
                expr = "(" + ", ".join(values) + ")"
            if expr:
                self.current_value = eval(node.func.id + expr)

    def visit_Attribute(self, node):
        self.visit(node.value)
        self.current_value += "." + node.attr

    def visit_Name(self, node):
        self.current_value = node.id

    def visit_Num(self, node):
        self.current_value = str(node.n)

    def visit_Str(self, node):
        self.current_value = node.s
