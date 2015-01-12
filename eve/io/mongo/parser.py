# -*- coding: utf-8 -*-

"""
    eve.io.mongo.parser
    ~~~~~~~~~~~~~~~~~~~

    This module implements a Python-to-Mongo syntax parser. Allows the MongoDB
    data-layer to seamlessy respond to a Python-like query.

    :copyright: (c) 2015 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import ast
import sys
from datetime import datetime   # noqa
from bson import ObjectId       # noqa


def parse(expression):
    """ Given a python-like conditional statement, returns the equivalent
    mongo-like query expression. Conditional and boolean operators (==, <=, >=,
    !=, >, <) along with a couple function calls (ObjectId(), datetime()) are
    supported.
    """
    v = MongoVisitor()
    try:
        v.visit(ast.parse(expression))
    except SyntaxError as e:
        e = ParseError(e)
        e.__traceback__ = sys.exc_info()[2]
        raise e
    return v.mongo_query


class ParseError(ValueError):
    pass


class MongoVisitor(ast.NodeVisitor):
    """ Implements the python-to-mongo parser. Only Python conditional
    statements are supported, however nested, combined with most common compare
    and boolean operators (And and Or).

    Supported compare operators: ==, >, <, !=, >=, <=
    Supported boolean operators: And, Or
    """
    op_mapper = {
        ast.Eq: '',
        ast.Gt: '$gt',
        ast.GtE: '$gte',
        ast.Lt: '$lt',
        ast.LtE: '$lte',
        ast.NotEq: '$ne',
        ast.Or: '$or',
        ast.And: '$and'
    }

    def visit_Module(self, node):
        """ Module handler, our entry point.
        """
        self.mongo_query = {}
        self.ops = []
        self.current_value = None

        # perform the magic.
        self.generic_visit(node)

        # if we didn't obtain a query, it is likely that an unsopported
        # python expression has been passed.
        if self.mongo_query == {}:
            raise ParseError("Only conditional statements with boolean "
                             "(and, or) and comparison operators are "
                             "supported.")

    def visit_Expr(self, node):
        """ Make sure that we are parsing compare or boolean operators
        """
        if not (isinstance(node.value, ast.Compare) or
                isinstance(node.value, ast.BoolOp)):
            raise ParseError("Will only parse conditional statements")
        self.generic_visit(node)

    def visit_Compare(self, node):
        """ Compare operator handler.
        """
        self.visit(node.left)
        left = self.current_value

        operator = self.op_mapper[node.ops[0].__class__] if node.ops else None

        if node.comparators:
            comparator = node.comparators[0]
            self.visit(comparator)

        if operator != '':
            value = {operator: self.current_value}
        else:
            value = self.current_value

        if self.ops:
            self.ops[-1].append({left: value})
        else:
            self.mongo_query[left] = value

    def visit_BoolOp(self, node):
        """ Boolean operator handler.
        """
        op = self.op_mapper[node.op.__class__]
        self.ops.append([])
        for value in node.values:
            self.visit(value)

        c = self.ops.pop()
        if self.ops:
            self.ops[-1].append({op: c})
        else:
            self.mongo_query[op] = c

    def visit_Call(self, node):
        """ A couple function calls are supported: bson's ObjectId() and
        datetime().
        """
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
        """ Attribute handler ('Contact.Id').
        """
        self.visit(node.value)
        self.current_value += "." + node.attr

    def visit_Name(self, node):
        """ Names handler.
        """
        self.current_value = node.id

    def visit_Num(self, node):
        """ Numbers handler.
        """
        self.current_value = node.n

    def visit_Str(self, node):
        """ Strings handler.
        """
        self.current_value = node.s
