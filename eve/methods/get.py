# -*- coding: utf-8 -*-

"""
    eve.methods.get
    ~~~~~~~~~~~~~~~

    This module implements the API 'GET' methods, supported by both the
    resources and single item endpoints.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import math

import copy
import simplejson as json
from flask import current_app as app, abort, request
from werkzeug.datastructures import MultiDict

from .common import (
    ratelimit,
    epoch,
    pre_event,
    resolve_embedded_fields,
    build_response_document,
    resource_link,
    document_link,
    last_updated,
)
from eve.auth import requires_auth
from eve.utils import parse_request, home_link, querydef, config
from eve.versioning import (
    synthesize_versioned_document,
    versioned_id_field,
    get_old_document,
    diff_document,
)


@ratelimit()
@requires_auth("resource")
@pre_event
def get(resource, **lookup):
    """
    Default function for handling GET requests, it has decorators for
    rate limiting, authentication and for raising pre-request events. After the
    decorators are applied forwards to call to :func:`get_internal`

    .. versionadded:: 0.6.2
    """
    return get_internal(resource, **lookup)


def get_internal(resource, **lookup):
    """Retrieves the resource documents that match the current request.

    :param resource: the name of the resource.

    .. versionchanged:: 0.6
       Support for HEADER_TOTAL_COUNT returned with response header.

    .. versionchanged:: 0.5
       Support for customizable query parameters.

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
       Event hooks renamed to be more robust and consistent: 'on_getting'
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

    datasource = config.DOMAIN[resource]["datasource"]
    aggregation = datasource.get("aggregation")

    if aggregation:
        return _perform_aggregation(
            resource, aggregation["pipeline"], aggregation["options"]
        )
    else:
        return _perform_find(resource, lookup)


def _perform_aggregation(resource, pipeline, options):
    """
    .. versionadded:: 0.7
    """

    # TODO move most of this down to the Mongo layer?

    # TODO experiment with cursor.batch_size as alternative pagination
    # implementation

    def parse_aggregation_stage(st_item, key, value):
        def parse_again(st_value, key, value):
            """
            If stage value is list or dict then parse recursively
            """
            if isinstance(st_value, (list, dict)):
                parse_aggregation_stage(st_value, key, value)

        if isinstance(st_item, dict):
            for st_key, st_value in st_item.items():
                if key == st_value:
                    st_item[st_key] = value
                else:
                    parse_again(st_value, key, value)

        elif isinstance(st_item, list):
            for st_i, st_value in enumerate(st_item):
                if key == st_value:
                    st_item[st_i] = value
                else:
                    parse_again(st_value, key, value)

    def prune_aggregation_stage(d):
        """
        Remove the stages whose parameters are not set.

        For example, we have endpoint with a stage like {'$lookup': {'$userId': '$a', '$name': '$b'}}, $a is provided
        but $b is provided as {}. Then the stage will be pruned as {'$lookup': {'$userId': '$a'}}
        """
        for st_key, st_value in list(d.items()):
            if isinstance(st_value, dict):
                prune_aggregation_stage(st_value)
                if not st_value:
                    # value is an empty dict, remove the key
                    del d[st_key]

    response = {}
    documents = []
    req = parse_request(resource)

    req_pipeline = copy.deepcopy(pipeline)
    if req.aggregation:
        try:
            query = json.loads(req.aggregation)
        except ValueError:
            abort(400, description="Aggregation query could not be parsed.")

        for key, value in query.items():
            if key.startswith("$"):
                pass
            for stage in req_pipeline:
                parse_aggregation_stage(stage, key, value)

    # remove the stages whose conditions are not yet set
    req_pipeline_pruned = []
    for stage in req_pipeline:
        prune_aggregation_stage(stage)
        if stage:
            req_pipeline_pruned.append(stage)

    paginated_results = []

    if req.max_results > 0:
        limit = {"$limit": req.max_results}
        skip = {"$skip": (req.page - 1) * req.max_results}
        paginated_results.append(skip)
        paginated_results.append(limit)
    else:
        # sub-pipeline in $facet stage cannot be empty
        skip = {"$skip": 0}
        paginated_results.append(skip)

    facet_pipelines = {}
    facet_pipelines["paginated_results"] = paginated_results
    facet_pipelines["total_count"] = [{"$count": "count"}]

    facet = {"$facet": facet_pipelines}

    getattr(app, "before_aggregation")(resource, req_pipeline_pruned)

    # Appending $facet afer the before_aggregation hook allows for
    # easy modification of the orginal pipline, however, pagination
    # (skip, limit) cannot be accessed.
    req_pipeline_pruned.append(facet)

    cursor = app.data.aggregate(resource, req_pipeline_pruned, options).next()

    for document in cursor["paginated_results"]:
        documents.append(document)

    getattr(app, "after_aggregation")(resource, documents)

    response[config.ITEMS] = documents

    if cursor["total_count"]:
        # IndexError: list index out of range
        count = cursor["total_count"][0]["count"]
    else:
        count = 0

    # add pagination info
    if config.DOMAIN[resource]["pagination"]:
        response[config.META] = _meta_links(req, count)

    if config.DOMAIN[resource]["hateoas"]:
        response[config.LINKS] = _pagination_links(resource, req, count)

    return response, None, None, 200, []


