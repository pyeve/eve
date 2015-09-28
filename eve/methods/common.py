# -*- coding: utf-8 -*-

"""
    eve.methods.common
    ~~~~~~~~~~~~~~~~~~

    Utility functions for API methods implementations.

    :copyright: (c) 2015 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import time
from datetime import datetime

import base64
import simplejson as json
from bson.errors import InvalidId
from copy import copy
from flask import current_app as app, request, abort, g, Response
from functools import wraps

from eve.utils import parse_request, document_etag, config, request_method, \
    debug_error_message, auto_fields
from eve.versioning import resolve_document_version, \
    get_data_version_relation_document


def get_document(resource, concurrency_check, **lookup):
    """ Retrieves and return a single document. Since this function is used by
    the editing methods (PUT, PATCH, DELETE), we make sure that the client
    request references the current representation of the document before
    returning it. However, this concurrency control may be turned off by
    internal functions. If resource enables soft delete, soft deleted documents
    will be returned, and must be handled by callers.

    :param resource: the name of the resource to which the document belongs to.
    :param concurrency_check: boolean check for concurrency control
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
    if config.DOMAIN[resource]['soft_delete']:
        # get_document should always fetch soft deleted documents from the db
        # callers must handle soft deleted documents
        req.show_deleted = True

    document = app.data.find_one(resource, req, **lookup)
    if document:
        if not req.if_match and config.IF_MATCH and concurrency_check:
            # we don't allow editing unless the client provides an etag
            # for the document
            abort(403, description='An etag must be provided to edit a '
                  'document')

        # ensure the retrieved document has LAST_UPDATED and DATE_CREATED,
        # eventually with same default values as in GET.
        document[config.LAST_UPDATED] = last_updated(document)
        document[config.DATE_CREATED] = date_created(document)

        if req.if_match and concurrency_check:
            ignore_fields = config.DOMAIN[resource]['etag_ignore_fields']
            etag = document.get(config.ETAG, document_etag(document,
                                ignore_fields=ignore_fields))
            if req.if_match != etag:
                # client and server etags must match, or we don't allow editing
                # (ensures that client's version of the document is up to date)
                abort(412, description='Client and server etags don\'t match')

    return document


def parse(value, resource):
    """ Safely evaluates a string containing a Python expression. We are
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
    """ Performs sanity checks or decoding depending on the Content-Type,
    then returns the request payload as a dict. If request Content-Type is
    unsupported, aborts with a 400 (Bad Request).

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
    content_type = request.headers.get('Content-Type', '').split(';')[0]

    if content_type == 'application/json':
        return request.get_json()
    elif content_type == 'application/x-www-form-urlencoded':
        return request.form.to_dict() if len(request.form) else \
            abort(400, description='No form-urlencoded data supplied')
    elif content_type == 'multipart/form-data':
        # as multipart is also used for file uploads, we let an empty
        # request.form go through as long as there are also files in the
        # request.
        if len(request.form) or len(request.files):
            # merge form fields and request files, so we get a single payload
            # to be validated against the resource schema.

            # list() is needed because Python3 items() returns a dict_view, not
            # a list as in Python2.
            return dict(list(request.form.to_dict().items()) +
                        list(request.files.to_dict().items()))
        else:
            abort(400, description='No multipart/form-data supplied')
    else:
        abort(400, description='Unknown or no Content-Type header supplied')


class RateLimit(object):
    """ Implements the Rate-Limiting logic using Redis as a backend.

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
    """ If available, returns a RateLimit instance which is valid for the
    current request-response.

    .. versionadded:: 0.0.7
    """
    return getattr(g, '_rate_limit', None)


def ratelimit():
    """ Enables support for Rate-Limits on API methods
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
            method_limit = app.config.get('RATE_LIMIT_' + request_method())
            if method_limit and app.redis:
                limit = method_limit[0]
                period = method_limit[1]
                # If authorization is being used the key is 'username'.
                # Else, fallback to client IP.
                key = 'rate-limit/%s' % (request.authorization.username
                                         if request.authorization else
                                         request.remote_addr)
                rlimit = RateLimit(key, limit, period, True)
                if rlimit.over_limit:
                    return Response('Rate limit exceeded', 429)
                # store the rate limit for further processing by
                # send_response
                g._rate_limit = rlimit
            else:
                g._rate_limit = None
            return f(*args, **kwargs)
        return rate_limited
    return decorator


