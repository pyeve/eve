# -*- coding: utf-8 -*-

"""
    eve.io.sqlalchemy
    ~~~~~~~~~~~~

    This package implements the SQLAlchemy data layer.

    :copyright: (c) 2013 by Nicola Iarocci, Tomasz Jezierski (Tefnet)
    :license: BSD, see LICENSE for more details.
"""

from sqlalchemy import SQLAlchemy, db
from validation import Validator

__all__ = ['SQLAlchemy', 'db', 'Validator']
