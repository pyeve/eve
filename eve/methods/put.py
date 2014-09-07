# -*- coding: utf-8 -*-

"""
    eve.methods.put
    ~~~~~~~~~~~~~~~

    This module imlements the PUT method.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from werkzeug import exceptions
from datetime import datetime
from eve.auth import requires_auth
from eve.defaults import resolve_default_values
from eve.validation import ValidationError
from flask import current_app as app, abort
from eve.utils import config, debug_error_message, parse_request
from eve.methods.common import get_document, parse, payload as payload_, \
    ratelimit, pre_event, store_media_files, resolve_user_restricted_access, \
    resolve_embedded_fields, build_response_document, marshal_write_response, \
    resolve_document_etag
from eve.versioning import resolve_document_version, \
    insert_versioning_documents, late_versioning_catch


@ratelimit()
@requires_auth('item')
@pre_event
def put(resource, **lookup):
    """
    Default function for handling PUT requests, it has decorators for
    rate limiting, authentication and for raising pre-request events.
    After the decorators are applied forwards to call to :func:`put_internal`

    .. versionchanged:: 0.5
       Split into put() and put_internal().
    """
    return put_internal(resource, concurrency_check=True, **lookup)


def put_internal(resource, concurrency_check=False, **lookup):
    """ Perform a document replacement. Updates are first validated against
    the resource schema. If validation passes, the document is repalced and
    an OK status update is returned. If validation fails a set of validation
    issues is returned.

    :param resource: the name of the resource to which the document belongs.
    :param **lookup: document lookup query.

    .. versionchanged:: 0.5
       ETAG is now stored with the document (#369).
       Catching all HTTPExceptions and returning them to the caller, allowing
       for eventual flask.abort() invocations in callback functions to go
       through. Fixes #395.

    .. versionchanged:: 0.4
       Allow abort() to be inoked by callback functions.
       Resolve default values before validation is performed. See #353.
       Raise 'on_replace' instead of 'on_insert'. The callback function gets
       the document (as opposed to a list of just 1 document) as an argument.
       Support for document versioning.
       Raise `on_replaced` after the document has been replaced

    .. versionchanged:: 0.3
       Support for media fields.
       When IF_MATCH is disabled, no etag is included in the payload.
       Support for new validation format introduced with Cerberus v0.5.

    .. versionchanged:: 0.2
       Use the new STATUS setting.
       Use the new ISSUES setting.
       Raise pre_<method> event.
       explictly resolve default values instead of letting them be resolved
       by common.parse. This avoids a validation error when a read-only field
       also has a default value.

    .. versionchanged:: 0.1.1
       auth.request_auth_value is now used to store the auth_field value.
       Item-identifier wrapper stripped from both request and response payload.

    .. versionadded:: 0.1.0
    """
    resource_def = app.config['DOMAIN'][resource]
    schema = resource_def['schema']
    validator = app.validator(schema, resource)

    payload = payload_()
    original = get_document(resource, concurrency_check, **lookup)
    if not original:
        # not found
        abort(404)

    last_modified = None
    etag = None
    issues = {}
    object_id = original[config.ID_FIELD]

    response = {}

    if config.BANDWIDTH_SAVER is True:
        embedded_fields = []
    else:
        req = parse_request(resource)
        embedded_fields = resolve_embedded_fields(resource, req)

    try:
        document = parse(payload, resource)
        resolve_default_values(document, resource_def['defaults'])
        validation = validator.validate_replace(document, object_id)
        if validation:
            # sneak in a shadow copy if it wasn't already there
            late_versioning_catch(original, resource)

            # update meta
            last_modified = datetime.utcnow().replace(microsecond=0)
            document[config.LAST_UPDATED] = last_modified
            document[config.DATE_CREATED] = original[config.DATE_CREATED]

            # ID_FIELD not in document means it is not being automatically
            # handled (it has been set to a field which exists in the resource
            # schema.
            if config.ID_FIELD not in document:
                document[config.ID_FIELD] = object_id

            resolve_user_restricted_access(document, resource)
            store_media_files(document, resource, original)
            resolve_document_version(document, resource, 'PUT', original)

            # notify callbacks
            getattr(app, "on_replace")(resource, document, original)
            getattr(app, "on_replace_%s" % resource)(document, original)

            resolve_document_etag(document)

            # write to db
            app.data.replace(resource, object_id, document)
            insert_versioning_documents(resource, document)

            # notify callbacks
            getattr(app, "on_replaced")(resource, document, original)
            getattr(app, "on_replaced_%s" % resource)(document, original)

            # build the full response document
            build_response_document(
                document, resource, embedded_fields, document)
            response = document
        else:
            issues = validator.errors
    except ValidationError as e:
        # TODO should probably log the error and abort 400 instead (when we
        # got logging)
        issues['validator exception'] = str(e)
    except exceptions.HTTPException as e:
        raise e
    except Exception as e:
        # consider all other exceptions as Bad Requests
        abort(400, description=debug_error_message(
            'An exception occurred: %s' % e
        ))

    if len(issues):
        response[config.ISSUES] = issues
        response[config.STATUS] = config.STATUS_ERR
        status = config.VALIDATION_ERROR_STATUS
    else:
        response[config.STATUS] = config.STATUS_OK
        status = 200

    # limit what actually gets sent to minimize bandwidth usage
    response = marshal_write_response(response, resource)

    return response, last_modified, etag, status
