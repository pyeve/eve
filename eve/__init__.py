# -*- coding: utf-8 -*-

"""
    Eve
    ~~~

    An out-of-the-box REST Web API that's as dangerous as you want it to be.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.

    .. versionchanged:: 0.2
       'LINKS' defaults to '_links'.
       'ITEMS' defaults to '_items'.
       'STATUS' defaults to 'status'.
       'ISSUES' defaults to 'issues'.

    .. versionchanged:: 0.1.1
       'SERVER_NAME' defaults to None.

    .. versionchagned:: 0.0.9
       'DATE_FORMAT now using GMT instead of UTC.

"""

__version__ = '0.3'

#DEBUG = True

# RFC 1123 (ex RFC 822)
DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'

URL_PREFIX = ''
API_VERSION = ''
SERVER_NAME = None
PAGINATION = True
PAGINATION_LIMIT = 50
PAGINATION_DEFAULT = 25
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
LAST_UPDATED = '_updated'
DATE_CREATED = '_created'
ISSUES = '_issues'
STATUS = '_status'
ITEMS = '_items'
LINKS = '_links'
ETAG = '_etag'

# must be the last line (will raise W402 on pyflakes)
from eve.flaskapp import Eve  # noqa
