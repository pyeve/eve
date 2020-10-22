# -*- coding: utf-8 -*-

"""
    eve.methods.common
    ~~~~~~~~~~~~~~~~~~

    Utility functions for API methods implementations.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import re
import base64
import time
from copy import copy
from datetime import datetime
from functools import wraps

import simplejson as json
from bson.dbref import DBRef
from bson.errors import InvalidId
from cerberus import schema_registry, rules_set_registry
from flask import abort, current_app as app, g, request
from werkzeug.datastructures import MultiDict, CombinedMultiDict

from eve.utils import (
    auto_fields,
    config,
    debug_error_message,
    document_etag,
    parse_request,
)
from eve.versioning import get_data_version_relation_document, resolve_document_version
from collections import Counter


def get_document(
    resource,
    concurrency_check,
    original=None,
    check_auth_value=True,
    force_auth_field_projection=False,
    mongo_options=None,
    **lookup
):
    """Retrieves and return a single document. Since this function is used by
    the editing methods (PUT, PATCH, DELETE), we make sure that the client
    request references the current representation of the document before
    returning it. However, this concurrency control may be turned off by
    internal functions. If resource enables soft delete, soft deleted documents
    will be returned, and must be handled by callers.

    :param resource: the name of the resource to which the document belongs to.
    :param concurrency_check: boolean check for concurrency control
    :param original: in case the document was already retrieved before
    :param check_auth_value: a boolean flag indicating if the find operation
                             should consider user-restricted resource
                             access. Defaults to ``True``.
    :param force_auth_field_projection: a boolean flag indicating if the
                                        find operation should always include
                                        the user-restricted resource access
                                        field (if configured). Defaults to
                                        ``False``.
    :param mongo_options: Options to pass to PyMongo. e.g. read_preferences.
    :param **lookup: document lookup query

    .. versionchanged:: 0.6
        Return soft deleted documents.

    .. versionchanged:: 0.5
       Concurrency control optional for internal functions.
       ETAG are now stored with the document (#369).

    .. versionchanged:: 0.0.9
       More informative error messages.

    .. versionchanged:: 0.0.5
      Pass current resource to ``parse_request``, allowing for proper
      processing of new configuration settings: `filters`, `sorting`, `paging`.
    """
    req = parse_request(resource)
    if config.DOMAIN[resource]["soft_delete"]:
        # get_document should always fetch soft deleted documents from the db
        # callers must handle soft deleted documents
        req.show_deleted = True

    if original:
        document = original
    else:
        document = app.data.find_one(
            resource,
            req,
            check_auth_value,
            force_auth_field_projection,
            mongo_options=mongo_options,
            **lookup
        )

    if document:
        e_if_m = config.ENFORCE_IF_MATCH
        if_m = config.IF_MATCH
        if not req.if_match and e_if_m and if_m and concurrency_check:
            # we don't allow editing unless the client provides an etag
            # for the document or explicitly decides to allow editing by either
            # disabling the ``concurrency_check`` or ``IF_MATCH`` or
            # ``ENFORCE_IF_MATCH`` fields.
            abort(
                428,
                description="To edit a document "
                "its etag must be provided using the If-Match header",
            )

        # ensure the retrieved document has LAST_UPDATED and DATE_CREATED,
        # eventually with same default values as in GET.
        document[config.LAST_UPDATED] = last_updated(document)
        document[config.DATE_CREATED] = date_created(document)

        if req.if_match and concurrency_check:
            ignore_fields = config.DOMAIN[resource]["etag_ignore_fields"]
            etag = document.get(
                config.ETAG, document_etag(document, ignore_fields=ignore_fields)
            )
            if req.if_match != etag:
                # client and server etags must match, or we don't allow editing
                # (ensures that client's version of the document is up to date)
                abort(412, description="Client and server etags don't match")

    return document


def parse(value, resource):
    """Safely evaluates a string containing a Python expression. We are
    receiving json and returning a dict.

    :param value: the string to be evaluated.
    :param resource: name of the involved resource.

    .. versionchanged:: 0.1.1
       Serialize data-specific values as needed.

    .. versionchanged:: 0.1.0
       Support for PUT method.

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

    # if needed, get field values serialized by the data diver being used.
    # If any error occurs, assume validation will take care of it (i.e. a badly
    # formatted objectid).
    try:
        document = serialize(document, resource)
    except:
        pass

    return document


def payload():
    """Performs sanity checks or decoding depending on the Content-Type,
    then returns the request payload as a dict. If request Content-Type is
    unsupported, aborts with a 400 (Bad Request).

    .. versionchanged:: 0.7
       Allow 'multipart/form-data' form fields to be JSON encoded, once the
       MULTIPART_FORM_FIELDS_AS_JSON setting was been set.

    .. versionchanged:: 0.3
       Allow 'multipart/form-data' content type.

    .. versionchanged:: 0.1.1
       Payload returned as a standard python dict regardless of request content
       type.

    .. versionchanged:: 0.0.9
       More informative error messages.
       request.get_json() replaces the now deprecated request.json


    .. versionchanged:: 0.0.7
       Native Flask request.json preferred over json.loads.

    .. versionadded: 0.0.5
    """
    content_type = request.headers.get("Content-Type", "").split(";")[0]

    if content_type in config.JSON_REQUEST_CONTENT_TYPES:
        return request.get_json(force=True)
    elif content_type == "application/x-www-form-urlencoded":
        return (
            multidict_to_dict(request.form)
            if len(request.form)
            else abort(400, description="No form-urlencoded data supplied")
        )
    elif content_type == "multipart/form-data":
        # as multipart is also used for file uploads, we let an empty
        # request.form go through as long as there are also files in the
        # request.
        if len(request.form) or len(request.files):
            # merge form fields and request files, so we get a single payload
            # to be validated against the resource schema.

            formItems = MultiDict(request.form)

            if config.MULTIPART_FORM_FIELDS_AS_JSON:
                for key, lst in formItems.lists():
                    new_lst = []
                    for value in lst:
                        try:
                            new_lst.append(json.loads(value))
                        except ValueError:
                            new_lst.append(json.loads('"{0}"'.format(value)))
                    formItems.setlist(key, new_lst)

            payload = CombinedMultiDict([formItems, request.files])
            return multidict_to_dict(payload)

        else:
            abort(400, description="No multipart/form-data supplied")
    else:
        abort(400, description="Unknown or no Content-Type header supplied")


def multidict_to_dict(multidict):
    """Convert a MultiDict containing form data into a regular dict. If the
    config setting AUTO_COLLAPSE_MULTI_KEYS is True, multiple values with the
    same key get entered as a list. If it is False, the first entry is picked.
    """
    if config.AUTO_COLLAPSE_MULTI_KEYS:
        d = dict(multidict.lists())
        for key, value in d.items():
            if len(value) == 1:
                d[key] = value[0]
        return d
    else:
        return multidict.to_dict()


class RateLimit(object):
    """Implements the Rate-Limiting logic using Redis as a backend.

    :param key_prefix: the key used to uniquely identify a client.
    :param limit: requests limit, per period.
    :param period: limit validity period
    :param send_x_headers: True if response headers are supposed to include
                           special 'X-RateLimit' headers

    .. versionadded:: 0.0.7
    """

    # Maybe has something complicated problems.

    def __init__(self, key, limit, period, send_x_headers=True):
        self.reset = int(time.time()) + period
        self.key = key
        self.limit = limit
        self.period = period
        self.send_x_headers = send_x_headers
        p = app.redis.pipeline()
        p.incr(self.key)
        p.expireat(self.key, self.reset)
        self.current = p.execute()[0]

    remaining = property(lambda x: x.limit - x.current)
    over_limit = property(lambda x: x.current > x.limit)


def get_rate_limit():
    """If available, returns a RateLimit instance which is valid for the
    current request-response.

    .. versionadded:: 0.0.7
    """
    return getattr(g, "_rate_limit", None)


def ratelimit():
    """Enables support for Rate-Limits on API methods
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
            method_limit = app.config.get("RATE_LIMIT_" + request.method)
            if method_limit and app.redis:
                limit = method_limit[0]
                period = method_limit[1]
                # If authorization is being used the key is 'username'.
                # Else, fallback to client IP.
                key = "rate-limit/%s" % (
                    request.authorization.username
                    if request.authorization
                    else request.remote_addr
                )
                rlimit = RateLimit(key, limit, period, True)
                if rlimit.over_limit:
                    abort(429, "Rate limit exceeded")
                # store the rate limit for further processing by
                # send_response
                g._rate_limit = rlimit
            else:
                g._rate_limit = None
            return f(*args, **kwargs)

        return rate_limited

    return decorator


def last_updated(document):
    """Fixes document's LAST_UPDATED field value. Flask-PyMongo returns
    timezone-aware values while stdlib datetime values are timezone-naive.
    Comparisons between the two would fail.

    If LAST_UPDATE is missing we assume that it has been created outside of the
    API context and inject a default value, to allow for proper computing of
    Last-Modified header tag. By design all documents return a LAST_UPDATED
    (and we don't want to break existing clients).

    :param document: the document to be processed.

    .. versionchanged:: 0.1.0
       Moved to common.py and renamed as public, so it can also be used by edit
       methods (via get_document()).

    .. versionadded:: 0.0.5
    """
    if config.LAST_UPDATED in document:
        return document[config.LAST_UPDATED].replace(tzinfo=None)
    else:
        return epoch()


def date_created(document):
    """If DATE_CREATED is missing we assume that it has been created outside
    of the API context and inject a default value. By design all documents
    return a DATE_CREATED (and we dont' want to break existing clients).

    :param document: the document to be processed.

    .. versionchanged:: 0.1.0
       Moved to common.py and renamed as public, so it can also be used by edit
       methods (via get_document()).

    .. versionadded:: 0.0.5
    """
    return document[config.DATE_CREATED] if config.DATE_CREATED in document else epoch()


def epoch():
    """A datetime.min alternative which won't crash on us.

    .. versionchanged:: 0.1.0
       Moved to common.py and renamed as public, so it can also be used by edit
       methods (via get_document()).

    .. versionadded:: 0.0.5
    """
    return datetime(1970, 1, 1)


def serialize(document, resource=None, schema=None, fields=None):
    """Recursively handles field values that require data-aware serialization.
    Relies on the app.data.serializers dictionary.

    .. versionchanged: 0.8.1
       Normalize dotted fields according to normalized_dotted_fields. See #1173.

    .. versionchanged:: 0.7
       Add support for normalizing anyof-like rules inside lists. See #876.

    .. versionchanged:: 0.6
       Add support for normalizing dotted fields.

    .. versionchanged:: 0.5.4
       Fix serialization of lists of lists. See # 614.

    .. versionchanged:: 0.5.3
       Don't block on custom serialization errors so the whole document can
       be processed. See #568.

    .. versionchanged:: 0.5.2
       Fix serialization of keyschemas with objectids. See #525.

    .. versionchanged:: 0.3
       Fix serialization of sub-documents. See #244.

    .. versionadded:: 0.1.1
    """

    def resolve_schema(schema):
        return schema if isinstance(schema, dict) else schema_registry.get(schema)

    if (
        resource not in config.DOMAIN
        or config.DOMAIN[resource]["normalize_dotted_fields"]
    ):
        normalize_dotted_fields(document)

    if app.data.serializers:
        if resource:
            schema = resolve_schema(config.DOMAIN[resource]["schema"])
        if not fields:
            fields = document.keys()
        for field in fields:
            if document[field] is None:
                continue
            if field in schema:
                field_schema = schema[field]
                if not isinstance(field_schema, dict):
                    field_schema = rules_set_registry.get(field_schema)
                field_types = field_schema.get("type")
                if not isinstance(field_types, list):
                    field_types = [field_types]
                for field_type in field_types:
                    for x_of in ["allof", "anyof", "oneof", "noneof"]:
                        for optschema in field_schema.get(x_of, []):
                            optschema = dict(field_schema, **optschema)
                            optschema.pop(x_of, None)
                            serialize(document, schema={field: optschema})
                        x_of_type = "{0}_type".format(x_of)
                        for opttype in field_schema.get(x_of_type, []):
                            optschema = dict(field_schema, type=opttype)
                            optschema.pop(x_of_type, None)
                            serialize(document, schema={field: optschema})
                    if config.AUTO_CREATE_LISTS and field_type == "list":
                        # Convert single values to lists
                        if not isinstance(document[field], list):
                            document[field] = [document[field]]
                    if "schema" in field_schema:
                        field_schema = resolve_schema(field_schema["schema"])
                        if "dict" in (field_type, field_schema.get("type")):
                            # either a dict or a list of dicts
                            embedded = (
                                [document[field]]
                                if field_type == "dict"
                                else document[field]
                            )
                            for subdocument in embedded:
                                if type(subdocument) is not dict:
                                    # value is not a dict - continue
                                    # serialization error will be reported by
                                    # validation if appropriate
                                    continue
                                elif "schema" in field_schema:
                                    serialize(
                                        subdocument, schema=field_schema["schema"]
                                    )
                                else:
                                    serialize(subdocument, schema=field_schema)
                        elif field_schema.get("type") == "list":
                            # a list of lists
                            sublist_schema = resolve_schema(field_schema.get("schema"))
                            item_type = sublist_schema.get("type")
                            for sublist in document[field]:
                                for i, v in enumerate(sublist):
                                    if item_type == "dict":
                                        serialize(
                                            sublist[i], schema=sublist_schema["schema"]
                                        )
                                    elif item_type in app.data.serializers:
                                        sublist[i] = serialize_value(item_type, v)
                        elif field_schema.get("type") is None:
                            # a list of items determined by *of rules
                            for x_of in ["allof", "anyof", "oneof", "noneof"]:
                                for optschema in field_schema.get(x_of, []):
                                    serialize(
                                        document,
                                        schema={
                                            field: {
                                                "type": field_type,
                                                "schema": optschema,
                                            }
                                        },
                                    )
                                x_of_type = "{0}_type".format(x_of)
                                for opttype in field_schema.get(x_of_type, []):
                                    serialize(
                                        document,
                                        schema={
                                            field: {
                                                "type": field_type,
                                                "schema": {"type": opttype},
                                            }
                                        },
                                    )
                        else:
                            # a list of one type, arbitrary length
                            field_type = field_schema.get("type")
                            if field_type in app.data.serializers:
                                for i, v in enumerate(document[field]):
                                    document[field][i] = serialize_value(field_type, v)
                    elif "items" in field_schema:
                        # a list of multiple types, fixed length
                        for i, (s, v) in enumerate(
                            zip(field_schema["items"], document[field])
                        ):
                            field_type = s.get("type")
                            if field_type in app.data.serializers:
                                document[field][i] = serialize_value(
                                    field_type, document[field][i]
                                )
                    elif "valueschema" in field_schema:
                        # a valueschema
                        field_type = field_schema["valueschema"]["type"]
                        if field_type == "objectid":
                            target = document[field]
                            for field in target:
                                target[field] = serialize_value(
                                    field_type, target[field]
                                )
                        elif field_type == "dict":
                            for subdocument in document[field].values():
                                serialize(
                                    subdocument,
                                    schema=field_schema["valueschema"]["schema"],
                                )

                    elif field_type in app.data.serializers:
                        # a simple field
                        document[field] = serialize_value(field_type, document[field])

    return document


def serialize_value(field_type, value):
    """Serialize value of a given type. Relies on the app.data.serializers
    dictionary.
    """
    try:
        return app.data.serializers[field_type](value)
    except (KeyError, ValueError, TypeError, InvalidId):
        # value can't be cast or no serializer defined, return as is and
        # validation will later report back the issue.
        return value


def normalize_dotted_fields(document):
    """Normalizes eventual dotted fields so validation can be performed
    seamlessly. For example this document:

        {"location.city": "a nested city"}

    would be normalized to:

        {"location": {"city": "a nested city"}}

    Being recursive, normalizing of sub-documents is also supported. For
    example:

        {"location": {"city": "a city", "sub.address": "a subaddress"}}

    would be normalized to:

        {"location": {"city": "a city", "sub": {"address": "a subaddress}}}

    .. versionchanged:: 0.7
       Fix normalization of nested inputs (#738).

    .. versionadded:: 0.6
    """
    if isinstance(document, list):
        prev = document
        for i in prev:
            normalize_dotted_fields(i)
    elif isinstance(document, dict):
        for field in list(document):
            if "." in field:
                parts = field.split(".")
                prev = document
                for part in parts[:-1]:
                    if part not in prev:
                        prev[part] = {}
                    prev = prev[part]
                if isinstance(document[field], (dict, list)):
                    normalize_dotted_fields(document[field])
                prev[parts[-1]] = document[field]
                document.pop(field)
            elif isinstance(document[field], (dict, list)):
                normalize_dotted_fields(document[field])


def build_response_document(document, resource, embedded_fields, latest_doc=None):
    """Prepares a document for response including generation of ETag and
    metadata fields.

    :param document: the document to embed other documents into.
    :param resource: the resource name.
    :param embedded_fields: the list of fields we are allowed to embed.
    :param document: the latest version of document.

    .. versionchanged:: 0.8.2
       Add data relation fields hateoas support (#1204).

    .. versionchanged:: 0.5
       Only compute ETAG if necessary (#369).
       Add version support (#475).

    .. versionadded:: 0.4
    """
    resource_def = config.DOMAIN[resource]

    resolve_resource_projection(document, resource)

    # need to update the document field since the etag must be computed on the
    # same document representation that might have been used in the collection
    # 'get' method
    document[config.DATE_CREATED] = date_created(document)
    document[config.LAST_UPDATED] = last_updated(document)

    # Up to v0.4 etags were not stored with the documents.
    if config.IF_MATCH and config.ETAG not in document:
        ignore_fields = resource_def["etag_ignore_fields"]
        document[config.ETAG] = document_etag(document, ignore_fields=ignore_fields)

    # hateoas links
    if resource_def["hateoas"] and resource_def["id_field"] in document:
        version = None
        if resource_def["versioning"] is True and request.args.get(
            config.VERSION_PARAM
        ):
            version = document[config.VERSION]

        self_dict = {
            "self": document_link(resource, document[resource_def["id_field"]], version)
        }
        if config.LINKS not in document:
            document[config.LINKS] = self_dict
        elif "self" not in document[config.LINKS]:
            document[config.LINKS].update(self_dict)

        # add data relation links if hateoas enabled
        resolve_data_relation_links(document, resource)

    # add version numbers
    resolve_document_version(document, resource, "GET", latest_doc)

    # resolve media
    resolve_media_files(document, resource)

    # resolve soft delete
    if resource_def["soft_delete"] is True:
        if document.get(config.DELETED) is None:
            document[config.DELETED] = False
        elif document[config.DELETED] is True:
            # Soft deleted documents are sent without expansion of embedded
            # documents. Return before resolving them.
            return

    # resolve embedded documents
    resolve_embedded_documents(document, resource, embedded_fields)


def resolve_resource_projection(document, resource):
    """Purges a document of fields that are not included in its resource
    projecton.

    :param document: the original document.
    :param resource: the resource name.
    """

    if config.BANDWIDTH_SAVER:
        return

    resource_def = config.DOMAIN[resource]
    projection = resource_def["datasource"]["projection"]
    projection_enabled = resource_def["projection"]
    # Fix for #1338
    if not projection_enabled or not projection:
        # BANDWIDTH_SAVER is disabled, and no projection is defined or
        # projection feature is disabled, so return entire document.
        return
    fields = {
        field for field, value in projection.items() if value and field in document
    }
    fields.add(resource_def["id_field"])

    for field in set(document.keys()) - fields:
        del document[field]


def field_definition(resource, chained_fields):
    """Resolves query string to resource with dot notation like
    'people.address.city' and returns corresponding field definition
    of the resource

    :param resource: the resource name whose field to be accepted.
    :param chained_fields: query string to retrieve field definition

    .. versionchanged:: 0.8.2
       fix field definition for list without a schema. See #1204.

    .. versionadded 0.5
    """
    definition = config.DOMAIN[resource]
    subfields = chained_fields.split(".")

    for field in subfields:
        if field not in definition.get("schema", {}):
            if "data_relation" in definition:
                sub_resource = definition["data_relation"]["resource"]
                definition = config.DOMAIN[sub_resource]

        if field not in definition["schema"]:
            return
        definition = definition["schema"][field]
        field_type = definition.get("type")
        if field_type == "list":
            # the list can be 1) a list of allowed values for string and list types
            #                 2) a list of references that have schema
            # we want to resolve field definition deeper for the second one
            definition = definition.get("schema", definition)
        elif field_type == "objectid":
            pass
    return definition


def resolve_data_relation_links(document, resource):
    """Resolves all fields in a document that has data relation to other resources

    :param document: the document to include data relation links.
    :param resource: the resource name.

    .. versionadded:: 0.8.2
    """
    resource_def = config.DOMAIN[resource]
    related_dict = {}

    for field in resource_def.get("schema", {}):

        field_def = field_definition(resource, field)
        if "data_relation" not in field_def:
            continue

        if field in document and document[field] is not None:
            related_links = []

            # Make the code DRY for list of linked relation and single linked relation
            for related_document_id in (
                document[field]
                if isinstance(document[field], list)
                else [document[field]]
            ):
                # Get the resource endpoint string for the linked relation
                related_resource = (
                    related_document_id.collection
                    if isinstance(related_document_id, DBRef)
                    else field_def["data_relation"]["resource"]
                )

                # Get the item endpoint id for the linked relation
                if isinstance(related_document_id, DBRef):
                    related_document_id = related_document_id.id
                if isinstance(related_document_id, dict):
                    related_resource_field = field_definition(resource, field)[
                        "data_relation"
                    ]["field"]
                    related_document_id = related_document_id[related_resource_field]

                # Get the version for the item endpoint id
                related_version = (
                    related_document_id.get("_version")
                    if isinstance(related_document_id, dict)
                    else None
                )

                related_links.append(
                    document_link(
                        related_resource, related_document_id, related_version
                    )
                )

            if isinstance(document[field], list):
                related_dict.update({field: related_links})
            else:
                related_dict.update({field: related_links[0]})

    if related_dict != {}:
        document[config.LINKS].update({"related": related_dict})


def resolve_embedded_fields(resource, req):
    """Returns a list of validated embedded fields from the incoming request
    or from the resource definition is the request does not specify.

    :param resource: the resource name.
    :param req: and instace of :class:`eve.utils.ParsedRequest`.

    .. versionchanged:: 0.5
       Enables subdocuments embedding. #389.

    .. versionadded:: 0.4
    """
    embedded_fields = []
    non_embedded_fields = []
    if req.embedded:
        # Parse the embedded clause, we are expecting
        # something like:   '{"user":1}'
        try:
            client_embedding = json.loads(req.embedded)
        except ValueError:
            abort(400, description="Unable to parse `embedded` clause")

        # Build the list of fields where embedding is being requested
        try:
            embedded_fields = [k for k, v in client_embedding.items() if v == 1]
            non_embedded_fields = [k for k, v in client_embedding.items() if v == 0]
        except AttributeError:
            # We got something other than a dict
            abort(400, description="Unable to parse `embedded` clause")

    embedded_fields = list(
        (set(config.DOMAIN[resource]["embedded_fields"]) | set(embedded_fields))
        - set(non_embedded_fields)
    )

    # For each field, is the field allowed to be embedded?
    # Pick out fields that have a `data_relation` where `embeddable=True`
    enabled_embedded_fields = []
    for field in sorted(embedded_fields, key=lambda a: a.count(".")):
        # Reject bogus field names
        field_def = field_definition(resource, field)
        if field_def:
            if field_def.get("type") == "list":
                field_def = field_def["schema"]
            if "data_relation" in field_def and field_def["data_relation"].get(
                "embeddable"
            ):
                # or could raise 400 here
                enabled_embedded_fields.append(field)

    return enabled_embedded_fields


def embedded_document(references, data_relation, field_name):
    """Returns a document to be embedded by reference using data_relation
        taking into account document versions

        :param reference: reference to the document to be embedded.
        :param data_relation: the relation schema definition.
        :param field_name: field name used in abort message only

    )    .. versionadded:: 0.5
    """
    embedded_docs = []

    output_is_list = True

    if not isinstance(references, list):
        output_is_list = False
        references = [references]

    # Retrieve and serialize the requested document
    if "version" in data_relation and data_relation["version"] is True:
        # For the version flow, I keep the as-is logic (flow is too complex to
        # make it bulk)
        for reference in references:
            # grab the specific version
            embedded_doc = get_data_version_relation_document(data_relation, reference)

            # grab the latest version
            latest_embedded_doc = get_data_version_relation_document(
                data_relation, reference, latest=True
            )

            # make sure we got the documents
            if embedded_doc is None or latest_embedded_doc is None:
                # your database is not consistent!!! that is bad
                # TODO: we should notify the developers with a log.
                abort(
                    404,
                    description=debug_error_message(
                        "Unable to locate embedded documents for '%s'" % field_name
                    ),
                )

            build_response_document(
                embedded_doc, data_relation["resource"], [], latest_embedded_doc
            )
            embedded_docs.append(embedded_doc)
    else:
        (
            id_value_to_sort,
            list_of_id_field_name,
            subresources_query,
        ) = generate_query_and_sorting_criteria(data_relation, references)
        for subresource in subresources_query:
            result, _ = app.data.find(
                subresource, None, subresources_query[subresource]
            )
            list_embedded_doc = list(result)

            if not list_embedded_doc:
                embedded_docs.extend(
                    [None] * len(subresources_query[subresource]["$or"])
                )
            else:
                for embedded_doc in list_embedded_doc:
                    resolve_media_files(embedded_doc, subresource)
                embedded_docs.extend(list_embedded_doc)

        # After having retrieved my data, I have to be sure that the sorting of
        # the list is the same in input as in output (this is to support
        # embedding of sub-documents - only in case the storage is not done via
        # DBref)
        if embedded_docs:
            embedded_docs = sort_db_response(
                embedded_docs, id_value_to_sort, list_of_id_field_name
            )

    if output_is_list:
        return embedded_docs
    elif embedded_docs:
        return embedded_docs[0]
    else:
        return None


def sort_db_response(embedded_docs, id_value_to_sort, list_of_id_field_name):
    """Sorts the documents fetched from the database

    :param embedded_docs: the documents fetch from the database.
    :param id_value_to_sort: id_value sort criteria.
    :param list_of_id_field_name: list of name of fields
    :return embedded_docs: the list of documents sorted as per input
    """

    id_field_name_occurrences = Counter(list_of_id_field_name)
    temp_embedded_docs = []
    old_occurrence = 0

    for id_field_name in set(list_of_id_field_name):
        current_occurrence = old_occurrence + int(
            id_field_name_occurrences[id_field_name]
        )
        temp_embedded_docs.extend(
            sort_per_resource(
                embedded_docs[old_occurrence:current_occurrence],
                id_value_to_sort,
                id_field_name,
            )
        )
        old_occurrence = current_occurrence

    return temp_embedded_docs


def sort_per_resource(embedded_docs, id_values_to_sort, id_field_name):
    """Sorts the documents fetched from the database per single resource

    :param embedded_docs: list of the documents fetched from the database.
    :param id_values_to_sort: list of the id_values sort criteria.
    :param list_of_id_field_name: list of name of fields
    :param id_field_name: key name of the id field; `_id`
    :return embedded_docs: the list of documents sorted as per input
    """
    if id_values_to_sort is None:
        id_values_to_sort = []
    embedded_docs = [x for x in embedded_docs if x is not None]
    id2dict = dict((d[id_field_name], d) for d in embedded_docs)
    temporary_embedded_docs = []
    for id_value_ in id_values_to_sort:
        if id_value_ in id2dict:
            temporary_embedded_docs.append(id2dict[id_value_])

    return temporary_embedded_docs


def generate_query_and_sorting_criteria(data_relation, references):
    """Generate query and sorting critiria

    :param data_relation: data relation for the resource.
    :param references: DBRef or id to use to embed the document.
    :returns id_value_to_sort: list of ids to use in the sort
             list_of_id_field_name: list of field name (important only for
                                    DBRef)
             subresources_query: the list of query to perform per resource
                                 (in case is not DBRef, it will be only one
                                 query)
    """
    query = {"$or": []}
    subresources_query = {}
    old_subresource = ""
    id_value_to_sort = []
    # id_field name should be the same for
    # all the elements in the list
    list_of_id_field_name = []
    for counter, reference in enumerate(references):
        # if reference is DBRef take the referenced collection as subresource
        # NOTE: using DBRef, I can define several resource for each link
        subresource = (
            reference.collection
            if isinstance(reference, DBRef)
            else data_relation["resource"]
        )
        if old_subresource and old_subresource != subresource:
            add_query_to_list(query, subresource, subresources_query)
        # NOTE: in case it is a DBRef link, the id_field_name is always the _id
        # regardless the Eve set-up
        id_field_name = (
            "_id"
            if isinstance(reference, DBRef)
            else data_relation.get("field", False)
            or config.DOMAIN[subresource]["id_field"]
        )
        id_field_value = reference.id if isinstance(reference, DBRef) else reference
        query["$or"].append({id_field_name: id_field_value})
        id_value_to_sort.append(id_field_value)
        list_of_id_field_name.append(id_field_name)
        if counter == len(references) - 1:
            add_query_to_list(query, subresource, subresources_query)
    return id_value_to_sort, list_of_id_field_name, subresources_query


def add_query_to_list(query, subresource, subresource_query):
    subresource_query.update({subresource: copy(query)})
    query.clear()
    query["$or"] = []


def subdocuments(fields_chain, resource, document, prefix=""):
    """Traverses the given document and yields subdocuments which
    correspond to the given fields_chain

    :param fields_chain: list of nested field names.
    :param resource: the resource name.
    :param document: document to be traversed
    :param prefix: prefix to recursively concatenate nested field names.

    .. versionadded:: 0.5
    """
    if len(fields_chain) == 0:
        yield document
    elif isinstance(document, dict) and fields_chain[0] in document:
        subdocument = document[fields_chain[0]]
        docs = subdocument if isinstance(subdocument, list) else [subdocument]
        try:
            definition = field_definition(resource, prefix + fields_chain[0])
            if "data_relation" in definition:
                resource = definition["data_relation"]["resource"]
                prefix = ""
            else:
                prefix = prefix + fields_chain[0] + "."
        except KeyError:
            resource = resource

        for doc in docs:
            for result in subdocuments(fields_chain[1:], resource, doc, prefix):
                yield result
    else:
        yield document


def resolve_embedded_documents(document, resource, embedded_fields):
    """Loops through the documents, adding embedded representations
    of any fields that are (1) defined eligible for embedding in the
    DOMAIN and (2) requested to be embedded in the current `req`.

    Currently we support embedding of documents by references located
    in any subdocuments. For example, query embedded={"user.friends":1}
    will return a document with "user" and all his "friends" embedded,
    but only if "user" is a subdocument.

    We do not support multiple layers embeddings.

    :param document: the document to embed other documents into.
    :param resource: the resource name.
    :param embedded_fields: the list of fields we are allowed to embed.

    .. versionchanged:: 0.5
       Support for embedding documents located in subdocuments.
       Allocated two functions embedded_document and subdocuments.

    .. versionchanged:: 0.4
        Moved parsing of embedded fields to _resolve_embedded_fields.
        Support for document versioning.

    .. versionchanged:: 0.2
        Support for 'embedded_fields'.

    .. versionchanged:: 0.1.1
       'collection' key has been renamed to 'resource' (data_relation).

    .. versionadded:: 0.1.0
    """
    # NOTE(Gonéri): We resolve the embedded documents at the end.
    for field in sorted(embedded_fields, key=lambda a: a.count(".")):
        data_relation = field_definition(resource, field)["data_relation"]
        getter = lambda ref: embedded_document(ref, data_relation, field)  # noqa
        fields_chain = field.split(".")
        last_field = fields_chain[-1]
        for subdocument in subdocuments(fields_chain[:-1], resource, document):
            if not subdocument or last_field not in subdocument:
                continue
            subdocument[last_field] = getter(subdocument[last_field])


def resolve_media_files(document, resource):
    """Embed media files into the response document.

    :param document: the document eventually containing the media files.
    :param resource: the resource being consumed by the request.

    .. versionadded:: 0.4
    """
    for field in resource_media_fields(document, resource):
        if isinstance(document[field], list):
            resolved_list = []
            for file_id in document[field]:
                resolved_list.append(resolve_one_media(file_id, resource))
            document[field] = resolved_list
        else:
            document[field] = resolve_one_media(document[field], resource)


def resolve_one_media(file_id, resource):
    """ Get response for one media file """
    _file = app.media.get(file_id, resource)

    if _file:
        # otherwise we have a valid file and should send extended response
        # start with the basic file object
        if config.RETURN_MEDIA_AS_BASE64_STRING:
            ret_file = base64.b64encode(_file.read())
        elif config.RETURN_MEDIA_AS_URL:
            prefix = (
                config.MEDIA_BASE_URL
                if config.MEDIA_BASE_URL is not None
                else app.api_prefix
            )
            ret_file = "%s/%s/%s" % (prefix, config.MEDIA_ENDPOINT, file_id)
        else:
            ret_file = None

        if config.EXTENDED_MEDIA_INFO:
            ret = {"file": ret_file}

            # check if we should return any special fields
            for attribute in config.EXTENDED_MEDIA_INFO:
                if hasattr(_file, attribute):
                    # add extended field if found in the file object
                    ret.update({attribute: getattr(_file, attribute)})
                else:
                    # tried to select an invalid attribute
                    abort(
                        500,
                        description=debug_error_message(
                            "Invalid extended media attribute requested"
                        ),
                    )

            return ret
        else:
            return ret_file
    else:
        return None


def marshal_write_response(document, resource):
    """Limit response document to minimize bandwidth when client supports it.

    :param document: the response document.
    :param resource: the resource being consumed by the request.

    .. versionchanged: 0.5
       Avoid exposing 'auth_field' if it is not intended to be public.

    .. versionadded:: 0.4
    """

    resource_def = app.config["DOMAIN"][resource]
    if app.config["BANDWIDTH_SAVER"] is True:
        # only return the automatic fields and special extra fields
        fields = auto_fields(resource) + resource_def["extra_response_fields"]
        document = dict((k, v) for (k, v) in document.items() if k in fields)
    else:
        # avoid exposing the auth_field if it is not included in the
        # resource schema.
        auth_field = resource_def.get("auth_field")
        if auth_field and auth_field not in resource_def["schema"]:
            try:
                del document[auth_field]
            except:
                # 'auth_field' value has not been set by the auth class.
                pass
    return document


def store_media_files(document, resource, original=None):
    """Store any media file in the underlying media store and update the
    document with unique ids of stored files.

    :param document: the document eventually containing the media files.
    :param resource: the resource being consumed by the request.
    :param original: original document being replaced or edited.

    .. versionchanged:: 0.4
       Renamed to store_media_files to deconflict with new resolve_media_files.

    .. versionadded:: 0.3
    """
    # TODO We're storing media files in advance, before the corresponding
    # document is also stored. In the rare occurrence that the subsequent
    # document update fails we should probably attempt a cleanup on the storage
    # system. Easier said than done though.
    for field in resource_media_fields(document, resource):
        if original and field in original:
            # since file replacement is not supported by the media storage
            # system, we first need to delete the files being replaced.
            if isinstance(original[field], list):
                for file_id in original[field]:
                    app.media.delete(file_id, resource)
            else:
                app.media.delete(original[field], resource)

        if document[field]:
            # store files and update document with file's unique id/filename
            # also pass in mimetype for use when retrieving the file
            if isinstance(document[field], list):
                id_lst = []
                for stor_obj in document[field]:
                    id_lst.append(
                        app.media.put(
                            stor_obj,
                            filename=stor_obj.filename,
                            content_type=stor_obj.mimetype,
                            resource=resource,
                        )
                    )
                document[field] = id_lst
            else:
                document[field] = app.media.put(
                    document[field],
                    filename=document[field].filename,
                    content_type=document[field].mimetype,
                    resource=resource,
                )


def resource_media_fields(document, resource):
    """Returns a list of media fields defined in the resource schema.

    :param document: the document eventually containing the media files.
    :param resource: the resource being consumed by the request.

    .. versionadded:: 0.3
    """
    media_fields = app.config["DOMAIN"][resource]["_media"]
    return [field for field in media_fields if field in document]


def resolve_sub_resource_path(document, resource):
    if not request.view_args:
        return

    resource_def = config.DOMAIN[resource]
    schema = resource_def["schema"]
    fields = []
    for field, value in request.view_args.items():
        if field in schema and field != resource_def["id_field"]:
            fields.append(field)
            document[field] = value

    if fields:
        serialize(document, resource, fields=fields)


def resolve_user_restricted_access(document, resource):
    """Adds user restricted access metadata to the document if applicable.

    :param document: the document being posted or replaced
    :param resource: the resource to which the document belongs

    .. versionchanged:: 0.5.2
       Make User Restricted Resource Access work with HMAC Auth too.

    .. versionchanged:: 0.4
       Use new auth.request_auth_value() method.

    .. versionadded:: 0.3
    """
    # if 'user-restricted resource access' is enabled and there's
    # an Auth request active, inject the username into the document
    resource_def = app.config["DOMAIN"][resource]
    auth = resource_def["authentication"]
    auth_field = resource_def["auth_field"]
    if auth and auth_field:
        request_auth_value = auth.get_request_auth_value()
        if request_auth_value:
            document[auth_field] = request_auth_value


def resolve_document_etag(documents, resource):
    """Adds etags to documents.

    .. versionadded:: 0.5
    """
    if config.IF_MATCH:
        ignore_fields = config.DOMAIN[resource]["etag_ignore_fields"]

        if not isinstance(documents, list):
            documents = [documents]

        for document in documents:
            document[config.ETAG] = document_etag(document, ignore_fields=ignore_fields)


def pre_event(f):
    """Enable a Hook pre http request.

    .. versionchanged:: 0.6
       Enable callback hooks for HEAD requests.

    .. versionchanged:: 0.4
       Merge 'sub_resource_lookup' (args[1]) with kwargs, so http methods can
       all enjoy the same signature, and data layer find methods can seemingly
       process both kind of queries.

    .. versionadded:: 0.2
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        method = request.method
        if method == "HEAD":
            method = "GET"

        event_name = "on_pre_" + method
        resource = args[0] if args else None
        gh_params = ()
        rh_params = ()
        combined_args = kwargs

        if len(args) > 1:
            combined_args.update(args[1].items())

        if method in ("GET", "PATCH", "DELETE", "PUT"):
            gh_params = (resource, request, combined_args)
            rh_params = (request, combined_args)
        elif method in ("POST",):
            # POST hook does not support the kwargs argument
            gh_params = (resource, request)
            rh_params = (request,)

        # general hook
        getattr(app, event_name)(*gh_params)
        if resource:
            # resource hook
            getattr(app, event_name + "_" + resource)(*rh_params)

        r = f(resource, **combined_args)
        return r

    return decorated


def document_link(resource, document_id, version=None):
    """Returns a link to a document endpoint.

    :param resource: the resource name.
    :param document_id: the document unique identifier.
    :param version: the document version. Defaults to None.

    .. versionchanged:: 0.8.2
       Support document link for data relation resources. See #1204.

    .. versionchanged:: 0.5
       Add version support (#475).

    .. versionchanged:: 0.4
       Use the regex-neutral resource_link function.

    .. versionchanged:: 0.1.0
       No more trailing slashes in links.

    .. versionchanged:: 0.0.3
       Now returning a JSON link
    """
    version_part = "?version=%s" % version if version else ""
    return {
        "title": "%s" % config.DOMAIN[resource]["item_title"],
        "href": "%s/%s%s" % (resource_link(resource), document_id, version_part),
    }


def resource_link(resource=None):
    """Returns the current resource path relative to the API entry point.
    Mostly going to be used by hateoas functions when building
    document/resource links. The resource URL stored in the config settings
    might contain regexes and custom variable names, all of which are not
    needed in the response payload.

    :param resource: the resource name if not using the resource from request.path

    .. versionchanged:: 0.8.2
       Support resource link for data relation resources
       which may be different from request.path resource. See #1204.

    .. versionchanged:: 0.5
       URL is relative to API root.

    .. versionadded:: 0.4
    """
    path = request.path.strip("/")

    if request.endpoint and "|item" in request.endpoint:
        path = path[: path.rfind("/")]

    def strip_prefix(hit):
        return path[len(hit) :] if path.startswith(hit) else path

    if config.URL_PREFIX:
        path = strip_prefix(config.URL_PREFIX + "/")
    if config.API_VERSION:
        path = strip_prefix(config.API_VERSION + "/")

    # If request path does not match resource URL regex definition
    # We are creating a path for data relation resources
    if resource and not re.search(config.DOMAIN[resource]["url"], path):
        return config.DOMAIN[resource]["url"]
    else:
        return path


def oplog_push(resource, document, op, id=None):
    """Pushes an edit operation to the oplog if included in OPLOG_METHODS. To
    save on storage space (at least on MongoDB) field names are shortened:

        'r' = resource endpoint,
        'o' = operation performed,
        'i' = unique id of the document involved,
        'ip' = client IP,
        'c' = changes

    config.LAST_UPDATED, config.LAST_CREATED and AUTH_FIELD are not being
    shortened to allow for standard endpoint behavior (so clients can
    query the endpoint with If-Modified-Since queries, and User-Restricted-
    Resource-Access will keep working on the oplog endpoint too).

    :param resource: name of the resource involved.
    :param document: updates performed with the edit operation.
    :param op: operation performed. Can be 'POST', 'PUT', 'PATCH', 'DELETE'.
    :param id: unique id of the document.

    .. versionchanged:: 0.7
       Add user information to the audit. Closes #846.
       Raise on_oplog_push event.
       Add support for 'extra' custom field.

    .. versionchanged:: 0.5.4
       Use a copy of original document in order to avoid altering its state.
       See #590.

    .. versionadded:: 0.5
    """

    if (
        not config.OPLOG
        or op not in config.OPLOG_METHODS
        or resource not in config.URLS
    ):
        return

    resource_def = config.DOMAIN[resource]

    if document is None:
        updates = {}
    else:
        updates = copy(document)

    if not isinstance(updates, list):
        updates = [updates]

    entries = []
    for update in updates:
        entry = {
            "r": config.URLS[resource],
            "o": op,
            "i": (
                update[resource_def["id_field"]]
                if resource_def["id_field"] in update
                else id
            ),
        }
        if config.LAST_UPDATED in update:
            last_update = update[config.LAST_UPDATED]
        else:
            last_update = datetime.utcnow().replace(microsecond=0)
        entry[config.LAST_UPDATED] = entry[config.DATE_CREATED] = last_update
        if config.OPLOG_AUDIT:
            entry["ip"] = request.remote_addr

            auth = resource_def["authentication"]
            entry["u"] = auth.get_user_or_token() if auth else "n/a"

            if op in config.OPLOG_CHANGE_METHODS:
                entry["c"] = {
                    key: value
                    for key, value in update.items()
                    # these fields are already contained in 'entry'.
                    if key not in [config.ETAG, config.LAST_UPDATED]
                }
            else:
                pass

        resolve_user_restricted_access(entry, config.OPLOG_NAME)

        entries.append(entry)

    if entries:
        # notify callbacks
        getattr(app, "on_oplog_push")(resource, entries)
        # oplog push
        app.data.insert(config.OPLOG_NAME, entries)
