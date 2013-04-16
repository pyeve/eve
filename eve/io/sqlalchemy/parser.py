# -*- coding: utf-8 -*-

"""
    eve.io.sqlalchemy.parser
    ~~~~~~~~~~~~~~~~~~~

    This module implements a Python-to-SQLAlchemy syntax parser. Allows the SQLAlchemy
    data-layer to seamlessy respond to a Python-like query.

    :copyright: (c) 2013 by Nicola Iarocci, Tomasz Jezierski (Tefnet).
    :license: BSD, see LICENSE for more details.
"""

import ast
from datetime import datetime
import flask.ext.sqlalchemy as flask_sqlalchemy
sqla_op = flask_sqlalchemy.sqlalchemy.sql.expression.operators
sqla_exp = flask_sqlalchemy.sqlalchemy.sql.expression

def parse(expression, model):
    """Given a python-like conditional statement, returns the equivalent
    SQLAlchemy-like query expression. Conditional and boolean operators (==, <=, >=,
    !=, >, <) are supported.
    """
    v = SQLAVisitor(model)
    v.visit(ast.parse(expression))
    return v.sqla_query


class ParseError(ValueError):
    pass


class SQLAVisitor(ast.NodeVisitor):
    """Implements the python-to-sqlalchemy parser. Only Python conditional
    statements are supported, however nested, combined with most common compare
    and boolean operators (And and Or).

    Supported compare operators: ==, >, <, !=, >=, <=
    Supported boolean operators: And, Or
    """
    op_mapper = {
        ast.Eq: sqla_op.eq,
        ast.Gt: sqla_op.gt,
        ast.GtE: sqla_op.ge,
        ast.Lt: sqla_op.lt,
        ast.LtE: sqla_op.le,
        ast.NotEq: sqla_op.ne,
        ast.Or: sqla_exp.or_,
        ast.And: sqla_exp.and_
    }

    def __init__(self, model):
        super(SQLAVisitor, self).__init__()
        self.model = model

    def visit_Module(self, node):
        """ Module handler, our entry point.
        """
        self.sqla_query = []
        self.ops = []
        self.current_value = None

        # perform the magic.
        self.generic_visit(node)

        # if we didn't obtain a query, it is likely that an unsopported
        # python expression has been passed.
        if self.sqla_query == {}:
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
        left = getattr(self.model, self.current_value)

        operator = self.op_mapper[node.ops[0].__class__]

        if node.comparators:
            comparator = node.comparators[0]
            self.visit(comparator)

        value = self.current_value

        if self.ops:
            self.ops[-1]['args'].append(operator(left, value))
        else:
            self.sqla_query.append(operator(left, value))

    def visit_BoolOp(self, node):
        """ Boolean operator handler.
        """
        op = self.op_mapper[node.op.__class__]
        self.ops.append({'op':op, 'args':[]})
        for value in node.values:
            self.visit(value)

        tops = self.ops.pop()
        if self.ops:
            self.ops[-1]['args'].append(tops['op'](*tops['args']))
        else:
            self.sqla_query.append(tops['op'](*tops['args']))

    def visit_Call(self, node):
        # TODO ?
        pass

    def visit_Attribute(self, node):
        # FIXME ?
        self.visit(node.value)
        self.current_value += "." + node.attr

    def visit_Name(self, node):
        """ Names """
        self.current_value = node.id

    def visit_Num(self, node):
        """ Numbers """
        self.current_value = node.n

    def visit_Str(self, node):
        """ Strings """
        self.current_value = node.s
