from eve import Eve
from eve.io.mongo import Validator
import os


class Validator(Validator):
    def _validate_cin(self, cin, field, value):
        if cin:
            pass


if __name__ == '__main__':
    app = Eve(validator=Validator)
    port = int(os.environ.get('PORT', 5000))
    app.run(port=port)
