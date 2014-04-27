# -*- coding: utf-8 -*-

"""
    eve.io.sql.common
    ~~~~~~~~~~~~

    Master SQLAlchemy db.Model for all the tables to derive from.

"""
from sqlalchemy import func
from .sql import db


class CommonColumns(db.Model):
    """
    Master SQLAlchemy db.Model. All the SQL tables defined for the application should inherit from this class.
    It provides common columns such as _created, _updated and _id.

    WARNING: the _id column name does not respect Eve's setting for custom ID_FIELD.
    """
    __abstract__ = True
    _created = db.Column(db.DateTime)
    _updated = db.Column(db.DateTime)
    _id = db.Column(db.Integer, primary_key=True)  # TODO: make this comply to Eve's custom ID_FIELD setting
