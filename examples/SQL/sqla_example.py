from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from tables import People, Base

app = Eve(validator=ValidatorSQL, data=SQL)

# bind SQLAlchemy
db = app.data.driver
Base.metadata.bind = db.engine
db.Model = Base
db.create_all()

# Insert some example data in the db
if not db.session.query(People).count():
    import example_data
    for item in example_data.test_data:
        db.session.add(People.from_tuple(item))
    db.session.commit()

app.run(debug=True, use_reloader=False) # using reloaded will destory in-memory sqlite db
