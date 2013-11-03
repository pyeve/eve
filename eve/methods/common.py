# -*- coding: utf-8 -*-

"""
    eve.methods.common
    ~~~~~~~~~~~~~~~~~~

    Utility functions for API methods implementations.

    :copyright: (c) 2013 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import time
from datetime import datetime
from flask import current_app as app, request, abort, g, Response
import simplejson as json
from functools import wraps
from eve.utils import parse_request, document_etag, config, request_method, \
    debug_error_message


def get_document(resource, **lookup):
    """ Retrieves and return a single document. Since this function is used by
    the editing methods (POST, PATCH, DELETE), we make sure that the client
    request references the current representation of the document before
    returning it.

    :param resource: the name of the resource to which the document belongs to.
    :param **lookup: document lookup query

    .. versionchanged:: 0.0.9
       More informative error messages.

    .. versionchanged:: 0.0.5
      Pass current resource to ``parse_request``, allowing for proper
      processing of new configuration settings: `filters`, `sorting`, `paging`.
    """
    req = parse_request(resource)
    document = app.data.find_one(resource, **lookup)
    if document:

        if not req.if_match:
            # we don't allow editing unless the client provides an etag
            # for the document
            abort(403, description=debug_error_message(
                'An etag must be provided to edit a document'
            ))

        # ensure the retrieved document has LAST_UPDATED and DATE_CREATED,
        # eventually with same default values as in GET.
        document[config.LAST_UPDATED] = last_updated(document)
        document[config.DATE_CREATED] = date_created(document)

        if req.if_match != document_etag(document):
            # client and server etags must match, or we don't allow editing
            # (ensures that client's version of the document is up to date)
            abort(412, description=debug_error_message(
                'Client and server etags don\'t match'
            ))

    return document


def parse(value, resource):
    """ Safely evaluates a string containing a Python expression. We are
    receiving json and returning a dict.

    :param value: the string to be evaluated.
    :param resource: name of the involved resource.

    .. versionchanged:: 0.1.1
       Serialize data-specific values as needed.

    .. versionchanged:: 0.1.0
       Support for PUT method.

    .. versionchanged:: 0.0.5
       Support for 'application/json' Content-Type.

    .. versionchanged:: 0.0.4
       When parsing POST requests, eventual default values are injected in
       parsed documents.
    """

    try:
        # assume it's not decoded to json yet (request Content-Type = form)
        document = json.loads(value)
    except:
        # already a json
        document = value

    # if needed, get field values serialized by the data diver being used.
    # If any error occurs, assume validation will take care of it (i.e. a badly
    # formatted objectid).
    try:
        document = serialize(document, resource)
    except:
        pass

    return document


def payload():
    """ Performs sanity checks or decoding depending on the Content-Type,
    then returns the request payload as a dict. If request Content-Type is
    unsupported, aborts with a 400 (Bad Request).

    .. versionchanged:: 0.1.1
       Payload returned as a standard python dict regardless of request content
       type.

    .. versionchanged:: 0.0.9
       More informative error messages.
       request.get_json() replaces the now deprecated request.json


    .. versionchanged:: 0.0.7
       Native Flask request.json preferred over json.loads.

    .. versionadded: 0.0.5
    """
    content_type = request.headers['Content-Type'].split(';')[0]

    if content_type == 'application/json':
        return request.get_json()
    elif content_type == 'application/x-www-form-urlencoded':
        return request.form.to_dict() if len(request.form) else \
            abort(400, description=debug_error_message(
                'No form-urlencoded data supplied'
            ))
    else:
        abort(400, description=debug_error_message(
            'Unknown or no Content-Type header supplied'))


class RateLimit(object):
    """ Implements the Rate-Limiting logic using Redis as a backend.

    :param key_prefix: the key used to uniquely identify a client.
    :param limit: requests limit, per period.
    :param period: limit validity period
    :param send_x_headers: True if response headers are supposed to include
                           special 'X-RateLimit' headers

    .. versionadded:: 0.0.7
    """
    # We give the key extra expiration_window seconds time to expire in redis
    # so that badly synchronized clocks between the workers and the redis
    # server do not cause problems
    expiration_window = 10

    def __init__(self, key_prefix, limit, period, send_x_headers=True):
        self.reset = (int(time.time()) // period) * period + period
        self.key = key_prefix + str(self.reset)
        self.limit = limit
        self.period = period
        self.send_x_headers = send_x_headers
        p = app.redis.pipeline()
        p.incr(self.key)
        p.expireat(self.key, self.reset + self.expiration_window)
        self.current = min(p.execute()[0], limit + 1)

    remaining = property(lambda x: x.limit - x.current)
    over_limit = property(lambda x: x.current > x.limit)


def get_rate_limit():
    """ If available, returns a RateLimit instance which is valid for the
    current request-response.

    .. versionadded:: 0.0.7
    """
    return getattr(g, '_rate_limit', None)


def ratelimit():
    """ Enables support for Rate-Limits on API methods
    The key is constructed by default from the remote address or the
    authorization.username if authentication is being used. On
    a authentication-only API, this will impose a ratelimit even on
    non-authenticated users, reducing exposure to DDoS attacks.

    Before the function is executed it increments the rate limit with the help
    of the RateLimit class and stores an instance on g as g._rate_limit. Also
    if the client is indeed over limit, we return a 429, see
    http://tools.ietf.org/html/draft-nottingham-http-new-status-04#section-4

    .. versionadded:: 0.0.7
    """
    def decorator(f):
        @wraps(f)
        def rate_limited(*args, **kwargs):
            method_limit = app.config.get('RATE_LIMIT_' + request_method())
            if method_limit and app.redis:
                limit = method_limit[0]
                period = method_limit[1]
                # If authorization is being used the key is 'username'.
                # Else, fallback to client IP.
                key = 'rate-limit/%s' % (request.authorization.username
                                         if request.authorization else
                                         request.remote_addr)
                rlimit = RateLimit(key, limit, period, True)
                if rlimit.over_limit:
                    return Response('Rate limit exceeded', 429)
                # store the rate limit for further processing by
                # send_response
                g._rate_limit = rlimit
            else:
                g._rate_limit = None
            return f(*args, **kwargs)
        return rate_limited
    return decorator


def last_updated(document):
    """Fixes document's LAST_UPDATED field value. Flask-PyMongo returns
    timezone-aware values while stdlib datetime values are timezone-naive.
    Comparisions between the two would fail.

    If LAST_UPDATE is missing we assume that it has been created outside of the
    API context and inject a default value, to allow for proper computing of
    Last-Modified header tag. By design all documents return a LAST_UPDATED
    (and we don't want to break existing clients).

    :param document: the document to be processed.

    .. versionchanged:: 0.1.0
       Moved to common.py and renamed as public, so it can also be used by edit
       methods (via get_document()).

    .. versionadded:: 0.0.5
    """
    if config.LAST_UPDATED in document:
        return document[config.LAST_UPDATED].replace(tzinfo=None)
    else:
        return epoch()


def date_created(document):
    """If DATE_CREATED is missing we assume that it has been created outside of
    the API context and inject a default value. By design all documents
    return a DATE_CREATED (and we dont' want to break existing clients).

    :param document: the document to be processed.

    .. versionchanged:: 0.1.0
       Moved to common.py and renamed as public, so it can also be used by edit
       methods (via get_document()).

    .. versionadded:: 0.0.5
    """
    return document[config.DATE_CREATED] if config.DATE_CREATED in document \
        else epoch()


def epoch():
    """ A datetime.min alternative which won't crash on us.

    .. versionchanged:: 0.1.0
       Moved to common.py and renamed as public, so it can also be used by edit
       methods (via get_document()).

    .. versionadded:: 0.0.5
    """
    return datetime(1970, 1, 1)


def serialize(document, resource=None, schema=None):
    """Recursively handles field values that require data-aware serialization.
    Relies on the app.data.serializers dictionary.

    .. versionadded:: 0.1.1
    """
    if app.data.serializers:
        if resource:
            schema = config.DOMAIN[resource]['schema']
        for field in document:
            if field in schema:
                field_schema = schema[field]
                field_type = field_schema['type']
                if 'schema' in field_schema:
                    field_schema = field_schema['schema']
                    if 'dict' in (field_type, field_schema.get('type', '')):
                        # either a dict or a list of dicts
                        embedded = [document[field]] if field_type == 'dict' \
                            else document[field]
                        for subdocument in embedded:
                            if 'schema' in field_schema:
                                serialize(subdocument,
                                          schema=field_schema['schema'])
                    else:
                        # a list of one type, arbirtrary length
                        field_type = field_schema['type']
                        if field_type in app.data.serializers:
                            i = 0
                            for v in document[field]:
                                document[field][i] = \
                                    app.data.serializers[field_type](v)
                                i += 1
                elif 'items' in field_schema:
                    # a list of multiple types, fixed length
                    i = 0
                    for s, v in zip(field_schema['items'], document[field]):
                        field_type = s['type'] if 'type' in s else None
                        if field_type in app.data.serializers:
                            document[field][i] = \
                                app.data.serializers[field_type](
                                    document[field][i])
                        i += 1
                elif field_type in app.data.serializers:
                    # a simple field
                    document[field] = \
                        app.data.serializers[field_type](document[field])
    return document


def resolve_default_values(document, resource):
    """Add any defined default value for missing document fields.

    :param document: the document being posted or replaced
    :param resource: the resource to which the document belongs

    .. versionadded:: 0.2
    """
    if request_method() in ('POST', 'PUT'):
        defaults = app.config['DOMAIN'][resource]['defaults']
        missing_defaults = defaults.difference(set(document.keys()))
        schema = config.DOMAIN[resource]['schema']
        for missing_field in missing_defaults:
            document[missing_field] = schema[missing_field]['default']
