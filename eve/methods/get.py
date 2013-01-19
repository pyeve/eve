# -*- coding: utf-8 -*-

"""
    eve.methods.get
    ~~~~~~~~~~~~~~~

    This module implements the API 'GET' methods, supported by both the
    resources and single item endpoints.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

# TODO currently documents are returned 'as-stored', with no validation
# against the domain model. Since validation happens when they are stored via
# the API (PATCH/POST), validating them again seems overkill. However there
# might be situations/scenarios where the stored document might different
# from the domain model (ie: different API versions, or fields that should
# be ignored by the API). Once versioning is properly implemented (or maybe
# even before than that), a domain filter should probably be in place.

from flask import current_app as app
from flask import abort
from datetime import datetime
from eve.utils import parse_request, document_etag, document_link, \
    collection_link, home_link, querydef, resource_uri, config


def get(resource):
    """Retrieves the resource documents that match the current request.

    :param resource: the name of the resource.

    .. versionchanged:: 0.0.3
       Superflous ``response`` container removed. Collection items wrapped
       with ``_items``. Links wrapped with ``_links``. Links are now properly
       JSON formatted.
    """

    documents = list()
    response = dict()
    last_updated = datetime.min

    req = parse_request()
    cursor = app.data.find(resource, req)
    for document in cursor:
        # flask-pymongo returns timezone-aware value, we strip it out
        # because std lib datetime doesn't provide that, and comparisions
        # between the two values would fail

        # TODO consider testing if the app.data is of type Mongo before
        # replacing the tzinfo. On the other hand this could be handy for
        # other drivers as well (think of it as a safety measure). A
        # 'pythonic' alternative would be to perform the comparision in a
        # try..catch statement.. performing the replace in case of an
        # exception. However that would mean getting the exception at each
        # execution under standard circumstances (the default driver being
        # Mongo).
        document[config.LAST_UPDATED] = \
            document[config.LAST_UPDATED].replace(tzinfo=None)

        if document[config.LAST_UPDATED] > last_updated:
            last_updated = document[config.LAST_UPDATED]

        # document metadata
        document['etag'] = document_etag(document)
        document['_links'] = {'self': document_link(resource,
                                                    document[config.ID_FIELD])}

        documents.append(document)

    if req.if_modified_since and len(documents) == 0:
        # the if-modified-since conditional request returned no documents, we
        # send back a 304 Not-Modified, which means that the client already
        # has the up-to-date representation of the resultset.
        status = 304
        last_modified = None
    else:
        status = 200
        last_modified = last_updated if last_updated > datetime.min else None
        response['_items'] = documents
        response['_links'] = _pagination_links(resource, req, cursor.count())

    etag = None
    return response, last_modified, etag, status


def getitem(resource, **lookup):
    """ Retrieves and returns a single document.

    :param resource: the name of the resource to which the document belongs.
    :param **lookup: the lookup query.

    .. versionchanged:: 0.0.3
       Superflous ``response`` container removed. Links wrapped with
       ``_links``. Links are now properly JSON formatted.
    """
    response = dict()

    req = parse_request()
    document = app.data.find_one(resource, **lookup)
    if document:
        # need to update the document field as well since the etag must
        # be computed on the same document representation that might have
        # been used in the collection 'get' method
        last_modified = document[config.LAST_UPDATED] = \
            document[config.LAST_UPDATED].replace(tzinfo=None)
        etag = document_etag(document)

        if req.if_none_match and etag == req.if_none_match:
            # request etag matches the current server representation of the
            # document, return a 304 Not-Modified.
            return response, last_modified, etag, 304

        if req.if_modified_since and last_modified <= req.if_modified_since:
            # request If-Modified-Since conditional request match. We test
            # this after the etag since Last-Modified dates have lower
            # resolution (1 second).
            return response, last_modified, etag, 304

        response['_links'] = {
            'self': document_link(resource, document[config.ID_FIELD]),
            'collection': collection_link(resource),
            'parent': home_link()
        }
        response.update(document)
        return response, last_modified, etag, 200

    abort(404)


def _pagination_links(resource, req, documents_count):
    """Returns the appropriate set of resource links depending on the
    current page and the total number of documents returned by the query.

    :param resource: the resource name.
    :param req: and instace of :class:`eve.utils.ParsedRequest`.
    :param document_count: the number of documents returned by the query.

    .. versionchanged:: 0.0.3
       JSON links
    """
    _links = {'parent': home_link(), 'self': collection_link(resource)}

    if documents_count:
        if req.page * req.max_results < documents_count:
            q = querydef(req.max_results, req.where, req.sort, req.page + 1)
            _links['next'] = {'title': 'next page', 'href': '%s%s' %
                              (resource_uri(resource), q)}

        if req.page > 1:
            q = querydef(req.max_results, req.where, req.sort, req.page - 1)
            _links['prev'] = {'title': 'previous page', 'href': '%s%s' %
                              (resource_uri(resource), q)}

    return _links


def standard_links(resource):
    """Returns the standard set of resource links that are included in every
    kind of GET response.
    """
    return [home_link(), collection_link(resource)]
