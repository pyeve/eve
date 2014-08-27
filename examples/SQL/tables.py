"""
    SQL tables.
    This is a typical declarative usage of sqlalchemy,
    It has no dependency on flask or eve iself. Pure sqlalchemy.
"""
from sqlalchemy import inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext import hybrid
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property, relationship
from sqlalchemy import func
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    DateTime)

Base = declarative_base()


class CommonColumns(Base):
    __abstract__ = True
    _created = Column(DateTime, default=func.now())
    _updated = Column(DateTime, default=func.now(), onupdate=func.now())

    @hybrid_property
    def _id(self):
        """
        Eve backward compatibility
        """
        return self.id

    def jsonify(self):
        """
        Used to dump related objects to json
        """
        relationships = inspect(self.__class__).relationships.keys()
        mapper = inspect(self)
        attrs = [a.key for a in mapper.attrs if \
                a.key not in relationships \
                and not a.key in mapper.expired_attributes]
        attrs += [a.__name__ for a in inspect(self.__class__).all_orm_descriptors if a.extension_type is hybrid.HYBRID_PROPERTY]
        return dict([(c, getattr(self, c, None)) for c in attrs])


class People(CommonColumns):
    __tablename__ = 'people'
    id = Column(Integer, primary_key=True, autoincrement=True)
    firstname = Column(String(80))
    lastname = Column(String(120))
    fullname = column_property(firstname + " " + lastname)

    @classmethod
    def from_tuple(cls, data):
        """Helper method to populate the db"""
        return cls(firstname=data[0], lastname=data[1])


class Invoices(CommonColumns):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(Integer)
    people_id = Column(Integer, ForeignKey('people.id'))
    people = relationship(People, uselist=False)
