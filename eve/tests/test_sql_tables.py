import hashlib

from eve.io.sql.decorators import registerSchema
from eve.io.sql.sql import db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import column_property, relationship
from sqlalchemy import (
    Column,
    inspect,
    Integer,
    String,
    ForeignKey,
    DateTime)

Base = declarative_base()
db.Model = Base


class CommonColumns(Base):
    """
    Master SQLAlchemy Model. All the SQL tables defined for the application
    should inherit from this class. It provides common columns such as
    _created, _updated and _id.

    WARNING: the _id column name does not respect Eve's setting for custom
    ID_FIELD.
    """
    __abstract__ = True
    _created = Column(DateTime)
    _updated = Column(DateTime)
    _etag = Column(String)
    # TODO: make this comply to Eve's custom ID_FIELD setting
    _id = Column(Integer, primary_key=True)

    def __init__(self, *args, **kwargs):
        h = hashlib.sha1()
        self._etag = h.hexdigest()
        super(CommonColumns, self).__init__(*args, **kwargs)

    def jsonify(self):
        relationships = inspect(self.__class__).relationships.keys()
        mapper = inspect(self)
        attrs = [a.key for a in mapper.attrs if
                 a.key not in relationships
                 and a.key not in mapper.expired_attributes]
        return dict([(c, getattr(self, c, None)) for c in attrs])


@registerSchema('people')
class People(CommonColumns):
    __tablename__ = 'people'
    firstname = Column(String(80), unique=True)
    lastname = Column(String(120))
    fullname = column_property(firstname + " " + lastname)
    prog = Column(Integer)
    born = Column(DateTime)
    title = Column(String(20), default='Mr.')

    @classmethod
    def from_tuple(cls, data):
        return cls(firstname=data[0], lastname=data[1], prog=data[2])


@registerSchema('invoices')
class Invoices(CommonColumns):
    __tablename__ = 'invoices'
    number = Column(Integer)
    people_id = Column(Integer, ForeignKey('people._id'))
    people = relationship(People)


@registerSchema('payments')
class Payments(CommonColumns):
    __tablename__ = 'payments'
    number = Column(Integer)
    string = Column(String(80))
