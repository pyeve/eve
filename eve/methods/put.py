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
from eve.validation import ValidationError
from flask import current_app as app, abort
from eve.utils import document_etag, document_link, config, debug_error_message
from eve.methods.common import get_document, parse, payload as payload_, \
    ratelimit, resolve_default_values, pre_event, resolve_media_files, \
    resolve_user_restricted_access


@ratelimit()
@requires_auth('item')
@pre_event
def put(resource, **lookup):
    """ Perform a document replacement. Updates are first validated against
    the resource schema. If validation passes, the document is repalced and
    an OK status update is returned. If validation fails a set of validation
    issues is returned.

    :param resource: the name of the resource to which the document belongs.
    :param **lookup: document lookup query.

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
    original = get_document(resource, **lookup)
    if not original:
        # not found
        abort(404)

    last_modified = None
    etag = None
    issues = {}
    object_id = original[config.ID_FIELD]

    response = {}

    try:
        document = parse(payload, resource)
        validation = validator.validate_replace(document, object_id)
        if validation:
            last_modified = datetime.utcnow().replace(microsecond=0)
            document[config.LAST_UPDATED] = last_modified
            document[config.DATE_CREATED] = original[config.DATE_CREATED]

            # ID_FIELD not in document means it is not being automatically
            # handled (it has been set to a field which exists in the resource
            # schema.
            if config.ID_FIELD not in document:
                document[config.ID_FIELD] = object_id

            resolve_user_restricted_access(document, resource)
            resolve_default_values(document, resource)
            resolve_media_files(document, resource, original)

            # notify callbacks
            getattr(app, "on_insert")(resource, [document])
            getattr(app, "on_insert_%s" % resource)([document])

            app.data.replace(resource, object_id, document)

            response[config.ID_FIELD] = document.get(config.ID_FIELD,
                                                     object_id)
            response[config.LAST_UPDATED] = last_modified

            # metadata
            if config.IF_MATCH:
                etag = response[config.ETAG] = document_etag(document)
            if resource_def['hateoas']:
                response[config.LINKS] = {
                    'self': document_link(resource, response[config.ID_FIELD])
                }
        else:
            issues = validator.errors
    except ValidationError as e:
        # TODO should probably log the error and abort 400 instead (when we
        # got logging)
        issues['validator exception'] = str(e)
    except exceptions.InternalServerError as e:
        raise e
    except Exception as e:
        # consider all other exceptions as Bad Requests
        abort(400, description=debug_error_message(
            'An exception occurred: %s' % e
        ))

    if len(issues):
        response[config.ISSUES] = issues
        response[config.STATUS] = config.STATUS_ERR
    else:
        response[config.STATUS] = config.STATUS_OK

    return response, last_modified, etag, 200
