from eve import Eve
from eve.io.sqlalchemy import SQLAlchemy


app = Eve(data=SQLAlchemy)

db = app.data.driver

test_data = [
(u'George', u'Washington'),
(u'John', u'Adams'),
(u'Thomas', u'Jefferson'),
(u'George', u'Clinton'),
(u'James', u'Madison'),
(u'Elbridge', u'Gerry'),
(u'James', u'Monroe'),
(u'John', u'Adams'),
(u'Andrew', u'Jackson'),
(u'Martin', u'Van Buren'),
(u'William', u'Harrison'),
(u'John', u'Tyler'),
(u'James', u'Polk'),
(u'Zachary', u'Taylor'),
(u'Millard', u'Fillmore'),
(u'Franklin', u'Pierce'),
(u'James', u'Buchanan'),
(u'Abraham', u'Lincoln'),
(u'Andrew', u'Johnson'),
(u'Ulysses', u'Grant'),
(u'Henry', u'Wilson'),
(u'Rutherford', u'Hayes'),
(u'James', u'Garfield'),
(u'Chester', u'Arthur'),
(u'Grover', u'Cleveland'),
(u'Benjamin', u'Harrison'),
(u'Grover', u'Cleveland'),
(u'William', u'McKinley'),
(u'Theodore', u'Roosevelt'),
(u'Charles', u'Fairbanks'),
(u'William', u'Taft'),
(u'Woodrow', u'Wilson'),
(u'Warren', u'Harding'),
(u'Calvin', u'Coolidge'),
(u'Charles', u'Dawes'),
(u'Herbert', u'Hoover'),
(u'Franklin', u'Roosevelt'),
(u'Henry', u'Wallace'),
(u'Harry', u'Truman'),
(u'Alben', u'Barkley'),
(u'Dwight', u'Eisenhower'),
(u'John', u'Kennedy'),
(u'Lyndon', u'Johnson'),
(u'Hubert', u'Humphrey'),
(u'Richard', u'Nixon'),
(u'Gerald', u'Ford'),
(u'Nelson', u'Rockefeller'),
(u'Jimmy', u'Carter'),
(u'Ronald', u'Reagan'),
(u'George', u'Bush'),
(u'Bill', u'Clinton'),
(u'George', u'Bush'),
(u'Barack', u'Obama')
]


class People(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(80))
    lastname = db.Column(db.String(120))
    fullname = db.column_property(firstname + " " + lastname)
    def __repr__(self):
        return '<People %s>' % (self.fullname,)
    
    @classmethod
    def from_tuple(cls, data):
        return cls(firstname=data[0], lastname=data[1])

db.create_all()
if not db.session.query(People).count():
    for item in test_data:
        db.session.add(People.from_tuple(item))
    db.session.commit()
    
app.run(debug=True)
