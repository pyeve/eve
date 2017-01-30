# -*- coding: utf-8 -*-

"""
    eve.settings
    ~~~~~~~~~~~~

    Default API settings. These can be overridden by editing this file or, more
    appropriately, by using a custom settings module (see the optional
    'settings' argument or the EVE_SETTING environment variable).

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.

    .. versionchanged:: 0.7
       'OPTIMIZE_PAGINATION_FOR_SPEED' added and set to False.
       'OPLOG_RETURN_EXTRA_FIELD' added and set to False.
       'ENFORCE_IF_MATCH'added and set to True.
       'X_DOMAINS_RE' added and set to None

    .. versionchanged:: 0.6
       'UPSERT_ON_PUT? added and set to True.
       'STANDARD_ERRORS' added.
       'JSONP_ARGUMENT' added and set to None.
       'HEADER_TOTAL_COUNT' added and set to 'X-Total-Count'.
       'RETURN_MEDIA_AS_URL' added and set to None.
       'MEDIA_ENDPOINT' added and set to 'media'.
       'MEDIA_URL' added and set to regex("[a-f0-9]{24}").
       'SOFT_DELETE' added and set to False.
       'DELETED' added and set to '_deleted'.
       'SHOW_DELETED_PARAM' added and set to 'show_deleted'.
       'SCHEMA_ENDPOINT' added and set to None

    .. versionchanged:: 0.5
       'SERVER_NAME' removed.
       'URL_PROTOCOL' removed.
       'OPLOG' added and set to False.
       'OPLOG_NAME' added and set to 'oplog'.
       'OPLOG_METHODS' added and set to all edit operations.
       'OPLOG_ENDPOINT' added and set to None.
       'OPLOG_AUDIT' added and set to True.
       'QUERY_WHERE' added and set to 'where'
       'QUERY_PROJECTION' added and set to 'projection'
       'QUERY_SORT' added and set to 'sort'
       'QUERY_PAGE' added and set to 'page'
       'QUERY_MAX_RESULTS' added and set to 'max_results'
       'QUERY_EMBEDDED' added and set to 'embedded'
       'INTERNAL_RESOURCE' added and set to False

    .. versionchanged:: 0.4
       'META' added and set to '_meta'.
       'ERROR' added and set to '_error'.
       'URL_PROTOCOL' added and set to ''.
       'BANDWIDTH_SAVER' added and set to True.
       'VERSION' added and set to '_version'.
       'VERSIONS' added and set to '_versions'.
       'VERSIONING' added and set to False.
       'VERSION_PARAM' added and set to 'version'.
       'LATEST_VERSION' added and set to '_latest_version'.
       'VERSION_ID_SUFFIX' added and set to '_document'.
       'VERSION_DIFF_INCLUDE' added and set to [].

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
# DEBUG = True

# RFC 1123 (ex RFC 822)
DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'

STATUS_OK = "OK"
STATUS_ERR = "ERR"
LAST_UPDATED = '_updated'
DATE_CREATED = '_created'
ISSUES = '_issues'
STATUS = '_status'
ERROR = '_error'
ITEMS = '_items'
LINKS = '_links'
ETAG = '_etag'
VERSION = '_version'            # field that stores the version number
DELETED = '_deleted'            # field to store soft delete status
META = '_meta'
INFO = None
VALIDATION_ERROR_STATUS = 422

# return a single field validation error as a list (by default a single error
# is retuned as string, while multiple errors are returned as a list).
VALIDATION_ERROR_AS_LIST = False

# codes for which we want to return a standard response which includes
# a JSON body with the status, code, and description.
STANDARD_ERRORS = [400, 401, 404, 405, 406, 409, 410, 412, 422, 428]

# field returned on GET requests so we know if we have the latest copy even if
# we access a specific version
LATEST_VERSION = '_latest_version'

# appended to ID_FIELD, holds the original document id in parallel collection
VERSION_ID_SUFFIX = '_document'
VERSION_DIFF_INCLUDE = []       # always include these fields when diffing

API_VERSION = ''
URL_PREFIX = ''
ID_FIELD = '_id'
CACHE_CONTROL = ''
CACHE_EXPIRES = 0
ITEM_CACHE_CONTROL = ''
X_DOMAINS = None                # CORS disabled by default.
X_DOMAINS_RE = None             # CORS disabled by default.
X_HEADERS = None                # CORS disabled by default.
X_EXPOSE_HEADERS = None         # CORS disabled by default.
X_ALLOW_CREDENTIALS = None      # CORS disabled by default.
X_MAX_AGE = 21600               # Access-Control-Max-Age when CORS is enabled
HATEOAS = True                  # HATEOAS enabled by default.
IF_MATCH = True                 # IF_MATCH (ETag match) enabled by default.
ENFORCE_IF_MATCH = True         # ENFORCE_IF_MATCH enabled by default.

ALLOWED_FILTERS = ['*']         # filtering enabled by default
VALIDATE_FILTERS = False
SORTING = True                  # sorting enabled by default.
JSON_SORT_KEYS = False          # json key sorting
EMBEDDING = True                # embedding enabled by default
PROJECTION = True               # projection enabled by default
PAGINATION = True               # pagination enabled by default.
PAGINATION_LIMIT = 50
PAGINATION_DEFAULT = 25
VERSIONING = False              # turn document versioning on or off.
VERSIONS = '_versions'          # suffix for parallel collection w/old versions
VERSION_PARAM = 'version'       # URL param for specific version of a document.
INTERNAL_RESOURCE = False       # resources are public by default.
JSONP_ARGUMENT = None           # JSONP disabled by default.
SOFT_DELETE = False             # soft delete disabled by default.
SHOW_DELETED_PARAM = 'show_deleted'
BULK_ENABLED = True

OPLOG = False                   # oplog is disabled by default.
OPLOG_NAME = 'oplog'            # default oplog resource name.
OPLOG_ENDPOINT = None           # oplog endpoint is disabled by default.
OPLOG_AUDIT = True              # oplog audit enabled by default.
OPLOG_METHODS = ['DELETE',
                 'POST',
                 'PATCH',
                 'PUT']         # oplog logs all operations by default.
OPLOG_CHANGE_METHODS = ['DELETE',
                        'PATCH',
                        'PUT']  # methods which write changes to the oplog
OPLOG_RETURN_EXTRA_FIELD = False    # oplog does not return the 'extra' field.

RESOURCE_METHODS = ['GET']
ITEM_METHODS = ['GET']
PUBLIC_METHODS = []
ALLOWED_ROLES = []
ALLOWED_READ_ROLES = []
ALLOWED_WRITE_ROLES = []
PUBLIC_ITEM_METHODS = []
ALLOWED_ITEM_ROLES = []
ALLOWED_ITEM_READ_ROLES = []
ALLOWED_ITEM_WRITE_ROLES = []
# globally enables / disables HTTP method overriding
ALLOW_OVERRIDE_HTTP_METHOD = True
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD
ITEM_URL = 'regex("[a-f0-9]{24}")'
UPSERT_ON_PUT = True            # insert unexisting documents on PUT.

# use a simple file response format by default
EXTENDED_MEDIA_INFO = []
RETURN_MEDIA_AS_BASE64_STRING = True
RETURN_MEDIA_AS_URL = False
MEDIA_ENDPOINT = 'media'
MEDIA_URL = 'regex("[a-f0-9]{24}")'
MEDIA_BASE_URL = None

MULTIPART_FORM_FIELDS_AS_JSON = False
AUTO_COLLAPSE_MULTI_KEYS = False
AUTO_CREATE_LISTS = False

SCHEMA_ENDPOINT = None

# list of extra fields to be included with every POST response. This list
# should not include the 'standard' fields (ID_FIELD, LAST_UPDATED,
# DATE_CREATED, and ETAG). Only relevant when bandwidth saving mode is on.
EXTRA_RESPONSE_FIELDS = []
BANDWIDTH_SAVER = True

# default query parameters
QUERY_WHERE = 'where'
QUERY_PROJECTION = 'projection'
QUERY_SORT = 'sort'
QUERY_PAGE = 'page'
QUERY_MAX_RESULTS = 'max_results'
QUERY_EMBEDDED = 'embedded'
QUERY_AGGREGATION = 'aggregate'

HEADER_TOTAL_COUNT = 'X-Total-Count'
OPTIMIZE_PAGINATION_FOR_SPEED = False

# user-restricted resource access is disabled by default.
AUTH_FIELD = None

# don't allow unknown key/value pairs for POST/PATCH payloads.
ALLOW_UNKNOWN = False

# don't ignore unknown schema rules (raise SchemaError)
TRANSPARENT_SCHEMA_RULES = False

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
MONGO_OPTIONS = {
    'connect': True
}
# Compatibility for flask-pymongo.
MONGO_CONNECT = MONGO_OPTIONS['connect']
