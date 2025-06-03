# -*- coding: utf-8 -*-

"""
    Eve
    ~~~

    An out-of-the-box REST Web API that's as dangerous as you want it to be.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.

    .. versionchanged:: 0.5
       'SERVER_NAME' removed.
       'QUERY_WHERE' added.
       'QUERY_SORT' added.
       'QUERY_PAGE' added.
       'QUERY_MAX_RESULTS' added.
       'QUERY_PROJECTION' added.
       'QUERY_EMBEDDED' added.
       'RFC1123_DATE_FORMAT' added.

    .. versionchanged:: 0.4
       'META' defaults to '_meta'.
       'ERROR' defaults to '_error'.
       Remove unnecessary commented code.

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

__version__ = "2.2.1"

# RFC 1123 (ex RFC 822)
DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
RFC1123_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

URL_PREFIX = ""
API_VERSION = ""
PAGINATION = True
PAGINATION_LIMIT = 50
PAGINATION_DEFAULT = 25
ID_FIELD = "_id"
CACHE_CONTROL = "max-age=10,must-revalidate"  # TODO confirm this value
CACHE_EXPIRES = 10

ALLOW_CUSTOM_FIELDS_IN_GEOJSON = False

RESOURCE_METHODS = ["GET"]
ITEM_METHODS = ["GET"]
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD
ITEM_URL = 'regex("[a-f0-9]{24}")'

STATUS_OK = "OK"
STATUS_ERR = "ERR"
LAST_UPDATED = "_updated"
DATE_CREATED = "_created"
ISSUES = "_issues"
STATUS = "_status"
ERROR = "_error"
ITEMS = "_items"
LINKS = "_links"
ETAG = "_etag"
VERSION = "_version"
META = "_meta"
INFO = None

QUERY_WHERE = "where"
QUERY_SORT = "sort"
QUERY_PAGE = "page"
QUERY_MAX_RESULTS = "max_results"
QUERY_EMBEDDED = "embedded"
QUERY_PROJECTION = "projection"

VALIDATION_ERROR_STATUS = 422
VALIDATION_ERROR_AS_LIST = False

# must be the last line (will raise W402 on pyflakes)
from eve.flaskapp import Eve  # noqa
