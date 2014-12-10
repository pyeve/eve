# -*- coding: utf-8 -*-

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_USERNAME = 'test_user'
MONGO_PASSWORD = 'test_pw'
MONGO_DBNAME = 'eve_test'
ID_FIELD = '_id'

RESOURCE_METHODS = ['GET', 'POST', 'DELETE']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE', 'PUT']
ITEM_CACHE_CONTROL = ''
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD

contacts = {
    'url': 'arbitraryurl',
    'cache_control': 'max-age=20,must-revalidate',
    'cache_expires': 20,
    'item_title': 'contact',
    'additional_lookup': {
        'url': 'regex("[\w]+")',   # to be unique field
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
        'media': {
            'type': 'media'
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
            'nullable': True
        },
        'title': {
            'type': 'string',
            'default': 'Mr.',
        },
        'id_list': {
            'type': 'list',
            'schema': {'type': 'objectid'}
        },
        'id_list_of_dict': {
            'type': 'list',
            'schema': {'type': 'dict', 'schema': {'id': {'type': 'objectid'}}}
        },
        'id_list_fixed_len': {
            'type': 'list',
            'items': [{'type': 'objectid'}]
        },
        'dependency_field1': {
            'type': 'string',
            'default': 'default'
        },
        'dependency_field2': {
            'type': 'string',
            'dependencies': ['dependency_field1']
        },
        'read_only_field': {
            'type': 'string',
            'default': 'default',
            'readonly': True
        },
        'dict_with_read_only': {
            'type': 'dict',
            'schema': {
                'read_only_in_dict': {
                    'type': 'string',
                    'default': 'default',
                    'readonly': True
                }
            }
        },
        'key1': {
            'type': 'string',
        },
        'keyschema_dict': {
            'type': 'dict',
            'keyschema': {'type': 'integer'}
        },
        'aninteger': {
            'type': 'integer',
        },
        'afloat': {
            'type': 'float',
        },
    }
}

import copy
users = copy.deepcopy(contacts)
users['url'] = 'users'
users['datasource'] = {'source': 'contacts',
                       'filter': {'username': {'$exists': True}},
                       'projection': {'username': 1, 'ref': 1}}
users['schema']['username'] = {'type': 'string', 'required': True}
users['resource_methods'] = ['DELETE', 'POST', 'GET']
users['item_title'] = 'user'
users['additional_lookup']['field'] = 'username'

invoices = {
    'schema': {
        'inv_number': {'type': 'string'},
        'person': {
            'type': 'objectid',
            'data_relation': {'resource': 'contacts'}
        },
        'invoicing_contacts': {
            'type': 'list',
            'data_relation': {'resource': 'contacts'}
        }
    }
}

# This resource is used to test app initialization when using resource
# level versioning
versioned_invoices = copy.deepcopy(invoices)
versioned_invoices['versioning'] = True

companies = {
    'item_title': 'company',
    'schema': {
        'departments': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'title': {'type': 'string'},
                    'members': {
                        'type': 'list',
                        'schema': {
                            'type': 'objectid',
                            'data_relation': {'resource': 'contacts'}
                        }
                    }
                }
            }
        }
    }
}

users_overseas = copy.deepcopy(users)
users_overseas['url'] = 'users/overseas'
users_overseas['datasource'] = {'source': 'contacts'}

payments = {
    'resource_methods': ['GET'],
    'item_methods': ['GET'],
}

empty = copy.deepcopy(invoices)

user_restricted_access = copy.deepcopy(contacts)
user_restricted_access['url'] = 'restricted'
user_restricted_access['datasource'] = {'source': 'contacts'}

users_invoices = copy.deepcopy(invoices)
users_invoices['url'] = 'users/<regex("[a-f0-9]{24}"):person>/invoices'
users_invoices['datasource'] = {'source': 'invoices'}

internal_transactions = {
    'resource_methods': ['GET'],
    'item_methods': ['GET'],
    'internal_resource': True
}

DOMAIN = {
    'contacts': contacts,
    'users': users,
    'users_overseas': users_overseas,
    'invoices': invoices,
    'versioned_invoices': versioned_invoices,
    'payments': payments,
    'empty': empty,
    'restricted': user_restricted_access,
    'peopleinvoices': users_invoices,
    'companies': companies,
    'internal_transactions': internal_transactions,
}
