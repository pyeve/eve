# -*- coding: utf-8 -*-

"""
    eve.settings
    ~~~~~~~~~~~~

    Default API settings. These can be overridden by editing this file or, more
    appropriately, by using a custom settings module (see the optional
    'settings' argument or the EVE_SETTING environment variable).

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.

    .. versionchanged:: 0.0.5
       'X_DOMAIN' keyword added to support Cross-Origin Resource Sharing CORS
"""
#DEBUG = True

# RFC 1123 (ex RFC 822)
DATE_FORMAT = '%a, %d %b %Y %H:%M:%S UTC'


API_VERSION = ''
URL_PREFIX = ''
SERVER_NAME = 'localhost:5000'
LAST_UPDATED = 'updated'
DATE_CREATED = 'created'
ID_FIELD = '_id'
CACHE_CONTROL = ''
CACHE_EXPIRES = 0
ITEM_CACHE_CONTROL = ''
X_DOMAINS = None                # CORS disabled by default.

FILTERS = True                  # filters enbaled by default.
SORTING = True                  # sorting enabled by default.
PAGINATION = True               # pagination enabled by default.
PAGINATION_LIMIT = 50
PAGINATION_DEFAULT = 25

RESOURCE_METHODS = ['GET']
ITEM_METHODS = ['GET']
PUBLIC_METHODS = []
ALLOWED_ROLES = None
PUBLIC_ITEM_METHODS = []
ALLOWED_ITEM_ROLES = None
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD
ITEM_URL = '[a-f0-9]{24}'

AUTH_USERNAME_FIELD = None      # Restrict API to user resources

STATUS_OK = "OK"
STATUS_ERR = "ERR"
