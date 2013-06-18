# -*- coding: utf-8 -*-

"""
    Eve
    ~~~

    An out-of-the-box REST Web API that's as dangerous as you want it to be.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

__version__ = '0.0.7'

#DEBUG = True

# RFC 1123 (ex RFC 822)
DATE_FORMAT = '%a, %d %b %Y %H:%M:%S UTC'

URL_PREFIX = ''
API_VERSION = ''
SERVER_NAME = 'localhost:5000'
PAGINATION = True
PAGINATION_LIMIT = 50
PAGINATION_DEFAULT = 25
LAST_UPDATED = 'updated'
DATE_CREATED = 'created'
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

# must be the last line (will raise W402 on pyflakes)
from flaskapp import Eve  # noqa