def _perform_find(resource, lookup):
    """
    .. versionadded:: 0.7
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

    cursor, count = app.data.find(
        resource, req, lookup, perform_count=not config.OPTIMIZE_PAGINATION_FOR_SPEED
    )
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

    if count is not None:
        headers.append((config.HEADER_TOTAL_COUNT, count))

    if config.DOMAIN[resource]["hateoas"]:
        response[config.LINKS] = _pagination_links(resource, req, count)

    # add pagination info
    if config.DOMAIN[resource]["pagination"]:
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
    if hasattr(cursor, "extra"):
        getattr(cursor, "extra")(response)

    return response, last_modified, etag, status, headers


@ratelimit()
@requires_auth("item")
@pre_event
def getitem(resource, **lookup):
    """
    Default function for handling GET requests to document endpoints, it has
    decorators for rate limiting, authentication and for raising pre-request
    events. After the decorators are applied forwards to call to
    :func:`getitem_internal`

    .. versionadded:: 0.6.2
    """
    return getitem_internal(resource, **lookup)


def getitem_internal(resource, **lookup):
    """
    :param resource: the name of the resource to which the document belongs.
    :param **lookup: the lookup query.

    .. versionchanged:: 0.8.2
       Prevent extra hateoas links from overwriting
       already existed data relation hateoas links.

    .. versionchanged:: 0.6
       Handle soft deleted documents

    .. versionchanged:: 0.5
       Allow ``?version=all`` requests to fire ``on_fetched_*`` events.
       Create pagination links for document versions. (#475)
       Pagination links reflect current query. (#464)

    .. versionchanged:: 0.4
       HATEOAS link for contains the business unit value even when
       regexes have been configured for the resource endpoint.
       'on_fetched' now returns the whole response (HATEOAS metafields
       included.)
       Support for document versioning.
       Changed ``on_fetch_*`` changed to ``on_fetched_*``.

    .. versionchanged:: 0.3
       Support for media fields.
       When IF_MATCH is disabled, no etag is included in the payload.

    .. versionchanged:: 0.1.1
       Support for Embedded Resource Serialization.

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

    soft_delete_enabled = config.DOMAIN[resource]["soft_delete"]
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
    if resource_def["versioning"] is True:
        latest_doc = document
        document = get_old_document(resource, req, lookup, document, version)

    # meld into response document
    build_response_document(document, resource, embedded_fields, latest_doc)
    if config.IF_MATCH:
        etag = document[config.ETAG]
        if resource_def["versioning"] is True:
            # In order to keep the LATEST_VERSION field up to date in client
            # caches, changes to the latest version should invalidate cached
            # copies of previous verisons. Incorporate the latest version into
            # versioned document ETags on the fly to ensure 'If-None-Match'
            # comparisons support this caching behavior.
            etag += str(document[config.LATEST_VERSION])

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
        cache_valid = last_modified <= req.if_modified_since
        cache_validators[cache_valid] += 1
    if req.if_none_match:
        cache_valid = etag == req.if_none_match
        cache_validators[cache_valid] += 1
    # If all cache validators are true, return 304
    if (cache_validators[True] > 0) and (cache_validators[False] == 0):
        return {}, last_modified, etag, 304

    if version in ("all", "diffs"):
        # find all versions
        lookup[versioned_id_field(resource_def)] = lookup[resource_def["id_field"]]
        del lookup[resource_def["id_field"]]
        if version == "diffs" or req.sort is None:
            # default sort for 'all', required sort for 'diffs'
            req.sort = '[("%s", 1)]' % config.VERSION
        req.if_modified_since = None  # we always want the full history here
        cursor, count = app.data.find(resource + config.VERSIONS, req, lookup)

        # build all versions
        documents = []
        if count == 0:
            # this is the scenario when the document existed before
            # document versioning got turned on
            documents.append(latest_doc)
        else:
            last_document = {}

            # if we aren't starting on page 1, then we need to init last_doc
            if version == "diffs" and req.page > 1:
                # grab the last document on the previous page to diff from
                last_version = cursor[0][app.config["VERSION"]] - 1
                last_document = get_old_document(
                    resource, req, lookup, latest_doc, last_version
                )

            for i, document in enumerate(cursor):
                document = synthesize_versioned_document(
                    latest_doc, document, resource_def
                )
                build_response_document(document, resource, embedded_fields, latest_doc)
                if version == "diffs":
                    if i == 0:
                        documents.append(document)
                    else:
                        documents.append(
                            diff_document(resource_def, last_document, document)
                        )
                    last_document = document
                else:
                    documents.append(document)

        # add documents to response
        if config.DOMAIN[resource]["hateoas"]:
            response[config.ITEMS] = documents
        else:
            response = documents
    elif soft_delete_enabled and document.get(config.DELETED) is True:
        # This document was soft deleted. Respond with 404 and the deleted
        # version of the document.
        document[config.STATUS] = (config.STATUS_ERR,)
        document[config.ERROR] = {
            "code": 404,
            "message": "The requested URL was not found on this server.",
        }
        return document, last_modified, etag, 404
    else:
        response = document

    # extra hateoas links
    if config.DOMAIN[resource]["hateoas"]:
        # use the id of the latest document for multi-document requests
        if cursor:
            response[config.LINKS] = _pagination_links(
                resource, req, count, latest_doc[resource_def["id_field"]]
            )
            if config.DOMAIN[resource]["pagination"]:
                response[config.META] = _meta_links(req, count)
        else:
            response[config.LINKS].update(
                _pagination_links(
                    resource, req, None, response[resource_def["id_field"]]
                )
            )

    # callbacks supported on all version methods - even for diffs with partial documents
    # partial documents should be handled properly in the callback
    #
    # notify registered callback functions. Please note that, should
    # the functions modify the document, last_modified and etag
    # won't be updated to reflect the changes (they always reflect the
    # documents state on the database).
    if resource_def["versioning"] is True and version in ("all", "diffs"):
        versions = response
        if config.DOMAIN[resource]["hateoas"]:
            versions = response[config.ITEMS]

        if version == "diffs":
            getattr(app, "on_fetched_diffs")(resource, versions)
            getattr(app, "on_fetched_diffs_%s" % resource)(versions)
        else:
            for version_item in versions:
                getattr(app, "on_fetched_item")(resource, version_item)
                getattr(app, "on_fetched_item_%s" % resource)(version_item)
    else:
        getattr(app, "on_fetched_item")(resource, response)
        getattr(app, "on_fetched_item_%s" % resource)(response)

    return response, last_modified, etag, 200


def _pagination_links(resource, req, document_count, document_id=None):
    """Returns the appropriate set of resource links depending on the
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
       HATEOAS link for contains the business unit value even when
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
    if config.DOMAIN[resource]["versioning"] is True:
        version = request.args.get(config.VERSION_PARAM)

    other_params = _other_params(req.args)
    # construct the default links
    q = querydef(req.max_results, req.where, req.sort, version, req.page, other_params)
    resource_title = config.DOMAIN[resource]["resource_title"]
    _links = {
        "parent": home_link(),
        "self": {"title": resource_title, "href": resource_link()},
    }

    # change links if document ID is given
    if document_id:
        _links["self"] = document_link(resource, document_id)
        _links["collection"] = {
            "title": resource_title,
            "href": "%s%s" % (resource_link(), q),
        }

        # make more specific links for versioned requests
        if version in ("all", "diffs"):
            _links["parent"] = {"title": resource_title, "href": resource_link()}
            _links["collection"] = document_link(resource, document_id)
        elif version:
            _links["parent"] = document_link(resource, document_id)
            _links["collection"] = {
                "title": resource_title,
                "href": "%s?version=all" % _links["parent"]["href"],
            }

    # modify the self link to add query params or version number
    if document_count:
        _links["self"]["href"] = "%s%s" % (_links["self"]["href"], q)
    elif not document_count and version and version not in ("all", "diffs"):
        _links["self"] = document_link(resource, document_id, version)

    # create pagination links
    if config.DOMAIN[resource]["pagination"]:
        # strip any queries from the self link if present
        _pagination_link = _links["self"]["href"].split("?")[0]

        if (
            req.page * req.max_results < (document_count or 0)
            or config.OPTIMIZE_PAGINATION_FOR_SPEED
        ):
            q = querydef(
                req.max_results,
                req.where,
                req.sort,
                version,
                req.page + 1,
                other_params,
            )
            _links["next"] = {
                "title": "next page",
                "href": "%s%s" % (_pagination_link, q),
            }

            if document_count:
                last_page = int(math.ceil(document_count / float(req.max_results)))
                q = querydef(
                    req.max_results,
                    req.where,
                    req.sort,
                    version,
                    last_page,
                    other_params,
                )
                _links["last"] = {
                    "title": "last page",
                    "href": "%s%s" % (_pagination_link, q),
                }

        if req.page > 1:
            q = querydef(
                req.max_results,
                req.where,
                req.sort,
                version,
                req.page - 1,
                other_params,
            )
            _links["prev"] = {
                "title": "previous page",
                "href": "%s%s" % (_pagination_link, q),
            }

    return _links


def _other_params(args):
    """Returns a multidict of params that are not used internally by Eve.

    :param args: multidict containing the request parameters
    """
    default_params = [
        config.QUERY_WHERE,
        config.QUERY_SORT,
        config.QUERY_PAGE,
        config.QUERY_MAX_RESULTS,
        config.QUERY_EMBEDDED,
        config.QUERY_PROJECTION,
        config.VERSION_PARAM,
    ]
    return MultiDict(
        (key, value)
        for key, values in args.lists()
        for value in values
        if key not in default_params
    )


def _meta_links(req, count):
    """Reterns the meta links for a paginated query.

    :param req: parsed request object.
    :param count: total number of documents in a query.

    .. versionadded:: 0.5
    """
    meta = {config.QUERY_PAGE: req.page, config.QUERY_MAX_RESULTS: req.max_results}
    if config.OPTIMIZE_PAGINATION_FOR_SPEED is False:
        meta["total"] = count
    return meta
