# -*- coding: utf-8 -*-
from __future__ import print_function

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column,
    String,
    Integer,
    )

from eve_sqlalchemy.decorators import registerSchema
from eve_sqlalchemy import SQL
from eve_sqlalchemy.validation import ValidatorSQL

Base = declarative_base()


class TestScheme(Base):
    __tablename__ = 'test'
    id = Column(Integer, primary_key=True, autoincrement=True)
    test_field = Column(String(100))

registerSchema('people')(TestScheme)

SETTINGS = {
    'DEBUG': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite://',
    'DOMAIN': {
        'test': TestScheme._eve_schema['people'],
    }
}