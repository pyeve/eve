# -*- coding: utf-8 -*-
import os

db_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test.db')
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s' % db_filename

SERVER_NAME = 'localhost:5000'

DOMAIN = {
    'people': {
        'item_title': 'person',
        'additional_lookup': {
            'url': '[0-9]+',
            'field': '_id'
        },
        'cache_control': 'max-age=10,must-revalidate',
        'cache_expires': 10,
        'resource_methods': ['GET', 'POST', 'DELETE']
    }
}