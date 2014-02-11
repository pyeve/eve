# -*- coding: utf-8 -*-

"""
    eve.methods.get
    ~~~~~~~~~~~~~~~

    This module implements the API 'GET' methods, supported by both the
    resources and single item endpoints.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import copy
import math
import base64

import simplejson as json

from .common import ratelimit, epoch, date_created, last_updated, pre_event, \
    resource_media_fields
from eve.auth import requires_auth
from eve.utils import parse_request, document_etag, document_link, home_link, \
    querydef, config, debug_error_message
from flask import current_app as app, abort, request


@ratelimit()
@requires_auth('resource')
@pre_event
def get(resource, lookup):
    """ Retrieves the resource documents that match the current request.

    :param resource: the name of the resource.

    .. versionchanged:: 0.3
       Don't return 304 if resource is empty. Fixes #243.
       Support for media fields.
       When IF_MATCH is disabled, no etag is included in the payload.
       When If-Modified-Since header is present, either no documents (304) or
       all documents (200) are sent per the HTTP spec. Original behavior can be
       achieved with:
           /resource?where={"updated":{"$gt":"if-modified-since-date"}}

    .. versionchanged:: 0.2
       Use the new ITEMS configuration setting.
       Raise 'on_pre_<method>' event.
       Let cursor add extra info to response.

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.
       Support for embeddable documents.

    .. versionchanged:: 0.0.9
       Event hooks renamed to be more robuts and consistent: 'on_getting'
       renamed to 'on_fetch'.

    .. versionchanged:: 0.0.8
       'on_getting' and 'on_getting_<resource>' events are raised when
       documents have been read from the database and are about to be sent to
       the client.

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
    etag = None
    req = parse_request(resource)

    if req.if_modified_since:
        # client has made this request before, has it changed?
        preflight_req = copy.copy(req)
        preflight_req.max_results = 1

        cursor = app.data.find(resource, preflight_req, lookup)
        if cursor.count() == 0:
            # make sure the datasource is not empty (#243).
            if not app.data.is_empty(resource):
                # the if-modified-since conditional request returned no
                # documents, we send back a 304 Not-Modified, which means that
                # the client already has the up-to-date representation of the
                # resultset.
                status = 304
                last_modified = None
                return response, last_modified, etag, status

    # continue processing the full request
    last_update = epoch()
    req.if_modified_since = None
    cursor = app.data.find(resource, req, lookup)

    for document in cursor:
        document[config.LAST_UPDATED] = last_updated(document)
        document[config.DATE_CREATED] = date_created(document)

        if document[config.LAST_UPDATED] > last_update:
            last_update = document[config.LAST_UPDATED]

        # document metadata
        if config.IF_MATCH:
            document[config.ETAG] = document_etag(document)

        if config.DOMAIN[resource]['hateoas']:
            document[config.LINKS] = {'self':
                                      document_link(resource,
                                                    document[config.ID_FIELD])}

        _resolve_media_files(document, resource)

        documents.append(document)

    _resolve_embedded_documents(resource, req, documents)

    status = 200
    last_modified = last_update if last_update > epoch() else None

    # notify registered callback functions. Please note that, should the
    # functions modify the documents, the last_modified and etag won't be
    # updated to reflect the changes (they always reflect the documents
    # state on the database.)

    getattr(app, "on_fetch_resource")(resource, documents)
    getattr(app, "on_fetch_resource_%s" % resource)(documents)

    if config.DOMAIN[resource]['hateoas']:
        response[config.ITEMS] = documents
        response[config.LINKS] = _pagination_links(resource, req,
                                                   cursor.count())
    else:
        response = documents

    # the 'extra' cursor field, if present, will be added to the response.
    # Can be used by Eve extensions to add extra, custom data to any
    # response.
    if hasattr(cursor, 'extra'):
        getattr(cursor, 'extra')(response)

    return response, last_modified, etag, status


