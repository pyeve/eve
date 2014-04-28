from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from tables import People


app = Eve(validator=ValidatorSQL, data=SQL)


# Insert some example data in the db
import example_data
db = app.data.driver
db.create_all()
if not db.session.query(People).count():
    for item in example_data.test_data:
        db.session.add(People.from_tuple(item))
    db.session.commit()


app.run(debug=True)