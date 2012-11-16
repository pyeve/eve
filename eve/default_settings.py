"""
    eve.settings
    ~~~~~~~~~~~~

    Default API settings. These can be overridden by editing this file or, more
    appropriately, by using a custom settings module (see the optional
    'settings' argument or the EVE_SETTING environment variable).

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
DEBUG = True

# RFC 1123 (ex RFC 822)
DATE_FORMAT = '%a, %d %b %Y %H:%M:%S UTC'

URL_PREFIX = ''
#BASE_URI = 'localhost:5000'
SERVER_NAME = 'localhost:5000'
PAGING_LIMIT = 50
PAGING_DEFAULT = 25
LAST_UPDATED = 'updated'
DATE_CREATED = 'date_created'
#DEFAULT_DB = 'mongo'
ID_FIELD = '_id'
CACHE_CONTROL = 'max-age=10,must-revalidate'        # TODO confirm this value
CACHE_EXPIRES = 10

RESOURCE_METHODS = ['GET']
ITEM_METHODS = ['GET']
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD
ITEM_URL = '[a-f0-9]{24}'

STATUS_OK = "OK"
STATUS_ERR = "ERR"

SERVER_NAME = 'localhost:5000'
ID_FIELD = '_id'
