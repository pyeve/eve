# -*- coding: utf-8 -*-
from __future__ import print_function


SETTINGS = {
    'DEBUG': True,
    'MONGO_HOST': 'localhost',
    'MONGO_PORT': 27017,
    'MONGO_DBNAME': 'test_db',
    'DOMAIN': {'test': {
        'test_field': {
            'type': 'string',
            'minlength': 5,
            'maxlength': 20,
        },
    }}
}
