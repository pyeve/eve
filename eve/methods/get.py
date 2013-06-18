# -*- coding: utf-8 -*-

"""
    eve.methods.get
    ~~~~~~~~~~~~~~~

    This module implements the API 'GET' methods, supported by both the
    resources and single item endpoints.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime
from flask import current_app as app, abort
from common import ratelimit
from eve.auth import requires_auth
from eve.utils import parse_request, document_etag, document_link, \
    collection_link, home_link, querydef, resource_uri, config


@ratelimit()
@requires_auth('resource')
def get(resource):
    """Retrieves the resource documents that match the current request.

    :param resource: the name of the resource.

    .. versionchanged:: 0.0.6
       Support for HEAD requests.

    .. versionchanged:: 0.0.5
       Support for user-restricted access to resources.
       Support for LAST_UPDATED field missing from documents, because they were
       created outside the API context.

    .. versionchanged:: 0.0.4
       Added the ``requires_auth`` decorator.

    .. versionchanged:: 0.0.3
       Superflous ``response`` container removed. Collection items wrapped
       with ``_items``. Links wrapped with ``_links``. Links are now properly
       JSON formatted.
    """

    documents = []
    response = {}
    last_updated = _epoch()

    req = parse_request(resource)
    cursor = app.data.find(resource, req)
    for document in cursor:
        document[config.LAST_UPDATED] = _last_updated(document)
        document[config.DATE_CREATED] = _date_created(document)

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
        last_modified = last_updated if last_updated > _epoch() else None
        response['_items'] = documents
        response['_links'] = _pagination_links(resource, req, cursor.count())

    etag = None
    return response, last_modified, etag, status


@ratelimit()
@requires_auth('item')
def getitem(resource, **lookup):
    """ Retrieves and returns a single document.

    :param resource: the name of the resource to which the document belongs.
    :param **lookup: the lookup query.

    .. versionchanged:: 0.0.7
       Support for Rate-Limiting.

    .. versionchanged:: 0.0.6
       Support for HEAD requests.

    .. versionchanged:: 0.0.6
        ETag added to payload.

    .. versionchanged:: 0.0.5
       Support for user-restricted access to resources.
       Support for LAST_UPDATED field missing from documents, because they were
       created outside the API context.

    .. versionchanged:: 0.0.4
       Added the ``requires_auth`` decorator.

    .. versionchanged:: 0.0.3
       Superflous ``response`` container removed. Links wrapped with
       ``_links``. Links are now properly JSON formatted.
    """
    response = {}

    req = parse_request(resource)
    document = app.data.find_one(resource, **lookup)
    if document:
        # need to update the document field as well since the etag must
        # be computed on the same document representation that might have
        # been used in the collection 'get' method
        last_modified = document[config.LAST_UPDATED] = _last_updated(document)
        document['etag'] = document_etag(document)

        if req.if_none_match and document['etag'] == req.if_none_match:
            # request etag matches the current server representation of the
            # document, return a 304 Not-Modified.
            return response, last_modified, document['etag'], 304

        if req.if_modified_since and last_modified <= req.if_modified_since:
            # request If-Modified-Since conditional request match. We test
            # this after the etag since Last-Modified dates have lower
            # resolution (1 second).
            return response, last_modified, document['etag'], 304

        response['_links'] = {
            'self': document_link(resource, document[config.ID_FIELD]),
            'collection': collection_link(resource),
            'parent': home_link()
        }
        response.update(document)
        return response, last_modified, document['etag'], 200

    abort(404)


def _pagination_links(resource, req, documents_count):
    """Returns the appropriate set of resource links depending on the
    current page and the total number of documents returned by the query.

    :param resource: the resource name.
    :param req: and instace of :class:`eve.utils.ParsedRequest`.
    :param document_count: the number of documents returned by the query.

    .. versionchanged:: 0.0.7
       Support for Rate-Limiting.

    .. versionchanged:: 0.0.5
       Support for optional pagination.

    .. versionchanged:: 0.0.3
       JSON links
    """
    _links = {'parent': home_link(), 'self': collection_link(resource)}

    if documents_count and config.DOMAIN[resource]['pagination']:
        if req.page * req.max_results < documents_count:
            q = querydef(req.max_results, req.where, req.sort, req.page + 1)
            _links['next'] = {'title': 'next page', 'href': '%s%s' %
                              (resource_uri(resource), q)}

        if req.page > 1:
            q = querydef(req.max_results, req.where, req.sort, req.page - 1)
            _links['prev'] = {'title': 'previous page', 'href': '%s%s' %
                              (resource_uri(resource), q)}

    return _links


def _last_updated(document):
    """Fixes document's LAST_UPDATED field value. Flask-PyMongo returns
    timezone-aware values while stdlib datetime values are timezone-naive.
    Comparisions between the two would fail.

    If LAST_UPDATE is missing we assume that it has been created outside of the
    API context and inject a default value, to allow for proper computing of
    Last-Modified header tag. By design all documents return a LAST_UPDATED
    (and we don't want to break existing clients).

    :param document: the document to be processed.

    .. versionadded:: 0.0.5
    """
    if config.LAST_UPDATED in document:
        return document[config.LAST_UPDATED].replace(tzinfo=None)
    else:
        return _epoch()


def _date_created(document):
    """If DATE_CREATED is missing we assume that it has been created outside of
    the API context and inject a default value. By design all documents
    return a DATE_CREATED (and we dont' want to break existing clients).

    :param document: the document to be processed.

    .. versionadded:: 0.0.5
    """
    return document[config.DATE_CREATED] if config.DATE_CREATED in document \
        else _epoch()


def _epoch():
    """ A datetime.min alternative which won't crash on us.

    .. versionadded:: 0.0.5
    """
    return datetime(1970, 1, 1)
