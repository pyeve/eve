from eve import Eve
from eve.io.sql import SQL, Validator
from eve.io.sql import db


# Insert some example data in the db
import example_data
from tables import People
db.create_all()
if not db.session.query(People).count():
    for item in example_data.test_data:
        db.session.add(People.from_tuple(item))
    db.session.commit()


app = Eve(validator=Validator, data=SQL)
app.run(debug=True)