# -*- coding: utf-8 -*-

"""
    eve.utils
    ~~~~~~~~~

    Utility functions and classes.

    :copyright: (c) 2015 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import sys
import eve
import hashlib
import werkzeug.exceptions
from copy import copy
from flask import request
from flask import current_app as app
from datetime import datetime, timedelta
from bson.json_util import dumps
from eve import RFC1123_DATE_FORMAT


class Config(object):
    """ Helper class used through the code to access configuration settings.
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

    .. versuinchanged;; 9,5
       'args' keyword.

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

    # `show_deleted` True when the SHOW_DELETED_PARAM is included in query.
    # Only relevant when soft delete is enabled. Defaults to False.
    show_deleted = False

    # `args` value of the original request. Defaults to None.
    args = None


def parse_request(resource):
    """ Parses a client request, returning instance of :class:`ParsedRequest`
    containing relevant request data.

    :param resource: the resource currently being accessed by the client.

    .. versionchanged:: 0.5
       Support for custom query parameters via configuration settings.
       Minor DRY updates.

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
    r.args = args

    settings = config.DOMAIN[resource]
    if settings['allowed_filters']:
        r.where = args.get(config.QUERY_WHERE)
    if settings['projection']:
        r.projection = args.get(config.QUERY_PROJECTION)
    if settings['sorting']:
        r.sort = args.get(config.QUERY_SORT)
    if settings['embedding']:
        r.embedded = args.get(config.QUERY_EMBEDDED)

    r.show_deleted = config.SHOW_DELETED_PARAM in args

    max_results_default = config.PAGINATION_DEFAULT if \
        settings['pagination'] else 0
    try:
        r.max_results = int(float(args[config.QUERY_MAX_RESULTS]))
        assert r.max_results > 0
    except (ValueError, werkzeug.exceptions.BadRequestKeyError,
            AssertionError):
        r.max_results = max_results_default

    if settings['pagination']:
        # TODO should probably return a 400 if 'page' is < 1 or non-numeric
        if config.QUERY_PAGE in args:
            try:
                r.page = abs(int(args.get(config.QUERY_PAGE))) or 1
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
    return datetime.strptime(date, RFC1123_DATE_FORMAT) + \
        timedelta(seconds=1) if date else None


def str_to_date(string):
    """ Converts a date string formatted as defined in the configuration
        to the corresponding datetime value.

    :param string: the RFC-1123 string to convert to datetime value.
    """
    return datetime.strptime(string, config.DATE_FORMAT) if string else None


def date_to_str(date):
    """ Converts a datetime value to the format defined in the configuration file.

    :param date: the datetime value to convert.
    """
    return datetime.strftime(date, config.DATE_FORMAT) if date else None


def date_to_rfc1123(date):
    """ Converts a datetime value to the corresponding RFC-1123 string.

    :param date: the datetime value to convert.
    """
    return datetime.strftime(date, RFC1123_DATE_FORMAT) if date else None


def home_link():
    """ Returns a link to the API entry point/home page.

    .. versionchanged:: 0.5
       Link is relative to API root.

    .. versionchanged:: 0.0.3
       Now returning a JSON link.
    """
    return {'title': 'home', 'href': '/'}


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
             version=None, page=None):
    """ Returns a valid query string.

    :param max_results: `max_result` part of the query string. Defaults to
                        `PAGINATION_DEFAULT`
    :param where: `where` part of the query string. Defaults to None.
    :param sort: `sort` part of the query string. Defaults to None.
    :param page: `version` part of the query string. Defaults to None.
    :param page: `page` part of the query string. Defaults to None.

    .. versionchanged:: 0.5
       Support for customizable query parameters.
       Add version to query string (#475).
    """
    where_part = '&%s=%s' % (config.QUERY_WHERE, where) if where else ''
    sort_part = '&%s=%s' % (config.QUERY_SORT, sort) if sort else ''
    page_part = '&%s=%s' % (config.QUERY_PAGE, page) if page and page > 1 \
        else ''
    version_part = '&%s=%s' % (config.VERSION_PARAM, version) if version \
        else ''
    max_results_part = '%s=%s' % (config.QUERY_MAX_RESULTS, max_results) \
        if max_results != config.PAGINATION_DEFAULT else ''

    # remove sort set by Eve if version is set
    if version and sort is not None:
        sort_part = '&%s=%s' % (config.QUERY_SORT, sort) \
            if sort != '[("%s", 1)]' % config.VERSION else ''

    return ('?' + ''.join([max_results_part, where_part, sort_part,
                           version_part, page_part]).lstrip('&')).rstrip('?')


def document_etag(value, ignore_fields=None):
    """ Computes and returns a valid ETag for the input value.

    :param value: the value to compute the ETag with.
    :param ignore_fields: `ignore_fields` list of fields to skip to
                          compute the ETag value.

    .. versionchanged:: 0.5.4
       Use json_encoder_class. See #624.

    .. versionchanged:: 0.0.4
       Using bson.json_util.dumps over str(value) to make etag computation
       consistent between different runs and/or server instances (#16).
    """
    if ignore_fields:
        def filter_ignore_fields(d, fields):
            # recursive function to remove the fields that they are in d,
            # field is a list of fields to skip or dotted fields to look up
            # to nested keys such as  ["foo", "dict.bar", "dict.joe"]
            for field in fields:
                key, _, value = field.partition(".")
                if value:
                    filter_ignore_fields(d[key], [value])
                elif field in d:
                    d.pop(field)
                else:
                    # not required fields can be not present
                    pass

        value_ = copy(value)
        filter_ignore_fields(value_, ignore_fields)
    else:
        value_ = value

    h = hashlib.sha1()
    json_encoder = app.data.json_encoder_class()
    h.update(dumps(value_, sort_keys=True,
                   default=json_encoder.default).encode('utf-8'))
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

    .. versionchanged: 0.5
       If the data layer supports a list of allowed operators, take them
       into consideration when validating the query string (#388).
       Recursively validate the whole query string.

    .. versionadded: 0.0.9
    """
    operators = getattr(app.data, 'operators', set())
    allowed = config.DOMAIN[resource]['allowed_filters'] + list(operators)

    def validate_filter(filter):
        for key, value in filter.items():
            if key not in allowed:
                return "filter on '%s' not allowed" % key

            if key in ('$or', '$and', '$nor'):
                if not isinstance(value, list):
                    return "operator '%s' expects a list of sub-queries" % key
                for v in value:
                    if not isinstance(v, dict):
                        return "operator '%s' expects a list of sub-queries" \
                            % key
                    r = validate_filter(v)
                    if r:
                        return r
            elif isinstance(value, dict):
                r = validate_filter(value)
                if r:
                    return r

    return validate_filter(where) if '*' not in allowed else None


def auto_fields(resource):
    """ Returns a list of automatically handled fields for a resource.

    :param resource: the resource currently being accessed by the client.

    .. versionchanged: 0.5
       ETAG is now a preserved meta data (#369).

    .. versionadded:: 0.4
    """
    resource_def = config.DOMAIN[resource]

    # preserved meta data
    fields = [resource_def['id_field'], config.LAST_UPDATED,
              config.DATE_CREATED, config.ETAG]

    # on-the-fly meta data (not in data store)
    fields += [config.ISSUES, config.STATUS, config.LINKS]

    if resource_def['versioning'] is True:
        fields.append(config.VERSION)
        fields.append(config.LATEST_VERSION)  # on-the-fly meta data
        fields.append(resource_def['id_field'] + config.VERSION_ID_SUFFIX)

    if resource_def['soft_delete'] is True:
        fields.append(config.DELETED)

    return fields

# Base string type that is compatible with both Python 2.x and 3.x.
str_type = str if sys.version_info[0] == 3 else basestring
