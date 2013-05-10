# -*- coding: utf-8 -*-

"""
    eve.methods.common
    ~~~~~~~~~~~~~~~~~~

    Utility functions for API methods implementations.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app as app, request
from flask import abort
import simplejson as json
from ..utils import str_to_date, parse_request, document_etag, config


def get_document(resource, **lookup):
    """ Retrieves and return a single document. Since this function is used by
    the editing methods (POST, PATCH, DELETE), we make sure that the client
    request references the current representation of the dcument before
    returning it.

    :param resource: the name of the resource to which the document belongs to.
    :param **lookup: document lookup query

    ..versionchanged:: 0.0.5
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
    if request.method == 'POST' and \
            'X-HTTP-Method-Override' not in request.headers:
        defaults = app.config['DOMAIN'][resource]['defaults']
        missing_defaults = defaults.difference(set(document.keys()))
        schema = config.DOMAIN[resource]['schema']
        for missing_field in missing_defaults:
            document[missing_field] = schema[missing_field]['default']

    return document


def payload():
    """ Performs sanity checks or decoding depending on the Content-Type,
    then keturns a the request payload as a dict. If request Content-Type is
    unsupported, aborts with a 400 (Bad Request).

    .. versionadded: 0.0.5
    """
    content_type = request.headers['Content-Type'].split(';')[0]

    if content_type == 'application/json':
        return json.loads(request.data)
    elif content_type == \
            'application/x-www-form-urlencoded':
        return request.form if len(request.form) else abort(400)
    else:
        abort(400)
