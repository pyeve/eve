from eve import Eve
from eve.validation import Validator
#from eve.io import Mongo


class Validator(Validator):
    def _validate_cin(self, cin, field, value):
        if cin:
            pass


if __name__ == '__main__':
    app = Eve(validator=Validator)
    app.run()
