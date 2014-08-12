# -*- coding: utf-8 -*-

"""
    eve.methods.common
    ~~~~~~~~~~~~~~~~~~

    Utility functions for API methods implementations.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import time
import base64
from datetime import datetime
from flask import current_app as app, request, abort, g, Response
import simplejson as json
from functools import wraps
from eve.utils import parse_request, document_etag, config, request_method, \
    debug_error_message, auto_fields
from eve.versioning import resolve_document_version, \
    get_data_version_relation_document, missing_version_field


def get_document(resource, **lookup):
    """ Retrieves and return a single document. Since this function is used by
    the editing methods (POST, PATCH, DELETE), we make sure that the client
    request references the current representation of the document before
    returning it.

    :param resource: the name of the resource to which the document belongs to.
    :param **lookup: document lookup query

    .. versionchanged:: 0.0.9
       More informative error messages.

    .. versionchanged:: 0.0.5
      Pass current resource to ``parse_request``, allowing for proper
      processing of new configuration settings: `filters`, `sorting`, `paging`.
    """
    req = parse_request(resource)
    document = app.data.find_one(resource, None, **lookup)
    if document:

        if not req.if_match and config.IF_MATCH:
            # we don't allow editing unless the client provides an etag
            # for the document
            abort(403, description=debug_error_message(
                'An etag must be provided to edit a document'
            ))

        # ensure the retrieved document has LAST_UPDATED and DATE_CREATED,
        # eventually with same default values as in GET.
        document[config.LAST_UPDATED] = last_updated(document)
        document[config.DATE_CREATED] = date_created(document)

        if req.if_match and req.if_match != document_etag(document):
            # client and server etags must match, or we don't allow editing
            # (ensures that client's version of the document is up to date)
            abort(412, description=debug_error_message(
                'Client and server etags don\'t match'
            ))

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
    content_type = request.headers['Content-Type'].split(';')[0]

    if content_type == 'application/json':
        return request.get_json()
    elif content_type == 'application/x-www-form-urlencoded':
        return request.form.to_dict() if len(request.form) else \
            abort(400, description=debug_error_message(
                'No form-urlencoded data supplied'
            ))
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
            abort(400, description=debug_error_message(
                'No multipart/form-data supplied'
            ))
    else:
        abort(400, description=debug_error_message(
            'Unknown or no Content-Type header supplied'))


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

    .. versionchanged:: 0.3
       Fix serialization of sub-documents. See #244.

    .. versionadded:: 0.1.1
    """
    if app.data.serializers:
        if resource:
            schema = config.DOMAIN[resource]['schema']
        if not fields:
            fields = document.keys()
        for field in fields:
            if field in schema:
                field_schema = schema[field]
                field_type = field_schema['type']
                if 'schema' in field_schema:
                    field_schema = field_schema['schema']
                    if 'dict' in (field_type, field_schema.get('type', '')):
                        # either a dict or a list of dicts
                        embedded = [document[field]] if field_type == 'dict' \
                            else document[field]
                        for subdocument in embedded:
                            if 'schema' in field_schema:
                                serialize(subdocument,
                                          schema=field_schema['schema'])
                            else:
                                serialize(subdocument, schema=field_schema)
                    else:
                        # a list of one type, arbirtrary length
                        field_type = field_schema['type']
                        if field_type in app.data.serializers:
                            for i, v in enumerate(document[field]):
                                document[field][i] = \
                                    app.data.serializers[field_type](v)
                elif 'items' in field_schema:
                    # a list of multiple types, fixed length
                    for i, (s, v) in enumerate(zip(field_schema['items'],
                                                   document[field])):
                        field_type = s['type'] if 'type' in s else None
                        if field_type in app.data.serializers:
                            document[field][i] = \
                                app.data.serializers[field_type](
                                    document[field][i])
                elif field_type in app.data.serializers:
                    # a simple field
                    document[field] = \
                        app.data.serializers[field_type](document[field])
    return document


