# -*- coding: utf-8 -*-

"""
    eve.utils
    ~~~~~~~~~

    Utility functions and classes.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import eve
import hashlib
from flask import request
from flask import current_app as app
from datetime import datetime, timedelta
from bson.json_util import dumps
import werkzeug.exceptions


class Config(object):
    """ Helper class used trorough the code to access configuration settings.
    If the main flaskapp object is not instantiated yet, returns the default
    setting in the eve __init__.py module, otherwise returns the flaskapp
    config value (which value might override the static defaults).
    """
    def __getattr__(self, name):
        try:
            # will return 'working outside of application context' if the
            # current_app is not available yet
            return app.config.get(name)
        except:
            # fallback to the module-level default value
            return getattr(eve, name)


# makes an instance of the Config helper class available to all the modules
# importing eve.utils.
config = Config()


class ParsedRequest(object):
    """ This class, by means of its attributes, describes a client request.

    .. versonchanged:: 0.1.0
       'embedded' keyword.

    .. versionchanged:: 0.0.6
       Projection queries ('?projection={"name": 1}')
    """
    # `where` value of the query string (?where). Defaults to None.
    where = None

    # `projection` value of the query string (?projection). Defaults to None.
    projection = None

    # `sort` value of the query string (?sort). Defaults to None.
    sort = None

    # `page` value of the query string (?page). Defaults to 1.
    page = 1

    # `max_result` value of the query string (?max_results). Defaults to
    # `PAGINATION_DEFAULT` unless pagination is disabled.
    max_results = 0

    # `If-Modified-Since` request header value. Defaults to None.
    if_modified_since = None

    # `If-None_match` request header value. Defaults to None.
    if_none_match = None

    # `If-Match` request header value. Default to None.
    if_match = None

    # `embedded` value of the query string (?embedded). Defaults to None.
    embedded = None


def parse_request(resource):
    """ Parses a client request, returning instance of :class:`ParsedRequest`
    containing relevant request data.

    :param resource: the resource currently being accessed by the client.

    .. versionchagend:: 0.1.0
       Support for embedded documents.

    .. versionchanged:: 0.0.6
       projection queries ('?projection={"name": 1}')

    .. versionchanged: 0.0.5
       Support for optional filters, sorting and pagination.
    """
    args = request.args
    headers = request.headers

    r = ParsedRequest()

    if config.DOMAIN[resource]['allowed_filters']:
        r.where = args.get('where')
    if config.DOMAIN[resource]['projection']:
        r.projection = args.get('projection')
    if config.DOMAIN[resource]['sorting']:
        r.sort = args.get('sort')
    if config.DOMAIN[resource]['embedding']:
        r.embedded = args.get('embedded')

    max_results_default = config.PAGINATION_DEFAULT if \
        config.DOMAIN[resource]['pagination'] else 0
    try:
        r.max_results = int(float(args['max_results']))
        assert r.max_results > 0
    except (ValueError, werkzeug.exceptions.BadRequestKeyError,
            AssertionError):
        r.max_results = max_results_default

    if config.DOMAIN[resource]['pagination']:
        # TODO should probably return a 400 if 'page' is < 1 or non-numeric
        if 'page' in args:
            try:
                r.page = abs(int(args.get('page'))) or 1
            except ValueError:
                pass

        # TODO should probably return a 400 if 'max_results' < 1 or
        # non-numeric
        if r.max_results > config.PAGINATION_LIMIT:
            r.max_results = config.PAGINATION_LIMIT

    if headers:
        r.if_modified_since = weak_date(headers.get('If-Modified-Since'))
        # TODO if_none_match and if_match should probably be validated as
        # valid etags, returning 400 on fail. Not sure however since
        # we're just going to use these for string-type comparision
        r.if_none_match = headers.get('If-None-Match')
        r.if_match = headers.get('If-Match')

    return r


def weak_date(date):
    """ Returns a RFC-1123 string corresponding to a datetime value plus
    a 1 second timedelta. This is needed because when saved, documents
    LAST_UPDATED values have higher resolution than If-Modified-Since's, which
    is limited to seconds.

    :param date: the date to be adjusted.
    """
    return str_to_date(date) + timedelta(seconds=1) if date else None


def str_to_date(string):
    """ Converts a RFC-1123 string to the corresponding datetime value.

    :param string: the RFC-1123 string to convert to datetime value.
    """
    return datetime.strptime(string, config.DATE_FORMAT) if string else None


def date_to_str(date):
    """ Converts a datetime value to the corresponding RFC-1123 string.

    :param date: the datetime value to convert.
    """
    return datetime.strftime(date, config.DATE_FORMAT) if date else None


def collection_link(resource):
    """ Returns a link to a resource endpoint.

    :param resource: the resource name.

    .. versionchanged:: 0.2
       Use new 'resource_title' setting for link title.

    .. versionchanged:: 0.0.3
       Now returning a JSON link
    """
    return {'title': '%s' % config.DOMAIN[resource]['resource_title'],
            'href': '%s' % resource_uri(resource)}


def document_link(resource, document_id):
    """ Returns a link to a document endpoint.

    :param resource: the resource name.
    :param document_id: the document unique identifier.

    .. versionchanged:: 0.1.0
       No more trailing slashes in links.

    .. versionchanged:: 0.0.3
       Now returning a JSON link
    """
    return {'title': '%s' % config.DOMAIN[resource]['item_title'],
            'href': '%s/%s' % (resource_uri(resource), document_id)}


def home_link():
    """ Returns a link to the API entry point/home page.

    .. versionchanged:: 0.1.1
       Handle the case of SERVER_NAME being None.

    .. versionchanged:: 0.0.3
       Now returning a JSON link.
    """
    server_name = config.SERVER_NAME if config.SERVER_NAME else ''
    return {'title': 'home',
            'href': '%s%s' % (server_name, api_prefix())}


def resource_uri(resource):
    """ Returns the absolute URI to a resource.

    .. versionchanged:: 0.1.1
       URL prefixes are now included in config.URLS items, no more need to
       explicitly add them to resource links.

       Handle the case of SERVER_NAME being None.

    .. versionchanged:: 0.1.0
       No more trailing slashes in links.

    :param resource: the resource name.
    """
    prefix = config.SERVER_NAME if config.SERVER_NAME else ''
    if config.URL_PREFIX:
        prefix += '/%s' % config.URL_PREFIX
    if config.API_VERSION:
        prefix += '/%s' % config.API_VERSION
    return '%s/%s' % (prefix, config.URLS[resource])


def api_prefix(url_prefix=None, api_version=None):
    """ Returns the prefix to API endpoints, according to the URL_PREFIX and
    API_VERSION  configuration settings.

    :param url_prefix: the prefix string. If `None`, defaults to the current
                       :class:`~eve.flaskapp` configuration setting.
                       The class itself will call this function while
                       initializing. In that case, it will pass its settings
                       as arguments (as they are not externally available yet)
    :param api_version: the api version string. If `None`, defaults to the
                        current :class:`~eve.flaskapp` configuration setting.
                        The class itself will call this function while
                        initializing. In that case, it will pass its settings
                        as arguments (as they are not externally available yet)

    .. versionadded:: 0.0.3
    """

    if url_prefix is None:
        url_prefix = config.URL_PREFIX
    if api_version is None:
        api_version = config.API_VERSION

    prefix = '/%s' % url_prefix if url_prefix else ''
    version = '/%s' % api_version if api_version else ''
    return prefix + version


def querydef(max_results=config.PAGINATION_DEFAULT, where=None, sort=None,
             page=None):
    """ Returns a valid query string.

    :param max_results: `max_result` part of the query string. Defaults to
                        `PAGINATION_DEFAULT`
    :param where: `where` part of the query string. Defaults to None.
    :param sort: `sort` part of the query string. Defaults to None.
    :param page: `page` parte of the query string. Defaults to None.
    """
    where_part = '&where=%s' % where if where else ''
    sort_part = '&sort=%s' % sort if sort else ''
    page_part = '&page=%s' % page if page and page > 1 else ''
    max_results_part = 'max_results=%s' % max_results \
        if max_results != config.PAGINATION_DEFAULT else ''

    return ('?' + ''.join([max_results_part, where_part, sort_part,
                           page_part]).lstrip('&')).rstrip('?')


def document_etag(value):
    """ Computes and returns a valid ETag for the input value.

    :param value: the value to compute the ETag with.

    .. versionchanged:: 0.0.4
       Using bson.json_util.dumps over str(value) to make etag computation
       consistent between different runs and/or server instances (#16).
    """
    h = hashlib.sha1()
    h.update(dumps(value, sort_keys=True).encode('utf-8'))
    return h.hexdigest()


def extract_key_values(key, d):
    """ Extracts all values that match a key, even in nested dicts.

    :param key: the lookup key.
    :param d: the dict to scan.

    .. versionadded: 0.0.7
    """
    if key in d:
        yield d[key]
    for k in d:
        if isinstance(d[k], dict):
            for j in extract_key_values(key, d[k]):
                yield j


def request_method():
    """ Returns the proper request method, also taking into account the
    possibile override requested by the client (via 'X-HTTP-Method-Override'
    header).

    .. versionchanged: 0.1.0
       Supports overriding of any HTTP Method (#95).

    .. versionadded: 0.0.7
    """
    return request.headers.get('X-HTTP-Method-Override', request.method)


def debug_error_message(msg):
    """ Returns the error message `msg` if config.DEBUG is True
    otherwise returns `None` which will cause Werkzeug to provide
    a generic error message

    :param msg: The error message to return if config.DEBUG is True

    .. versionadded: 0.0.9
    """
    if getattr(config, 'DEBUG', False):
        return msg
    return None


def validate_filters(where, resource):
    """ Report any filter which is not allowed by  `allowed_filters`

    :param where: the where clause, as a dict.
    :param resource: the resource being inspected.

    .. versionadded: 0.0.9
    """
    allowed = config.DOMAIN[resource]['allowed_filters']
    if '*' not in allowed:
        for filt, _ in where.items():
            if filt not in allowed:
                return "filter on '%s' not allowed" % filt
    return None
