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
    'datasource': {'filter': {'username': {'$exists': False}}},
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
            'schema': {
                'type': 'dict',
                'schema': {
                    'sku': {'type': 'string', 'maxlength': 10},
                    'price': {'type': 'integer'},
                },
            },
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
        'title': {
            'type': 'string',
            'default': 'Mr.',
        }
    }
}

import copy
users = copy.deepcopy(contacts)
users['url'] = 'users'
users['datasource'] = {'source': 'contacts',
                       'filter': {'username': {'$exists': True}}}
users['schema']['username'] = {'type': 'string', 'required': True}
users['resource_methods'] = ['DELETE', 'POST', 'GET']
users['item_title'] = 'user'

invoices = {
    #'item_lookup': False,
    #'item_methods': ['GET'],
    'schema': {
        'inv_number': {'type': 'string'},
        'person': {
            'type': 'objectid',
            'data_relation': {'collection': 'contacts'}
        }
    }
}


payments = {
    'resource_methods': ['GET'],
    'item_methods': ['GET'],
}

empty = copy.deepcopy(invoices)

DOMAIN = {
    'contacts': contacts,
    'users': users,
    'invoices': invoices,
    'payments': payments,
    'empty': empty,
}