def build_response_document(
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
    # TODO: last_update could include consideration for embedded documents

    # generate ETag
    if config.IF_MATCH:
        document[config.ETAG] = document_etag(document)

    # hateoas links
    if config.DOMAIN[resource]['hateoas'] and config.ID_FIELD in document:
        document[config.LINKS] = {'self':
                                  document_link(resource,
                                                document[config.ID_FIELD])}

    # add version numbers
    resolve_document_version(document, resource, 'GET', latest_doc)

    # media and embedded documents
    resolve_media_files(document, resource)
    resolve_embedded_documents(document, resource, embedded_fields)


def resolve_embedded_fields(resource, req):
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


def resolve_embedded_documents(document, resource, embedded_fields):
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
            # support late versioning
            if document[field][config.VERSION] == 1:
                # there is a chance this document hasn't been saved
                # since versioning was turned on
                embedded_doc = missing_version_field(
                    data_relation, document[field])

                if embedded_doc is None:
                    # this document has been saved since the data_relation was
                    # made - we basically do not have the copy of the document
                    # that existed when the data relation was made, but we'll
                    # try the next best thing - the first version
                    document[field][config.VERSION] = 1
                    embedded_doc = get_data_version_relation_document(
                        data_relation, document[field])

                latest_embedded_doc = embedded_doc
            else:
                # grab the specific version
                embedded_doc = get_data_version_relation_document(
                    data_relation, document[field])

                # grab the latest version
                latest_embedded_doc = get_data_version_relation_document(
                    data_relation, document[field], latest=True)

            # make sure we got the documents
            if embedded_doc is None or latest_embedded_doc is None:
                # your database is not consistent!!! that is bad
                abort(404, description=debug_error_message(
                    "Unable to locate embedded documents for '%s'" %
                    field
                ))

            # build the response document
            build_response_document(
                embedded_doc, data_relation['resource'],
                [], latest_embedded_doc)
        else:
            embedded_doc = app.data.find_one(
                data_relation['resource'], None,
                **{config.ID_FIELD: document[field]}
            )
        if embedded_doc:
            document[field] = embedded_doc


def resolve_media_files(document, resource):
    """ Embed media files into the response document.

    :param document: the document eventually containing the media files.
    :param resource: the resource being consumed by the request.

    .. versionadded:: 0.4
    """
    for field in resource_media_fields(document, resource):
        _file = app.media.get(document[field])
        # check if we should send a basic file response
        if config.EXTENDED_MEDIA_INFO == []:
            if _file and config.RETURN_MEDIA_AS_BASE64_STRING:
                document[field] = base64.encodestring(_file.read())
            else:
                document[field] = None
        elif _file:
            # otherwise we have a valid file and should send extended response
            # start with the basic file object
            ret_file = None
            if config.RETURN_MEDIA_AS_BASE64_STRING:
                ret_file = base64.encodestring(_file.read())
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
            document[field] = None


def marshal_write_response(document, resource):
    """ Limit response document to minimize bandwidth when client supports it.

    :param document: the response document.
    :param resource: the resource being consumed by the request.

    .. versionadded:: 0.4
    """

    if app.config['BANDWIDTH_SAVER'] is True:
        # only return the automatic fields and special extra fields
        fields = auto_fields(resource) + \
            app.config['DOMAIN'][resource]['extra_response_fields']
        document = dict((k, v) for (k, v) in document.items() if k in fields)

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
        if original and hasattr(original, field):
            # since file replacement is not supported by the media storage
            # system, we first need to delete the file being replaced.
            app.media.delete(original[field])

        # store file and update document with file's unique id/filename
        # also pass in mimetype for use when retrieving the file
        document[field] = app.media.put(document[field],
                                        content_type=document[field].mimetype)


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

    schema = app.config['DOMAIN'][resource]['schema']
    fields = []
    for field, value in request.view_args.items():
        if field in schema:
            fields.append(field)
            document[field] = value

    if fields:
        serialize(document, resource, fields=fields)


def resolve_user_restricted_access(document, resource):
    """ Adds user restricted access medadata to the document if applicable.

    :param document: the document being posted or replaced
    :param resource: the resource to which the document belongs

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
        if request_auth_value and request.authorization:
            document[auth_field] = request_auth_value


def pre_event(f):
    """ Enable a Hook pre http request.

    .. versionchanged:: 0.4
       Merge 'sub_resource_lookup' (args[1]) with kwargs, so http methods can
       all enjoy the same signature, and data layer find methods can seemingly
       process both kind of queries.

    .. versionadded:: 0.2
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        method = request_method()
        event_name = 'on_pre_' + method
        resource = args[0] if args else None
        gh_params = ()
        rh_params = ()
        if method in ('GET', 'PATCH', 'DELETE', 'PUT'):
            gh_params = (resource, request, kwargs)
            rh_params = (request, kwargs)
        elif method in ('POST'):
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


def document_link(resource, document_id):
    """ Returns a link to a document endpoint.

    :param resource: the resource name.
    :param document_id: the document unique identifier.

    .. versionchanged:: 0.4
       Use the regex-neutral resource_link function.

    .. versionchanged:: 0.1.0
       No more trailing slashes in links.

    .. versionchanged:: 0.0.3
       Now returning a JSON link
    """
    return {'title': '%s' % config.DOMAIN[resource]['item_title'],
            'href': '%s/%s' % (resource_link(), document_id)}


def resource_link():
    """ Returns the current resource path complete with server name if
    available. Mostly going to be used by hatoeas functions when building
    document/resource links. The resource URL stored in the config settings
    might contain regexes and custom variable names, all of which are not
    needed in the response payload.

    .. versionadded:: 0.4
    """
    path = request.path.rstrip('/')
    if '|item' in request.endpoint:
        path = path[:path.rfind('/')]
    server_name = config.SERVER_NAME if config.SERVER_NAME else ''
    if config.URL_PROTOCOL:
        server_name = '%s://%s' % (config.URL_PROTOCOL, server_name)
    return '%s%s' % (server_name, path)
