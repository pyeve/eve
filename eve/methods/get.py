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
    querydef, config, debug_error_message, resource_uri
from eve.versioning import resolve_document_version, \
    synthesize_versioned_document, versioned_id_field, get_old_document, \
    diff_document, get_data_version_relation_document
from flask import current_app as app, abort, request


@ratelimit()
@requires_auth('resource')
@pre_event
def get(resource, lookup):
    """ Retrieves the resource documents that match the current request.

    :param resource: the name of the resource.

    .. versionchanged:: 0.4
       Replaced ID_FIELD by item_lookup_field on self link.
       item_lookup_field will default to ID_FIELD if blank.

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
    embedded_fields = _resolve_embedded_fields(resource, req)

    # facilitate cached responses
    if req.if_modified_since:
        # client has made this request before, has it changed?
        # this request does not account for deleted documents!!! (issue #243)
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
        _build_response_document(document, resource, embedded_fields)
        documents.append(document)

        # build last update for entire response
        if document[config.LAST_UPDATED] > last_update:
            last_update = document[config.LAST_UPDATED]

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
    req = parse_request(resource)
    resource_def = config.DOMAIN[resource]
    embedded_fields = _resolve_embedded_fields(resource, req)

    document = app.data.find_one(resource, req, **lookup)
    if document:
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
        _build_response_document(
            document, resource, embedded_fields, latest_doc)

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
            # TODO: support pagination?

            # find all versions
            lookup[versioned_id_field()] = lookup[app.config['ID_FIELD']]
            del lookup[app.config['ID_FIELD']]
            req.sort = '[("%s", 1)]' % config.VERSION
            cursor = app.data.find(resource+config.VERSIONS, req, lookup)

            # build all versions
            documents = []
            if cursor.count() == 0:
                # this is the scenario when the document existed before
                # document versioning got turned on
                documents.append(latest_doc)
            else:
                last_document = {}
                for i, document in enumerate(cursor):
                    document = synthesize_versioned_document(
                        latest_doc, document, resource_def)
                    _build_response_document(
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

            # TODO: callbacks not currently supported with ?version=all

            # add documents to response
            if config.DOMAIN[resource]['hateoas']:
                response[config.ITEMS] = documents
            else:
                response = documents
        else:
            # notify registered callback functions. Please note that, should
            # the functions modify the document, last_modified and etag  won't
            # be updated to reflect the changes (they always reflect the
            # documents state on the database).
            item_title = config.DOMAIN[resource]['item_title'].lower()
            getattr(app, "on_fetch_item")(resource, document[config.ID_FIELD],
                                          document)
            getattr(app, "on_fetch_item_%s" %
                    item_title)(document[config.ID_FIELD], document)

            response = document

        # extra hateoas links
        if config.DOMAIN[resource]['hateoas']:
            if config.LINKS not in response:
                response[config.LINKS] = {}
            response[config.LINKS]['collection'] = {
                'title': config.DOMAIN[resource]['resource_title'],
                'href': resource_uri(resource)}
            response[config.LINKS]['parent'] = home_link()

        return response, last_modified, etag, 200

    abort(404)


def _build_response_document(
        document, resource, embedded_fields, latest_doc=None):
    """ Prepares a document for response including generation of ETag and
    metadata fields.

    :param document: the document to embed other documents into.
    :param resource: the resource name.
    :param embedded_fields: the list of fields we are allowed to embed.
    :param document: the latest version of document.

    .. versionadded:: 0.4
    """
    # need to update the document field since the etag must be computed on the
    # same document representation that might have been used in the collection
    # 'get' method
    document[config.DATE_CREATED] = date_created(document)
    document[config.LAST_UPDATED] = last_updated(document)
    #TODO: last_update should include consideration for embedded documents

    # generate ETag
    if config.IF_MATCH:
        document[config.ETAG] = document_etag(document)

    # hateoas links
    if config.DOMAIN[resource]['hateoas']:
        _lookup_field = config.DOMAIN[resource]['item_lookup_field']
        document[config.LINKS] = {'self':
                                  document_link(resource,
                                                document[_lookup_field])}

    # add version numbers
    resolve_document_version(document, resource, 'GET', latest_doc)

    # media and embedded documents
    _resolve_media_files(document, resource)
    _resolve_embedded_documents(document, resource, embedded_fields)


def _resolve_embedded_fields(resource, req):
    """ Returns a list of validated embedded fields from the incoming request
    or from the resource definition is the request does not specify.

    :param resource: the resource name.
    :param req: and instace of :class:`eve.utils.ParsedRequest`.

    .. versionadded:: 0.4
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

    return enabled_embedded_fields


def _resolve_embedded_documents(document, resource, embedded_fields):
    """ Loops through the documents, adding embedded representations
    of any fields that are (1) defined eligible for embedding in the
    DOMAIN and (2) requested to be embedded in the current `req`.

    Currently we only support a single layer of embedding,
    i.e. /invoices/?embedded={"user":1}
    *NOT*  /invoices/?embedded={"user.friends":1}

    :param document: the document to embed other documents into.
    :param resource: the resource name.
    :param embedded_fields: the list of fields we are allowed to embed.

    .. versionchagend:: 0.4
        Moved parsing of embedded fields to _resolve_embedded_fields.
        Support for document versioning.

    .. versionchagend:: 0.2
        Support for 'embedded_fields'.

    .. versonchanged:: 0.1.1
       'collection' key has been renamed to 'resource' (data_relation).

    .. versionadded:: 0.1.0
    """
    schema = config.DOMAIN[resource]['schema']
    for field in embedded_fields:
        data_relation = schema[field]['data_relation']
        # Retrieve and serialize the requested document
        if 'version' in data_relation and data_relation['version'] is True:
            # grab the specific version
            embedded_doc = get_data_version_relation_document(
                data_relation, document[field])

            # grab the latest version
            latest_embedded_doc = get_data_version_relation_document(
                data_relation, document[field], latest=True)

            # build the response document
            _build_response_document(
                embedded_doc, data_relation['resource'],
                [], latest_embedded_doc)
        else:
            embedded_doc = app.data.find_one(
                data_relation['resource'], None,
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

    .. versionchanged:: 0.4
       Now using resource_uri when building HATEOAS links (_collection_link
       removed).

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
                       'href': resource_uri(resource)}}

    if documents_count and config.DOMAIN[resource]['pagination']:
        if req.page * req.max_results < documents_count:
            q = querydef(req.max_results, req.where, req.sort, req.page + 1)
            _links['next'] = {'title': 'next page', 'href': '%s%s' %
                              (resource_uri(resource), q)}

            # in python 2.x dividing 2 ints produces an int and that's rounded
            # before the ceil call. Have to cast one value to float to get
            # a correct result. Wonder if 2 casts + ceil() call are actually
            # faster than documents_count // req.max_results and then adding
            # 1 if the modulo is non-zero...
            last_page = int(math.ceil(documents_count
                                      / float(req.max_results)))
            q = querydef(req.max_results, req.where, req.sort, last_page)
            _links['last'] = {'title': 'last page', 'href': '%s%s'
                              % (resource_uri(resource), q)}

        if req.page > 1:
            q = querydef(req.max_results, req.where, req.sort, req.page - 1)
            _links['prev'] = {'title': 'previous page', 'href': '%s%s' %
                              (resource_uri(resource), q)}

    return _links


def _resolve_media_files(document, resource):
    for field in resource_media_fields(document, resource):
        _file = app.media.get(document[field])
        document[field] = base64.encodestring(_file.read()) if _file else None
