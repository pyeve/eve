# -*- coding: utf-8 -*-

"""
    eve.settings
    ~~~~~~~~~~~~

    Default API settings. These can be overridden by editing this file or, more
    appropriately, by using a custom settings module (see the optional
    'settings' argument or the EVE_SETTING environment variable).

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.

    .. versionchanged:: 0.3
       X_MAX_AGE added and set to 21600.

    .. versionchanged:: 0.2
       IF_MATCH defaults to True.
       'LINKS' defaults to '_links'.
       'ITEMS' defaults to '_items'.
       'STATUS' defaults to 'status'.
       'ISSUES' defaults to 'issues'.
       'regex' is now part of 'ITEM_URL' default string.

    .. versionchanged:: 0.1.1
       'SERVER_NAME' defaults to None.

    .. versionchanged:: 0.1.0
       'EMBEDDING' added and set to True.
       'HATEOAS' added and set to True.

    .. versionchanged:: 0.0.9
       'FILTERS' boolean changed to 'ALLOWED_FILTERS' list.
       'AUTH_USERNAME_FIELD' renamed to 'AUTH_FIELD', and default value set to
       None.
       'DATE_FORMAT now using GMT instead of UTC.

    .. versionchanged:: 0.0.7
       'EXTRA_RESPONSE_FIELDS added and set to an empty list.

    .. versionchanged:: 0.0.6
       'PROJECTION' added and set to True.
       'ALLOW_UNKNOWN' added and set to False.

    .. versionchanged:: 0.0.5
       'AUTH_USERNAME_FIELD' keyword added to support 'user-restricted resource
       access.
       'X_DOMAIN' keyword added to support Cross-Origin Resource Sharing CORS
"""
#DEBUG = True

# RFC 1123 (ex RFC 822)
DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'

STATUS_OK = "OK"
STATUS_ERR = "ERR"
LAST_UPDATED = '_updated'
DATE_CREATED = '_created'
ISSUES = '_issues'
STATUS = '_status'
ITEMS = '_items'
LINKS = '_links'
ETAG = '_etag'

API_VERSION = ''
URL_PREFIX = ''
SERVER_NAME = None
ID_FIELD = '_id'
CACHE_CONTROL = ''
CACHE_EXPIRES = 0
ITEM_CACHE_CONTROL = ''
X_DOMAINS = None                # CORS disabled by default.
X_HEADERS = None                # CORS disabled by default.
X_MAX_AGE = 21600               # Access-Control-Max-Age when CORS is enabled
HATEOAS = True                  # HATEOAS enabled by default.
IF_MATCH = True                 # IF_MATCH (ETag match) enabled by default.

ALLOWED_FILTERS = ['*']         # filtering enabled by default
SORTING = True                  # sorting enabled by default.
EMBEDDING = True                # embedding enabled by default
PROJECTION = True               # projection enabled by default
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
ITEM_URL = 'regex("[a-f0-9]{24}")'

# list of extra fields to be included with every POST response. This list
# should not include the 'standard' fields (ID_FIELD, LAST_UPDATED,
# DATE_CREATED,ETAG).
EXTRA_RESPONSE_FIELDS = []


AUTH_FIELD = None               # user-restricted resource access is disabled
                                # by default.

ALLOW_UNKNOWN = False           # don't allow unknown key/value pairs for
                                # POST/PATCH payloads.

# Rate limits are disabled by default. Needs a running redis-server.
RATE_LIMIT_GET = None
RATE_LIMIT_POST = None
RATE_LIMIT_PATCH = None
RATE_LIMIT_DELETE = None

# MONGO defaults
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
# disallow Mongo's javascript queries as they might be vulnerable to injection
# attacks ('ReDoS' especially), are probably too complex for the average API
# end-user and finally can  seriously impact overall performance.
MONGO_QUERY_BLACKLIST = ['$where', '$regex']
# Explicitly set default write_concern to 'safe' (do regular
# aknowledged writes). This is also the current PyMongo/Mongo default setting.
MONGO_WRITE_CONCERN = {'w': 1}
