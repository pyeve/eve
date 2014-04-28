from eve.io.sql.decorators import registerSchema
from eve.io.sql.common import CommonColumns
from eve.io.sql.sql import db

@registerSchema('people')
class People(CommonColumns):
    __tablename__ = 'people'
    firstname = db.Column(db.String(80), unique=True)
    lastname = db.Column(db.String(120))
    fullname = db.column_property(firstname + " " + lastname)
    prog = db.Column(db.Integer)
    born = db.Column(db.DateTime)
    title = db.Column(db.String(20), default='Mr.')

    @classmethod
    def from_tuple(cls, data):
        return cls(firstname=data[0], lastname=data[1], prog=data[2])


@registerSchema('invoices')
class Invoices(CommonColumns):
    __tablename__ = 'invoices'
    number = db.Column(db.Integer)
    people = db.Column(db.Integer, db.ForeignKey('people._id'))


@registerSchema('payments')
class Payments(CommonColumns):
    __tablename__ = 'payments'
    number = db.Column(db.Integer)
    string = db.Column(db.String(80))
