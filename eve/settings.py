"""
    eve.settings
    ~~~~~~~~~~~~

    Default API settings. These can be overridden by editing this file or, more
    appropriately, by using a custom settings module (see the optional
    'settings' argument or the EVE_SETTING environment variable).

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
#MONGO_HOST = 'localhost'
#MONGO_PORT = 27017
#MONGO_USERNAME = 'user'
#MONGO_PASSWORD = 'user'
#MONGO_DBNAME = 'apitest'
#ID_FIELD = '_id'
MONGO_HOST = 'alex.mongohq.com'
MONGO_PORT = 10068
MONGO_USERNAME = 'heroku'
MONGO_PASSWORD = 'heroku'
MONGO_DBNAME = 'app9195931'
ID_FIELD = '_id'


RESOURCE_METHODS = ['GET', 'POST']               # defauts to GET
ITEM_METHODS = ['GET', 'PATCH', 'DELETE']       # defaults to GET
ITEM_CACHE_CONTROL = ''                         # TODO defaults to...
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD                    # defaults to '_id'
ITEM_URL = '[a-f0-9]{24}'                       # defaults to _id regex

contacts = {
    'url': 'contatti',                      # defaults to resource key
    'cache_control': 'max-age=20,must-revalidate',
    'cache_expires': 20,
    'item_title': 'contatto',
    'additional_lookup': {
        'url': '[\w]+',   # to be unique field
        'field': 'name'
    },
    'schema': {
        'name': {
            'type': 'string',
            'minlength': 2,
            #'maxlength': 5,
            'unique': True,
        },
        'role': {
            'type': 'list',
            'allowed': ["agent", "client", "vendor"],
        },
        'rows': {
            #'readonly': True,
            'type': 'list',
            'items': {
                'sku': {'type': 'string'},
                'price': {'type': 'integer'},
            }
        },
        'alist': {
            #'readonly': True,
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
        'cin': {
            'type': 'string',
            'cin': True,
        },
    }
}

invoices = {
    'item_lookup': False,
    'schema': {},
}

DOMAIN = {
    'contacts': contacts,
    #'invoices': invoices,
}
