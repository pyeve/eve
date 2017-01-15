# -*- coding: utf-8 -*-

"""
    eve.methods.put
    ~~~~~~~~~~~~~~~

    This module imlements the PUT method.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
from datetime import datetime

from flask import current_app as app, abort
from werkzeug import exceptions

from eve.auth import requires_auth
from eve.defaults import resolve_default_values
from eve.methods.common import get_document, parse, payload as payload_, \
    ratelimit, pre_event, store_media_files, resolve_user_restricted_access, \
    resolve_embedded_fields, build_response_document, marshal_write_response, \
    resolve_sub_resource_path, resolve_document_etag, oplog_push
from eve.methods.post import post_internal
from eve.utils import config, debug_error_message, parse_request
from eve.validation import ValidationError
from eve.versioning import resolve_document_version, \
    insert_versioning_documents, late_versioning_catch


@ratelimit()
@requires_auth('item')
@pre_event
def put(resource, payload=None, **lookup):
    """
    Default function for handling PUT requests, it has decorators for
    rate limiting, authentication and for raising pre-request events.
    After the decorators are applied forwards to call to :func:`put_internal`

    .. versionchanged:: 0.5
       Split into put() and put_internal().
    """
    return put_internal(resource, payload, concurrency_check=True,
                        skip_validation=False, **lookup)


def put_internal(resource, payload=None, concurrency_check=False,
                 skip_validation=False, **lookup):
    """ Intended for internal put calls, this method is not rate limited,
    authentication is not checked, pre-request events are not raised, and
    concurrency checking is optional. Performs a document replacement.
    Updates are first validated against the resource schema. If validation
    passes, the document is repalced and an OK status update is returned.
    If validation fails a set of validation issues is returned.

    :param resource: the name of the resource to which the document belongs.
    :param payload: alternative payload. When calling put() from your own code
                    you can provide an alternative payload. This can be useful,
                    for example, when you have a callback function hooked to a
                    certain endpoint, and want to perform additional put()
                    callsfrom there.

                    Please be advised that in order to successfully use this
                    option, a request context must be available.
    :param concurrency_check: concurrency check switch (bool)
    :param skip_validation: skip payload validation before write (bool)
    :param **lookup: document lookup query.

    .. versionchanged:: 0.6
       Create document if it does not exist. Closes #634.
       Allow restoring soft deleted documents via PUT

    .. versionchanged:: 0.5
       Back to resolving default values after validaton as now the validator
       can properly validate dependency even when some have default values. See
       #353.
       Original put() has been split into put() and put_internal().
       You can now pass a pre-defined custom payload to the funcion.
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

    if payload is None:
        payload = payload_()

    original = get_document(resource, concurrency_check, **lookup)
    if not original:
        if config.UPSERT_ON_PUT:
            id = lookup[resource_def['id_field']]
            # this guard avoids a bson dependency, which would be needed if we
            # wanted to use 'isinstance'. Should also be slightly faster.
            if schema[resource_def['id_field']].get('type', '') == 'objectid':
                id = str(id)
            payload[resource_def['id_field']] = id
            return post_internal(resource, payl=payload)
        else:
            abort(404)

    last_modified = None
    etag = None
    issues = {}
    object_id = original[resource_def['id_field']]

    response = {}

    if config.BANDWIDTH_SAVER is True:
        embedded_fields = []
    else:
        req = parse_request(resource)
        embedded_fields = resolve_embedded_fields(resource, req)

    try:
        document = parse(payload, resource)
        resolve_sub_resource_path(document, resource)
        if skip_validation:
            validation = True
        else:
            validation = validator.validate_replace(document, object_id,
                                                    original)
            # Apply coerced values
            document = validator.document

        if validation:
            # sneak in a shadow copy if it wasn't already there
            late_versioning_catch(original, resource)

            # update meta
            last_modified = datetime.utcnow().replace(microsecond=0)
            document[config.LAST_UPDATED] = last_modified
            document[config.DATE_CREATED] = original[config.DATE_CREATED]
            if resource_def['soft_delete'] is True:
                # PUT with soft delete enabled should always set the DELETED
                # field to False. We are either carrying through un-deleted
                # status, or restoring a soft deleted document
                document[config.DELETED] = False

            # id_field not in document means it is not being automatically
            # handled (it has been set to a field which exists in the
            # resource schema.
            if resource_def['id_field'] not in document:
                document[resource_def['id_field']] = object_id

            resolve_user_restricted_access(document, resource)
            resolve_default_values(document, resource_def['defaults'])
            store_media_files(document, resource, original)
            resolve_document_version(document, resource, 'PUT', original)

            # notify callbacks
            getattr(app, "on_replace")(resource, document, original)
            getattr(app, "on_replace_%s" % resource)(document, original)

            resolve_document_etag(document, resource)

            # write to db
            try:
                app.data.replace(
                    resource, object_id, document, original)
            except app.data.OriginalChangedError:
                if concurrency_check:
                    abort(412,
                          description='Client and server etags don\'t match')

            # update oplog if needed
            oplog_push(resource, document, 'PUT')

            insert_versioning_documents(resource, document)

            # notify callbacks
            getattr(app, "on_replaced")(resource, document, original)
            getattr(app, "on_replaced_%s" % resource)(document, original)

            # build the full response document
            build_response_document(
                document, resource, embedded_fields, document)
            response = document
            if config.IF_MATCH:
                etag = response[config.ETAG]
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
        app.logger.exception(e)
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
