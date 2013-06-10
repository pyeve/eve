# -*- coding: utf-8 -*-

"""
    eve.methods.common
    ~~~~~~~~~~~~~~~~~~

    Utility functions for API methods implementations.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import time
from flask import current_app as app, request, abort, g, Response
import simplejson as json
from ..utils import str_to_date, parse_request, document_etag, config, \
    request_method
from functools import wraps


def get_document(resource, **lookup):
    """ Retrieves and return a single document. Since this function is used by
    the editing methods (POST, PATCH, DELETE), we make sure that the client
    request references the current representation of the dcument before
    returning it.

    :param resource: the name of the resource to which the document belongs to.
    :param **lookup: document lookup query

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
            abort(403)

        document[config.LAST_UPDATED] = document[config.LAST_UPDATED].replace(
            tzinfo=None)
        if req.if_match != document_etag(document):
            # client and server etags must match, or we don't allow editing
            # (ensures that client's version of the document is up to date)
            abort(412)

    return document


def parse(value, resource):
    """ Safely evaluates a string containing a Python expression. We are
    receiving json and returning a dict.

    :param value: the string to be evaluated.
    :param resource: name of the involved resource.

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

    # By design, dates are expressed as RFC-1123 strings. We convert them
    # to proper datetimes.
    dates = app.config['DOMAIN'][resource]['dates']
    document_dates = dates.intersection(set(document.keys()))
    for date_field in document_dates:
        document[date_field] = str_to_date(document[date_field])

    # update the document with eventual default values
    if request_method() == 'POST':
        defaults = app.config['DOMAIN'][resource]['defaults']
        missing_defaults = defaults.difference(set(document.keys()))
        schema = config.DOMAIN[resource]['schema']
        for missing_field in missing_defaults:
            document[missing_field] = schema[missing_field]['default']

    return document


def payload():
    """ Performs sanity checks or decoding depending on the Content-Type,
    then returns a the request payload as a dict. If request Content-Type is
    unsupported, aborts with a 400 (Bad Request).

    .. versionchanged:: 0.0.7
       Native Flask request.json preferred over json.loads.

    .. versionadded: 0.0.5
    """
    content_type = request.headers['Content-Type'].split(';')[0]

    if content_type == 'application/json':
        return request.json
    elif content_type == \
            'application/x-www-form-urlencoded':
        return request.form if len(request.form) else abort(400)
    else:
        abort(400)


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
