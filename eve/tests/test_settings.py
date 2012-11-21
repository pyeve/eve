# -*- coding: utf-8 -*-

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_USERNAME = 'test_user'
MONGO_PASSWORD = 'test_pw'
MONGO_DBNAME = 'eve_test'
ID_FIELD = '_id'

SERVER_NAME = 'localhost:5000'

RESOURCE_METHODS = ['GET', 'POST', 'DELETE']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE']
ITEM_CACHE_CONTROL = ''
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD
ITEM_URL = '[a-f0-9]{24}'

contacts = {
    'url': 'arbitraryurl',
    'cache_control': 'max-age=20,must-revalidate',
    'cache_expires': 20,
    'item_title': 'contact',
    'additional_lookup': {
        'url': '[\w]+',   # to be unique field
        'field': 'ref'
    },
    'schema': {
        'ref': {
            'type': 'string',
            'minlength': 25,
            'maxlength': 25,
            'required': True,
            'unique': True,
        },
        'prog': {
            'type': 'integer'
        },
        'role': {
            'type': 'list',
            'allowed': ["agent", "client", "vendor"],
        },
        'rows': {
            'type': 'list',
            'items': {
                'sku': {'type': 'string', 'maxlength': 10},
                'price': {'type': 'integer'},
            }
        },
        'alist': {
            'type': 'list',
            'items': [{'type': 'string'}, {'type': 'integer'}, ]
        },
        'location': {
            'type': 'dict',
            'schema': {
                'address': {'type': 'string'},
                'city': {'type': 'string', 'required': True}
            },
        },
        'born': {
            'type': 'datetime',
        },
        'tid': {
            'type': 'objectid',
        },
    }
}

invoices = {
    #'item_lookup': False,
    #'item_methods': ['GET'],
    'schema': {'inv_number': {'type': 'string'}, }
}


payments = {
    'methods': ['GET'],
    'item_methods': ['GET'],
}

DOMAIN = {
    'contacts': contacts,
    'invoices': invoices,
    'payments': payments,
}
