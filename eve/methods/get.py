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
from flask import current_app as app, abort, request
from .common import ratelimit, epoch, pre_event, resolve_embedded_fields, \
    build_response_document, resource_link
from eve.auth import requires_auth
from eve.utils import parse_request, home_link, querydef, config
from eve.versioning import synthesize_versioned_document, versioned_id_field, \
    get_old_document, diff_document


@ratelimit()
@requires_auth('resource')
@pre_event
def get(resource, **lookup):
    """ Retrieves the resource documents that match the current request.

    :param resource: the name of the resource.

    .. versionchanged:: 0.4
       Add pagination info whatever the HATEOAS status.
       'on_fetched' events now return the whole response (HATEOAS metafields
       included.)
       Replaced ID_FIELD by item_lookup_field on self link.
       item_lookup_field will default to ID_FIELD if blank.
       Changed ``on_fetch_*`` changed to ``on_fetched_*``.

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
    embedded_fields = resolve_embedded_fields(resource, req)

    # facilitate cached responses
    if req.if_modified_since:
        # client has made this request before, has it changed?
        # this request does not account for deleted documents!!! (issue #243)
        preflight_req = copy.copy(req)
        preflight_req.max_results = 1
        preflight_req.page = 1

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
        build_response_document(document, resource, embedded_fields)
        documents.append(document)

        # build last update for entire response
        if document[config.LAST_UPDATED] > last_update:
            last_update = document[config.LAST_UPDATED]

    status = 200
    last_modified = last_update if last_update > epoch() else None

    response[config.ITEMS] = documents
    if config.DOMAIN[resource]['hateoas']:
        response[config.LINKS] = _pagination_links(resource, req,
                                                   cursor.count())

    # add pagination info
    if cursor.count() and config.DOMAIN[resource]['pagination']:
        response[config.META] = {
            'page': req.page,
            'max_results': req.max_results,
            'total': cursor.count(),
        }

    # notify registered callback functions. Please note that, should the
    # functions modify the documents, the last_modified and etag won't be
    # updated to reflect the changes (they always reflect the documents
    # state on the database.)
    getattr(app, "on_fetched_resource")(resource, response)
    getattr(app, "on_fetched_resource_%s" % resource)(response)

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

    .. versionchanged:: 0.4
       HATOEAS link for contains the business unit value even when
       regexes have been configured for the resource endpoint.
       'on_fetched' now returns the whole response (HATEOAS metafields
       included.)
       Support for document versioning.
       Changed ``on_fetch_*`` changed to ``on_fetched_*``.

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
    req = parse_request(resource)
    resource_def = config.DOMAIN[resource]
    embedded_fields = resolve_embedded_fields(resource, req)

    document = app.data.find_one(resource, req, **lookup)
    if not document:
        abort(404)

    response = {}
    etag = None
    version = request.args.get(config.VERSION_PARAM)
    latest_doc = None

    # synthesize old document version(s)
    if resource_def['versioning'] is True:
        latest_doc = copy.deepcopy(document)
        document = get_old_document(
            resource, req, lookup, document, version)

    # meld into response document
    build_response_document(document, resource, embedded_fields, latest_doc)

    # last_modified for the response
    last_modified = document[config.LAST_UPDATED]

    # facilitate client caching by returning a 304 when appropriate
    if config.IF_MATCH:
        etag = document[config.ETAG]

        if req.if_none_match and etag == req.if_none_match:
            # request etag matches the current server representation of the
            # document, return a 304 Not-Modified.
            return {}, last_modified, document[config.ETAG], 304

    if req.if_modified_since and last_modified <= req.if_modified_since:
        # request If-Modified-Since conditional request match. We test
        # this after the etag since Last-Modified dates have lower
        # resolution (1 second).
        return {}, last_modified, document.get(config.ETAG), 304

    if version == 'all' or version == 'diffs':
        # find all versions
        lookup[versioned_id_field()] = lookup[app.config['ID_FIELD']]
        del lookup[app.config['ID_FIELD']]
        if version == 'diffs' or req.sort is None:
            # default sort for 'all', required sort for 'diffs'
            req.sort = '[("%s", 1)]' % config.VERSION
        req.if_modified_since = None  # we always want the full history here
        cursor = app.data.find(resource + config.VERSIONS, req, lookup)

        # build all versions
        documents = []
        if cursor.count() == 0:
            # this is the scenario when the document existed before
            # document versioning got turned on
            documents.append(latest_doc)
        else:
            last_document = {}

            # if we aren't starting on page 1, then we need to init last_doc
            if version == 'diffs' and req.page > 1:
                # grab the last document on the previous page to diff from
                last_version = cursor[0][app.config['VERSION']] - 1
                last_document = get_old_document(
                    resource, req, lookup, latest_doc, last_version)

            for i, document in enumerate(cursor):
                document = synthesize_versioned_document(
                    latest_doc, document, resource_def)
                build_response_document(
                    document, resource, embedded_fields, latest_doc)
                if version == 'diffs':
                    if i == 0:
                        documents.append(document)
                    else:
                        documents.append(diff_document(
                            resource_def, last_document, document))
                    last_document = document
                else:
                    documents.append(document)

        # add documents to response
        if config.DOMAIN[resource]['hateoas']:
            response[config.ITEMS] = documents
        else:
            response = documents
    else:
        response = document

    # extra hateoas links
    if config.DOMAIN[resource]['hateoas']:
        if config.LINKS not in response:
            response[config.LINKS] = {}
        response[config.LINKS]['collection'] = {
            'title': config.DOMAIN[resource]['resource_title'],
            'href': resource_link()}
        response[config.LINKS]['parent'] = home_link()

    if version != 'all' and version != 'diffs':
        # TODO: callbacks not currently supported with ?version=all

        # notify registered callback functions. Please note that, should
        # the # functions modify the document, last_modified and etag
        # won't be updated to reflect the changes (they always reflect the
        # documents state on the database).
        getattr(app, "on_fetched_item")(resource, response)
        getattr(app, "on_fetched_item_%s" % resource)(response)

    return response, last_modified, etag, 200


def _pagination_links(resource, req, documents_count):
    """ Returns the appropriate set of resource links depending on the
    current page and the total number of documents returned by the query.

    :param resource: the resource name.
    :param req: and instace of :class:`eve.utils.ParsedRequest`.
    :param document_count: the number of documents returned by the query.

    .. versionchanged:: 0.4
       HATOEAS link for contains the business unit value even when
       regexes have been configured for the resource endpoint.

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
                       'href': resource_link()}}

    if documents_count and config.DOMAIN[resource]['pagination']:
        if req.page * req.max_results < documents_count:
            q = querydef(req.max_results, req.where, req.sort, req.page + 1)
            _links['next'] = {'title': 'next page', 'href': '%s%s' %
                              (resource_link(), q)}

            # in python 2.x dividing 2 ints produces an int and that's rounded
            # before the ceil call. Have to cast one value to float to get
            # a correct result. Wonder if 2 casts + ceil() call are actually
            # faster than documents_count // req.max_results and then adding
            # 1 if the modulo is non-zero...
            last_page = int(math.ceil(documents_count
                                      / float(req.max_results)))
            q = querydef(req.max_results, req.where, req.sort, last_page)
            _links['last'] = {'title': 'last page', 'href': '%s%s'
                              % (resource_link(), q)}

        if req.page > 1:
            q = querydef(req.max_results, req.where, req.sort, req.page - 1)
            _links['prev'] = {'title': 'previous page', 'href': '%s%s' %
                              (resource_link(), q)}

    return _links
