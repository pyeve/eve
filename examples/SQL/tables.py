# -*- coding: utf-8 -*-

"""
    SQL tables.

    The new SQL data layer for Eve uses SQLAlchemy, specifically Flask-SQLAlchemy, for interacting
    with a SQL database. To prevent Flask-SQLAlchemy to define the tables twice, the new layer
    requires the schema definition to be split into two python files, one for the tables and one for
    the schema dictionary required by Eve (settings.py).

    All defined tables should inherit from CommonColumns which attaches the _created, _updated and _id
    columns to all tables. NOTE: The SQL data layer does not conform yet to Eve feature that lets you specify
    a custom name for the ID field.

    All tables should have the registerSchema decorator applied to them in order to be registered in Eve's
    schema. The argument of the decorator is name of the resource for Eve.

"""

from eve.io.sql.decorators import registerSchema
from eve.io.sql.common import CommonColumns
from eve.io.sql import db

@registerSchema('people')
class People(CommonColumns):
    __tablename__ = 'people'
    firstname = db.Column(db.String(80))
    lastname = db.Column(db.String(120))
    fullname = db.column_property(firstname + " " + lastname)

    def __repr__(self):
        return '<People %s>' % (self.fullname,)

    @classmethod
    def from_tuple(cls, data):
        """Helper method to populate the db"""
        return cls(firstname=data[0], lastname=data[1])