def last_updated(document):
    """ Fixes document's LAST_UPDATED field value. Flask-PyMongo returns
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
    """ If DATE_CREATED is missing we assume that it has been created outside
    of the API context and inject a default value. By design all documents
    return a DATE_CREATED (and we dont' want to break existing clients).

    :param document: the document to be processed.

    .. versionchanged:: 0.1.0
       Moved to common.py and renamed as public, so it can also be used by edit
       methods (via get_document()).

    .. versionadded:: 0.0.5
    """
    return document[config.DATE_CREATED] if config.DATE_CREATED in document \
        else epoch()


def epoch():
    """ A datetime.min alternative which won't crash on us.

    .. versionchanged:: 0.1.0
       Moved to common.py and renamed as public, so it can also be used by edit
       methods (via get_document()).

    .. versionadded:: 0.0.5
    """
    return datetime(1970, 1, 1)


def serialize(document, resource=None, schema=None, fields=None):
    """ Recursively handles field values that require data-aware serialization.
    Relies on the app.data.serializers dictionary.

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

    normalize_dotted_fields(document)

    if app.data.serializers:
        if resource:
            schema = config.DOMAIN[resource]['schema']
        if not fields:
            fields = document.keys()
        for field in fields:
            if field in schema:
                field_schema = schema[field]
                field_type = field_schema.get('type')
                if 'schema' in field_schema:
                    field_schema = field_schema['schema']
                    if 'dict' in (field_type, field_schema.get('type')):
                        # either a dict or a list of dicts
                        embedded = [document[field]] if field_type == 'dict' \
                            else document[field]
                        for subdocument in embedded:
                            if type(subdocument) is not dict:
                                # value is not a dict - continue serialization
                                # error will be reported by validation if
                                # appropriate (could be allowed nullable dict)
                                continue
                            elif 'schema' in field_schema:
                                serialize(subdocument,
                                          schema=field_schema['schema'])
                            else:
                                serialize(subdocument, schema=field_schema)
                    elif field_schema.get('type') == 'list':
                        # a list of lists
                        sublist_schema = field_schema.get('schema')
                        item_type = sublist_schema.get('type')
                        for sublist in document[field]:
                            for i, v in enumerate(sublist):
                                if item_type == 'dict':
                                    serialize(sublist[i],
                                              schema=sublist_schema['schema'])
                                elif item_type in app.data.serializers:
                                        sublist[i] = \
                                            app.data.serializers[item_type](v)
                    else:
                        # a list of one type, arbitrary length
                        field_type = field_schema.get('type')
                        if field_type in app.data.serializers:
                            for i, v in enumerate(document[field]):
                                document[field][i] = \
                                    app.data.serializers[field_type](v)
                elif 'items' in field_schema:
                    # a list of multiple types, fixed length
                    for i, (s, v) in enumerate(zip(field_schema['items'],
                                                   document[field])):
                        field_type = s.get('type')
                        if field_type in app.data.serializers:
                            document[field][i] = \
                                app.data.serializers[field_type](
                                    document[field][i])
                elif 'valueschema' in field_schema:
                    # a valueschema
                    field_type = field_schema['valueschema']['type']
                    if field_type == 'objectid':
                        target = document[field]
                        for field in target:
                            target[field] = \
                                app.data.serializers[field_type](target[field])
                elif field_type in app.data.serializers:
                    # a simple field
                    try:
                        document[field] = \
                            app.data.serializers[field_type](document[field])
                    except (ValueError, InvalidId):
                        # value can't be casted, we continue processing the
                        # rest of the document. Validation will later report
                        # back the issue.
                        pass
    return document


def normalize_dotted_fields(document):
    """ Normalizes eventual dotted fields so validation can be performed
    seamlessly. For example this document:

        {"location.city": "a nested cisty"}

    would be normalized to:

        {"location": {"city": "a nested city"}}

    Being recursive, normalizing of sub-documents is also supported. For
    example:

        {"location": {"city": "a city", "sub.address": "a subaddress"}}

    would be normalized to:

        {"location": {"city": "a city", "sub": {"address": "a subaddress}}}

    .. versionadded:: 0.6
    """
    for field in document.keys():
        if '.' in field:
            parts = field.split('.')
            prev = document
            for part in parts[:-1]:
                if part not in prev:
                    prev[part] = {}
                prev = prev[part]
            prev[parts[-1]] = document[field]
            document.pop(field)
        elif isinstance(document[field], dict):
            normalize_dotted_fields(document[field])


def build_response_document(
        document, resource, embedded_fields, latest_doc=None):
    """ Prepares a document for response including generation of ETag and
    metadata fields.

    :param document: the document to embed other documents into.
    :param resource: the resource name.
    :param embedded_fields: the list of fields we are allowed to embed.
    :param document: the latest version of document.

    .. versionchanged:: 0.5
       Only compute ETAG if necessary (#369).
       Add version support (#475).

    .. versionadded:: 0.4
    """
    resource_def = config.DOMAIN[resource]

    # need to update the document field since the etag must be computed on the
    # same document representation that might have been used in the collection
    # 'get' method
    document[config.DATE_CREATED] = date_created(document)
    document[config.LAST_UPDATED] = last_updated(document)

    # Up to v0.4 etags were not stored with the documents.
    if config.IF_MATCH and config.ETAG not in document:
        ignore_fields = resource_def['etag_ignore_fields']
        document[config.ETAG] = document_etag(document,
                                              ignore_fields=ignore_fields)

    # hateoas links
    if resource_def['hateoas'] and resource_def['id_field'] in document:
        version = None
        if resource_def['versioning'] is True \
                and request.args.get(config.VERSION_PARAM):
            version = document[config.VERSION]

        self_dict = {'self': document_link(resource,
                                           document[resource_def['id_field']],
                                           version)}
        if config.LINKS not in document:
            document[config.LINKS] = self_dict
        elif 'self' not in document[config.LINKS]:
            document[config.LINKS].update(self_dict)

    # add version numbers
    resolve_document_version(document, resource, 'GET', latest_doc)

    # resolve media
    resolve_media_files(document, resource)

    # resolve soft delete
    if resource_def['soft_delete'] is True:
        if document.get(config.DELETED) is None:
            document[config.DELETED] = False
        elif document[config.DELETED] is True:
            # Soft deleted documents are sent without expansion of embedded
            # documents. Return before resolving them.
            return

    # resolve embedded documents
    resolve_embedded_documents(document, resource, embedded_fields)


def field_definition(resource, chained_fields):
    """ Resolves query string to resource with dot notation like
    'people.address.city' and returns corresponding field definition
    of the resource

    :param resource: the resource name whose field to be accepted.
    :param chained_fields: query string to retrieve field definition

    .. versionadded 0.5
    """
    definition = config.DOMAIN[resource]
    subfields = chained_fields.split('.')

    for field in subfields:
        if field not in definition.get('schema', {}):
            if 'data_relation' in definition:
                sub_resource = definition['data_relation']['resource']
                definition = config.DOMAIN[sub_resource]

        if field not in definition['schema']:
            return
        definition = definition['schema'][field]
        field_type = definition.get('type')
        if field_type == 'list':
            definition = definition['schema']
        elif field_type == 'objectid':
            pass
    return definition


def resolve_embedded_fields(resource, req):
    """ Returns a list of validated embedded fields from the incoming request
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
            abort(400, description='Unable to parse `embedded` clause')

        # Build the list of fields where embedding is being requested
        try:
            embedded_fields = [k for k, v in client_embedding.items()
                               if v == 1]
            non_embedded_fields = [k for k, v in client_embedding.items()
                                   if v == 0]
        except AttributeError:
            # We got something other than a dict
            abort(400, description='Unable to parse `embedded` clause')

    embedded_fields = list(
        (set(config.DOMAIN[resource]['embedded_fields']) |
         set(embedded_fields)) - set(non_embedded_fields))

    # For each field, is the field allowed to be embedded?
    # Pick out fields that have a `data_relation` where `embeddable=True`
    enabled_embedded_fields = []
    for field in sorted(embedded_fields, key=lambda a: a.count('.')):
        # Reject bogus field names
        field_def = field_definition(resource, field)
        if field_def:
            if field_def.get('type') == 'list':
                field_def = field_def['schema']
            if 'data_relation' in field_def and \
                    field_def['data_relation'].get('embeddable'):
                # or could raise 400 here
                enabled_embedded_fields.append(field)

    return enabled_embedded_fields


def embedded_document(reference, data_relation, field_name):
    """ Returns a document to be embedded by reference using data_relation
    taking into account document versions

    :param reference: reference to the document to be embedded.
    :param data_relation: the relation schema definition.
    :param field_name: field name used in abort message only

    .. versionadded:: 0.5
    """
    # Retrieve and serialize the requested document
    if 'version' in data_relation and data_relation['version'] is True:
        # grab the specific version
        embedded_doc = get_data_version_relation_document(
            data_relation, reference)

        # grab the latest version
        latest_embedded_doc = get_data_version_relation_document(
            data_relation, reference, latest=True)

        # make sure we got the documents
        if embedded_doc is None or latest_embedded_doc is None:
            # your database is not consistent!!! that is bad
            # TODO: we should notify the developers with a log.
            abort(404, description=debug_error_message(
                "Unable to locate embedded documents for '%s'" %
                field_name
            ))

        build_response_document(embedded_doc, data_relation['resource'],
                                [], latest_embedded_doc)
    else:
        subresource = data_relation['resource']
        id_field = config.DOMAIN[subresource]['id_field']
        embedded_doc = app.data.find_one(subresource, None,
                                         **{id_field: reference})
        if embedded_doc:
            resolve_media_files(embedded_doc, subresource)

    return embedded_doc


def subdocuments(fields_chain, resource, document):
    """ Traverses the given document and yields subdocuments which
    correspond to the given fields_chain

    :param fields_chain: list of nested field names.
    :param resource: the resource name.
    :param document: document to be traversed

    .. versionadded:: 0.5
    """
    if len(fields_chain) == 0:
        yield document
    elif isinstance(document, dict) and fields_chain[0] in document:
        subdocument = document[fields_chain[0]]
        docs = subdocument if isinstance(subdocument, list) else [subdocument]
        try:
            resource = field_definition(
                resource, fields_chain[0])['data_relation']['resource']
        except KeyError:
            resource = resource

        for doc in docs:
            for result in subdocuments(fields_chain[1:], resource, doc):
                yield result
    else:
        yield document


def resolve_embedded_documents(document, resource, embedded_fields):
    """ Loops through the documents, adding embedded representations
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

    .. versionchagend:: 0.5
       Support for embedding documents located in subdocuments.
       Allocated two functions embedded_document and subdocuments.

    .. versionchagend:: 0.4
        Moved parsing of embedded fields to _resolve_embedded_fields.
        Support for document versioning.

    .. versionchagend:: 0.2
        Support for 'embedded_fields'.

    .. versonchanged:: 0.1.1
       'collection' key has been renamed to 'resource' (data_relation).

    .. versionadded:: 0.1.0
    """
    # NOTE(Gonéri): We resolve the embedded documents at the end.
    for field in sorted(embedded_fields, key=lambda a: a.count('.')):
        data_relation = field_definition(resource, field)['data_relation']
        getter = lambda ref: embedded_document(ref, data_relation, field)  # noqa
        fields_chain = field.split('.')
        last_field = fields_chain[-1]
        for subdocument in subdocuments(fields_chain[:-1], resource, document):
            if last_field not in subdocument:
                continue
            if isinstance(subdocument[last_field], list):
                subdocument[last_field] = list(map(getter,
                                                   subdocument[last_field]))
            else:
                subdocument[last_field] = getter(subdocument[last_field])


def resolve_media_files(document, resource):
    """ Embed media files into the response document.

    :param document: the document eventually containing the media files.
    :param resource: the resource being consumed by the request.

    .. versionadded:: 0.4
    """
    for field in resource_media_fields(document, resource):
        file_id = document[field]
        _file = app.media.get(file_id, resource)

        if _file:
            # otherwise we have a valid file and should send extended response
            # start with the basic file object
            if config.RETURN_MEDIA_AS_BASE64_STRING:
                ret_file = base64.encodestring(_file.read())
            elif config.RETURN_MEDIA_AS_URL:
                prefix = config.MEDIA_BASE_URL if config.MEDIA_BASE_URL \
                    is not None else app.api_prefix
                ret_file = '%s/%s/%s' % (prefix, config.MEDIA_ENDPOINT,
                                         file_id)
            else:
                ret_file = None

            if config.EXTENDED_MEDIA_INFO:
                document[field] = {
                    'file': ret_file,
                }

                # check if we should return any special fields
                for attribute in config.EXTENDED_MEDIA_INFO:
                    if hasattr(_file, attribute):
                        # add extended field if found in the file object
                        document[field].update({
                            attribute: getattr(_file, attribute)
                        })
                    else:
                        # tried to select an invalid attribute
                        abort(500, description=debug_error_message(
                            'Invalid extended media attribute requested'
                        ))
            else:
                document[field] = ret_file
        else:
            document[field] = None


def marshal_write_response(document, resource):
    """ Limit response document to minimize bandwidth when client supports it.

    :param document: the response document.
    :param resource: the resource being consumed by the request.

    .. versionchanged: 0.5
       Avoid exposing 'auth_field' if it is not intended to be public.

    .. versionadded:: 0.4
    """

    resource_def = app.config['DOMAIN'][resource]
    if app.config['BANDWIDTH_SAVER'] is True:
        # only return the automatic fields and special extra fields
        fields = auto_fields(resource) + resource_def['extra_response_fields']
        document = dict((k, v) for (k, v) in document.items() if k in fields)
    else:
        # avoid exposing the auth_field if it is not included in the
        # resource schema.
        auth_field = resource_def.get('auth_field')
        if auth_field and auth_field not in resource_def['schema']:
            try:
                del(document[auth_field])
            except:
                # 'auth_field' value has not been set by the auth class.
                pass
    return document


def store_media_files(document, resource, original=None):
    """ Store any media file in the underlying media store and update the
    document with unique ids of stored files.

    :param document: the document eventually containing the media files.
    :param resource: the resource being consumed by the request.
    :param original: original document being replaced or edited.

    .. versionchanged:: 0.4
       Renamed to store_media_files to deconflict with new resolve_media_files.

    .. versionadded:: 0.3
    """
    # TODO We're storing media files in advance, before the corresponding
    # document is also stored. In the rare occurance that the subsequent
    # document update fails we should probably attempt a cleanup on the storage
    # sytem. Easier said than done though.
    for field in resource_media_fields(document, resource):
        if original and field in original:
            # since file replacement is not supported by the media storage
            # system, we first need to delete the file being replaced.
            app.media.delete(original[field], resource)

        if document[field]:
            # store file and update document with file's unique id/filename
            # also pass in mimetype for use when retrieving the file
            document[field] = app.media.put(
                document[field], filename=document[field].filename,
                content_type=document[field].mimetype, resource=resource)


def resource_media_fields(document, resource):
    """ Returns a list of media fields defined in the resource schema.

    :param document: the document eventually containing the media files.
    :param resource: the resource being consumed by the request.

    .. versionadded:: 0.3
    """
    media_fields = app.config['DOMAIN'][resource]['_media']
    return [field for field in media_fields if field in document]


def resolve_sub_resource_path(document, resource):
    if not request.view_args:
        return

    resource_def = config.DOMAIN[resource]
    schema = resource_def['schema']
    fields = []
    for field, value in request.view_args.items():
        if field in schema and field != resource_def['id_field']:
            fields.append(field)
            document[field] = value

    if fields:
        serialize(document, resource, fields=fields)


def resolve_user_restricted_access(document, resource):
    """ Adds user restricted access medadata to the document if applicable.

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
    resource_def = app.config['DOMAIN'][resource]
    auth = resource_def['authentication']
    auth_field = resource_def['auth_field']
    if auth and auth_field:
        request_auth_value = auth.get_request_auth_value()
        if request_auth_value:
            document[auth_field] = request_auth_value


def resolve_document_etag(documents, resource):
    """ Adds etags to documents.

    .. versionadded:: 0.5
    """
    if config.IF_MATCH:
        ignore_fields = config.DOMAIN[resource]['etag_ignore_fields']

        if not isinstance(documents, list):
            documents = [documents]

        for document in documents:
            document[config.ETAG] =\
                document_etag(document, ignore_fields=ignore_fields)


def pre_event(f):
    """ Enable a Hook pre http request.

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
        method = request_method()
        if method == 'HEAD':
            method = 'GET'

        event_name = 'on_pre_' + method
        resource = args[0] if args else None
        gh_params = ()
        rh_params = ()
        if method in ('GET', 'PATCH', 'DELETE', 'PUT'):
            gh_params = (resource, request, kwargs)
            rh_params = (request, kwargs)
        elif method in ('POST', ):
            # POST hook does not support the kwargs argument
            gh_params = (resource, request)
            rh_params = (request,)

        # general hook
        getattr(app, event_name)(*gh_params)
        if resource:
            # resource hook
            getattr(app, event_name + '_' + resource)(*rh_params)

        combined_args = kwargs
        if len(args) > 1:
            combined_args.update(args[1].items())
        r = f(resource, **combined_args)
        return r
    return decorated


def document_link(resource, document_id, version=None):
    """ Returns a link to a document endpoint.

    :param resource: the resource name.
    :param document_id: the document unique identifier.
    :param version: the document version. Defaults to None.

    .. versionchanged:: 0.5
       Add version support (#475).

    .. versionchanged:: 0.4
       Use the regex-neutral resource_link function.

    .. versionchanged:: 0.1.0
       No more trailing slashes in links.

    .. versionchanged:: 0.0.3
       Now returning a JSON link
    """
    version_part = '?version=%s' % version if version else ''
    return {'title': '%s' % config.DOMAIN[resource]['item_title'],
            'href': '%s/%s%s' % (resource_link(), document_id, version_part)}


def resource_link():
    """ Returns the current resource path relative to the API entry point.
    Mostly going to be used by hatoeas functions when building
    document/resource links. The resource URL stored in the config settings
    might contain regexes and custom variable names, all of which are not
    needed in the response payload.

    .. versionchanged:: 0.5
       URL is relative to API root.

    .. versionadded:: 0.4
    """
    path = request.path.strip('/')

    if '|item' in request.endpoint:
        path = path[:path.rfind('/')]

    def strip_prefix(hit):
        return path[len(hit):] if path.startswith(hit) else path

    if config.URL_PREFIX:
        path = strip_prefix(config.URL_PREFIX + '/')
    if config.API_VERSION:
        path = strip_prefix(config.API_VERSION + '/')
    return path


def oplog_push(resource, document, op, id=None):
    """ Pushes an edit operation to the oplog if included in OPLOG_METHODS. To
    save on storage space (at least on MongoDB) field names are shortened:

        'r' = resource endpoint,
        'o' = operation performed,
        'i' = unique id of the document involved,
        'pi' = client IP,
        'c' = changes

    config.LAST_UPDATED, config.LAST_CREATED and AUTH_FIELD are not being
    shortened to allow for standard endpoint behavior (so clients can
    query the endpoint with If-Modified-Since queries, and User-Restricted-
    Resource-Access will keep working on the oplog endpoint too).

    :param resource: name of the resource involved.
    :param document: updates performed with the edit operation.
    :param op: operation performed. Can be 'POST', 'PUT', 'PATCH', 'DELETE'.
    :param id: unique id of the document.

    .. versionchanged:: 0.5.4
       Use a copy of original document in order to avoid altering its state.
       See #590.

    .. versionadded:: 0.5
    """
    if not config.OPLOG or op not in config.OPLOG_METHODS:
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
            'r': config.URLS[resource],
            'o': op,
            'i': (update[resource_def['id_field']]
                  if resource_def['id_field'] in update else id),
        }
        if config.LAST_UPDATED in update:
            last_update = update[config.LAST_UPDATED]
        else:
            last_update = datetime.utcnow().replace(microsecond=0)
        entry[config.LAST_UPDATED] = entry[config.DATE_CREATED] = last_update
        if config.OPLOG_AUDIT:

            # TODO this needs further investigation. See:
            # http://esd.io/blog/flask-apps-heroku-real-ip-spoofing.html;
            # https://stackoverflow.com/questions/22868900/how-do-i-safely-get-the-users-real-ip-address-in-flask-using-mod-wsgi
            entry['ip'] = request.remote_addr

            if op in ('PATCH', 'PUT', 'DELETE'):
                # these fields are already contained in 'entry'.
                del(update[config.LAST_UPDATED])
                # legacy documents (v0.4 or less) could be missing the etag
                # field
                if config.ETAG in update:
                    del(update[config.ETAG])
                entry['c'] = update
            else:
                pass

        resolve_user_restricted_access(entry, config.OPLOG_NAME)

        entries.append(entry)

    if entries:
        app.data.insert(config.OPLOG_NAME, entries)
