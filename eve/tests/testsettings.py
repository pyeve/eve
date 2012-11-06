MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_USERNAME = 'test_user'
MONGO_PASSWORD = 'test_pw'
MONGO_DBNAME = 'eve_test'
ID_FIELD = '_id'


RESOURCE_METHODS = ['GET', 'POST']               # defauts to GET
ITEM_METHODS = ['GET', 'PATCH', 'DELETE']       # defaults to GET
ITEM_CACHE_CONTROL = ''                         # TODO defaults to...
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD                    # defaults to '_id'
ITEM_URL = '[a-f0-9]{24}'                       # defaults to _id regex

contacts = {
    'url': 'contactsurl',                      # defaults to resource key
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
    }
}

invoices = {
    'item_lookup': False,
    'methods': ['GET'],
    #'item_methods': ['GET'],
}

DOMAIN = {
    'contacts': contacts,
    'invoices': invoices,
    #'others': {},
}
