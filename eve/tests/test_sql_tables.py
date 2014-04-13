from eve.io.sql.decorators import registerSchema
from eve.io.sql.common import CommonColumns
from eve.io.sql.sql import db

@registerSchema('people')
class People(CommonColumns):
    __tablename__ = 'people'
    firstname = db.Column(db.String(80))
    lastname = db.Column(db.String(120))
    fullname = db.column_property(firstname + " " + lastname)
    prog = db.Column(db.Integer)

    @classmethod
    def from_tuple(cls, data):
        return cls(firstname=data[0], lastname=data[1], prog=data[2])
