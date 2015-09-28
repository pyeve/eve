# -*- coding: utf-8 -*-

"""
    eve.methods.get
    ~~~~~~~~~~~~~~~

    This module implements the API 'GET' methods, supported by both the
    resources and single item endpoints.

    :copyright: (c) 2015 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import math
from flask import current_app as app, abort, request
from .common import ratelimit, epoch, pre_event, resolve_embedded_fields, \
    build_response_document, resource_link, document_link, last_updated
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

    .. versionchanged:: 0.6
       Support for HEADER_TOTAL_COUNT returned with response header.

    .. versionchanged:: 0.5
       Support for customisable query parameters.

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

    # continue processing the full request
    last_update = epoch()

    # If-Modified-Since disabled on collections (#334)
    req.if_modified_since = None

    cursor = app.data.find(resource, req, lookup)
    # If soft delete is enabled, data.find will not include items marked
    # deleted unless req.show_deleted is True
    for document in cursor:
        build_response_document(document, resource, embedded_fields)
        documents.append(document)

        # build last update for entire response
        if document[config.LAST_UPDATED] > last_update:
            last_update = document[config.LAST_UPDATED]

    status = 200
    headers = []
    last_modified = last_update if last_update > epoch() else None

    response[config.ITEMS] = documents
    count = cursor.count(with_limit_and_skip=False)
    headers.append((config.HEADER_TOTAL_COUNT, count))

    if config.DOMAIN[resource]['hateoas']:
        response[config.LINKS] = _pagination_links(resource, req, count)

    # add pagination info
    if config.DOMAIN[resource]['pagination']:
        response[config.META] = _meta_links(req, count)

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

    return response, last_modified, etag, status, headers


@ratelimit()
@requires_auth('item')
@pre_event
def getitem(resource, **lookup):
    """
    :param resource: the name of the resource to which the document belongs.
    :param **lookup: the lookup query.

    .. versionchanged:: 0.6
       Handle soft deleted documents

    .. versionchanged:: 0.5
       Allow ``?version=all`` requests to fire ``on_fetched_*`` events.
       Create pagination links for document versions. (#475)
       Pagination links reflect current query. (#464)

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

    soft_delete_enabled = config.DOMAIN[resource]['soft_delete']
    if soft_delete_enabled:
        # GET requests should always fetch soft deleted documents from the db
        # They are handled and included in 404 responses below.
        req.show_deleted = True

    document = app.data.find_one(resource, req, **lookup)
    if not document:
        abort(404)

    response = {}
    etag = None
    version = request.args.get(config.VERSION_PARAM)
    latest_doc = None
    cursor = None

    # calculate last_modified before get_old_document rolls back the document,
    # allowing us to invalidate the cache when _latest_version changes
    last_modified = last_updated(document)

    # synthesize old document version(s)
    if resource_def['versioning'] is True:
        latest_doc = document
        document = get_old_document(
            resource, req, lookup, document, version)

    # meld into response document
    build_response_document(document, resource, embedded_fields, latest_doc)
    if config.IF_MATCH:
        etag = document[config.ETAG]

    # check embedded fields resolved in build_response_document() for more
    # recent last updated timestamps. We don't want to respond 304 if embedded
    # fields have changed
    for field in embedded_fields:
        embedded_document = document.get(field)
        if isinstance(embedded_document, dict):
            embedded_last_updated = last_updated(embedded_document)
            if embedded_last_updated > last_modified:
                last_modified = embedded_last_updated

    # facilitate client caching by returning a 304 when appropriate
    cache_validators = {True: 0, False: 0}
    if req.if_modified_since:
        cache_valid = (last_modified <= req.if_modified_since)
        cache_validators[cache_valid] += 1
    if req.if_none_match:
        if (resource_def['versioning'] is False) or \
           (document[app.config['VERSION']] ==
                document[app.config['LATEST_VERSION']]):
            cache_valid = (etag == req.if_none_match)
            cache_validators[cache_valid] += 1
    # If all cache validators are true, return 304
    if (cache_validators[True] > 0) and (cache_validators[False] == 0):
        return {}, last_modified, etag, 304

    if version == 'all' or version == 'diffs':
        # find all versions
        lookup[versioned_id_field(resource_def)] \
            = lookup[resource_def['id_field']]
        del lookup[resource_def['id_field']]
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
    elif soft_delete_enabled and document.get(config.DELETED) is True:
        # This document was soft deleted. Respond with 404 and the deleted
        # version of the document.
        document[config.STATUS] = config.STATUS_ERR,
        document[config.ERROR] = {
            'code': 404,
            'message': 'The requested URL was not found on this server.'
        }
        return document, last_modified, etag, 404
    else:
        response = document

    # extra hateoas links
    if config.DOMAIN[resource]['hateoas']:
        # use the id of the latest document for multi-document requests
        if cursor:
            count = cursor.count(with_limit_and_skip=False)
            response[config.LINKS] = \
                _pagination_links(resource, req, count,
                                  latest_doc[resource_def['id_field']])
            if config.DOMAIN[resource]['pagination']:
                response[config.META] = _meta_links(req, count)
        else:
            response[config.LINKS] = \
                _pagination_links(resource, req, None,
                                  response[resource_def['id_field']])

    # callbacks not supported on version diffs because of partial documents
    if version != 'diffs':
        # TODO: callbacks not currently supported with ?version=all

        # notify registered callback functions. Please note that, should
        # the functions modify the document, last_modified and etag
        # won't be updated to reflect the changes (they always reflect the
        # documents state on the database).
        if resource_def['versioning'] is True and version == 'all':
            versions = response
            if config.DOMAIN[resource]['hateoas']:
                versions = response[config.ITEMS]
            for version_item in versions:
                getattr(app, "on_fetched_item")(resource, version_item)
                getattr(app, "on_fetched_item_%s" % resource)(version_item)
        else:
            getattr(app, "on_fetched_item")(resource, response)
            getattr(app, "on_fetched_item_%s" % resource)(response)

    return response, last_modified, etag, 200


def _pagination_links(resource, req, documents_count, document_id=None):
    """ Returns the appropriate set of resource links depending on the
    current page and the total number of documents returned by the query.

    :param resource: the resource name.
    :param req: and instace of :class:`eve.utils.ParsedRequest`.
    :param document_count: the number of documents returned by the query.
    :param document_id: the document id (used for versions). Defaults to None.

    .. versionchanged:: 0.5
       Create pagination links given a document ID to allow paginated versions
       pages (#475).
       Pagination links reflect current query. (#464)

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
    version = None
    if config.DOMAIN[resource]['versioning'] is True:
        version = request.args.get(config.VERSION_PARAM)

    # construct the default links
    q = querydef(req.max_results, req.where, req.sort, version, req.page)
    resource_title = config.DOMAIN[resource]['resource_title']
    _links = {'parent': home_link(),
              'self': {'title': resource_title,
                       'href': resource_link()}}

    # change links if document ID is given
    if document_id:
        _links['self'] = document_link(resource, document_id)
        _links['collection'] = {'title': resource_title,
                                'href': '%s%s' % (resource_link(), q)}

        # make more specific links for versioned requests
        if version in ('all', 'diffs'):
            _links['parent'] = {'title': resource_title,
                                'href': resource_link()}
            _links['collection'] = document_link(resource, document_id)
        elif version:
            _links['parent'] = document_link(resource, document_id)
            _links['collection'] = {'title': resource_title,
                                    'href': '%s?version=all'
                                    % _links['parent']['href']}

    # modify the self link to add query params or version number
    if documents_count:
        _links['self']['href'] = '%s%s' % (_links['self']['href'], q)
    elif not documents_count and version and version not in ('all', 'diffs'):
        _links['self'] = document_link(resource, document_id, version)

    # create pagination links
    if documents_count and config.DOMAIN[resource]['pagination']:
        # strip any queries from the self link if present
        _pagination_link = _links['self']['href'].split('?')[0]
        if req.page * req.max_results < documents_count:
            q = querydef(req.max_results, req.where, req.sort, version,
                         req.page + 1)
            _links['next'] = {'title': 'next page', 'href': '%s%s' %
                              (_pagination_link, q)}

            # in python 2.x dividing 2 ints produces an int and that's rounded
            # before the ceil call. Have to cast one value to float to get
            # a correct result. Wonder if 2 casts + ceil() call are actually
            # faster than documents_count // req.max_results and then adding
            # 1 if the modulo is non-zero...
            last_page = int(math.ceil(documents_count /
                                      float(req.max_results)))
            q = querydef(req.max_results, req.where, req.sort, version,
                         last_page)
            _links['last'] = {'title': 'last page', 'href': '%s%s'
                              % (_pagination_link, q)}

        if req.page > 1:
            q = querydef(req.max_results, req.where, req.sort, version,
                         req.page - 1)
            _links['prev'] = {'title': 'previous page', 'href': '%s%s' %
                              (_pagination_link, q)}

    return _links


def _meta_links(req, count):
    """ Reterns the meta links for a paginated query.

    :param req: parsed request object.
    :param count: total number of documents in a query.

    .. versionadded:: 0.5
    """
    return {
        config.QUERY_PAGE: req.page,
        config.QUERY_MAX_RESULTS: req.max_results,
        'total': count
    }
