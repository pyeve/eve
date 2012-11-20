# -*- coding: utf-8 -*-

from eve import Eve
from eve.io.mongo import Validator


class Validator(Validator):
    def _validate_cin(self, cin, field, value):
        if cin:
            pass


if __name__ == '__main__':
    app = Eve(validator=Validator)
    app.run()
