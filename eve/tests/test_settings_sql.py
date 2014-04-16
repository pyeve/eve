# -*- coding: utf-8 -*-
import os

db_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test.db')
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s' % db_filename

# SQLALCHEMY_ECHO = True
# SQLALCHEMY_RECORD_QUERIES = True

SERVER_NAME = 'localhost:5000'

ID_FIELD = '_id'
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD

RESOURCE_METHODS = ['GET', 'POST', 'DELETE']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE', 'PUT']

DOMAIN = {
    'people': {
        'item_title': 'person',
        'additional_lookup': {
            'url': 'regex("[\w]+")',
            'field': 'firstname'
        },
        'cache_control': 'max-age=10,must-revalidate',
        'cache_expires': 10,
        'resource_methods': ['GET', 'POST', 'DELETE']
    }
}