# -*- coding: utf-8 -*-

"""
    eve.methods.common
    ~~~~~~~~~~~~~~~~~~

    Utility functions for API methods implementations.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app as app
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
    """
    req = parse_request()
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
    """

    document = json.loads(value)

    # By design, dates are expressed as RFC-1123 strings. We convert them
    # to proper datetimes.
    dates = app.config['DOMAIN'][resource]['dates']
    document_dates = dates.intersection(set(document.keys()))
    for date_field in document_dates:
        document[date_field] = str_to_date(document[date_field])

    return document