@ratelimit()
@requires_auth('item')
@pre_event
def getitem(resource, **lookup):
    """
    :param resource: the name of the resource to which the document belongs.
    :param **lookup: the lookup query.

    .. versionchanged:: 0.3
       Support for media fields.
       When IF_MATCH is disabled, no etag is included in the payload.

    .. versionchanged:: 0.1.1
       Support for Embeded Resource Serialization.

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.

    .. versionchanged: 0.0.8
       'on_getting_item' event is raised when a document has been read from the
       database and is about to be sent to the client.

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
        last_modified = document[config.LAST_UPDATED] = last_updated(document)
        document[config.DATE_CREATED] = date_created(document)

        etag = None
        if config.IF_MATCH:
            etag = document[config.ETAG] = document_etag(document)

            if req.if_none_match and document[config.ETAG] == \
                    req.if_none_match:
                # request etag matches the current server representation of the
                # document, return a 304 Not-Modified.
                return response, last_modified, etag, 304

        if req.if_modified_since and last_modified <= req.if_modified_since:
            # request If-Modified-Since conditional request match. We test
            # this after the etag since Last-Modified dates have lower
            # resolution (1 second).
            return response, last_modified, document.get(config.ETAG), 304

        _resolve_embedded_documents(resource, req, [document])
        _resolve_media_files(document, resource)

        if config.DOMAIN[resource]['hateoas']:
            response[config.LINKS] = {
                'self': document_link(resource, document[config.ID_FIELD]),
                'collection': {'title':
                               config.DOMAIN[resource]['resource_title'],
                               'href': _collection_link(resource, True)},
                'parent': home_link()
            }

        # notify registered callback functions. Please note that, should the
        # functions modify the document, last_modified and etag  won't be
        # updated to reflect the changes (they always reflect the documents
        # state on the database).
        item_title = config.DOMAIN[resource]['item_title'].lower()

        getattr(app, "on_fetch_item")(resource, document[config.ID_FIELD],
                                      document)
        getattr(app, "on_fetch_item_%s" %
                item_title)(document[config.ID_FIELD], document)

        response.update(document)
        return response, last_modified, etag, 200

    abort(404)


def _resolve_embedded_documents(resource, req, documents):
    """ Loops through the documents, adding embedded representations
    of any fields that are (1) defined eligible for embedding in the
    DOMAIN and (2) requested to be embedded in the current `req`.

    Currently we only support a single layer of embedding,
    i.e. /invoices/?embedded={"user":1}
    *NOT*  /invoices/?embedded={"user.friends":1}

    :param resource: the resource name.
    :param req: and instace of :class:`eve.utils.ParsedRequest`.
    :param documents: list of documents returned by the query.

    .. versionchagend:: 0.2
        Support for 'embedded_fields'.

    .. versonchanged:: 0.1.1
       'collection' key has been renamed to 'resource' (data_relation).

    .. versionadded:: 0.1.0
    """
    embedded_fields = []
    if req.embedded:
        # Parse the embedded clause, we are expecting
        # something like:   '{"user":1}'
        try:
            client_embedding = json.loads(req.embedded)
        except ValueError:
            abort(400, description=debug_error_message(
                'Unable to parse `embedded` clause'
            ))

        # Build the list of fields where embedding is being requested
        try:
            embedded_fields = [k for k, v in client_embedding.items()
                               if v == 1]
        except AttributeError:
            # We got something other than a dict
            abort(400, description=debug_error_message(
                'Unable to parse `embedded` clause'
            ))

    embedded_fields = list(
        set(config.DOMAIN[resource]['embedded_fields']) |
        set(embedded_fields))

    # For each field, is the field allowed to be embedded?
    # Pick out fields that have a `data_relation` where `embeddable=True`
    enabled_embedded_fields = []
    for field in embedded_fields:
        # Reject bogus field names
        if field in config.DOMAIN[resource]['schema']:
            field_definition = config.DOMAIN[resource]['schema'][field]
            if 'data_relation' in field_definition and \
                    field_definition['data_relation'].get('embeddable'):
                # or could raise 400 here
                enabled_embedded_fields.append(field)

        for document in documents:
            for field in enabled_embedded_fields:
                field_definition = config.DOMAIN[resource]['schema'][field]
                # Retrieve and serialize the requested document
                embedded_doc = app.data.find_one(
                    field_definition['data_relation']['resource'],
                    **{config.ID_FIELD: document[field]}
                )
                if embedded_doc:
                    document[field] = embedded_doc


def _pagination_links(resource, req, documents_count):
    """ Returns the appropriate set of resource links depending on the
    current page and the total number of documents returned by the query.

    :param resource: the resource name.
    :param req: and instace of :class:`eve.utils.ParsedRequest`.
    :param document_count: the number of documents returned by the query.

    .. versionchanged:: 0.0.8
       Link to last page is provided if pagination is enabled (and the current
       page is not the last one).

    .. versionchanged:: 0.0.7
       Support for Rate-Limiting.

    .. versionchanged:: 0.0.5
       Support for optional pagination.

    .. versionchanged:: 0.0.3
       JSON links
    """
    _links = {'parent': home_link(),
              'self': {'title': config.DOMAIN[resource]['resource_title'],
                       'href': _collection_link(resource)}}

    if documents_count and config.DOMAIN[resource]['pagination']:
        if req.page * req.max_results < documents_count:
            q = querydef(req.max_results, req.where, req.sort, req.page + 1)
            _links['next'] = {'title': 'next page', 'href': '%s%s' %
                              (_collection_link(resource), q)}

            # in python 2.x dividing 2 ints produces an int and that's rounded
            # before the ceil call. Have to cast one value to float to get
            # a correct result. Wonder if 2 casts + ceil() call are actually
            # faster than documents_count // req.max_results and then adding
            # 1 if the modulo is non-zero...
            last_page = int(math.ceil(documents_count
                                      / float(req.max_results)))
            q = querydef(req.max_results, req.where, req.sort, last_page)
            _links['last'] = {'title': 'last page', 'href': '%s%s'
                              % (_collection_link(resource), q)}

        if req.page > 1:
            q = querydef(req.max_results, req.where, req.sort, req.page - 1)
            _links['prev'] = {'title': 'previous page', 'href': '%s%s' %
                              (_collection_link(resource), q)}

    return _links


def _collection_link(resource, item=False):
    path = request.path.rstrip('/')
    if item:
        path = path[:path.rfind('/')]
    server_name = config.SERVER_NAME if config.SERVER_NAME else ''
    return '%s%s' % (server_name, path)


def _resolve_media_files(document, resource):
    for field in resource_media_fields(document, resource):
        _file = app.media.get(document[field])
        document[field] = base64.encodestring(_file.read()) if _file else None
