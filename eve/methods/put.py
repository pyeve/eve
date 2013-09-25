# -*- coding: utf-8 -*-

"""
    eve.methods.put
    ~~~~~~~~~~~~~~~

    This module imlements the PUT method.

    :copyright: (c) 2013 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from werkzeug import exceptions
from datetime import datetime
from eve.auth import requires_auth
from eve.validation import ValidationError
from flask import current_app as app, abort, request
from eve.utils import document_etag, document_link, config, debug_error_message
from eve.methods.common import get_document, parse, payload as payload_, \
    ratelimit


@ratelimit()
@requires_auth('item')
def put(resource, **lookup):
    """Perform a document replacement. Updates are first validated against
    the resource schema. If validation passes, the document is repalced and
    an OK status update is returned. If validation fails a set of validation
    issues is returned.

    :param resource: the name of the resource to which the document belongs.
    :param **lookup: document lookup query.

    .. versionadded:: 0.1.0
    """
    resource_def = app.config['DOMAIN'][resource]
    schema = resource_def['schema']
    validator = app.validator(schema, resource)

    payload = payload_()
    if len(payload) > 1:
        abort(400, description=debug_error_message(
            'Only one update-per-document supported'))

    original = get_document(resource, **lookup)
    if not original:
        # not found
        abort(404)

    last_modified = None
    etag = None
    issues = []
    object_id = original[config.ID_FIELD]

    # TODO the list is needed for Py33. Find a less ridiculous alternative?
    key = list(payload.keys())[0]
    document = payload[key]

    response_item = {}

    try:
        document = parse(document, resource)
        validation = validator.validate_replace(document, object_id)
        if validation:
            last_modified = datetime.utcnow().replace(microsecond=0)
            document[config.ID_FIELD] = object_id
            document[config.LAST_UPDATED] = last_modified
            # TODO what do we need here: the original creation date or the
            # PUT date? Going for the former seems reasonable.
            document[config.DATE_CREATED] = original[config.DATE_CREATED]

            # if 'user-restricted resource access' is enabled and there's
            # an Auth request active, inject the username into the document
            auth_field = resource_def['auth_field']
            if auth_field:
                userid = app.auth.user_id
                if userid and request.authorization:
                    document[auth_field] = userid
            etag = document_etag(document)

            # notify callbacks
            getattr(app, "on_insert")(resource, [document])
            getattr(app, "on_insert_%s" % resource)([document])

            app.data.replace(resource, object_id, document)

            response_item[config.ID_FIELD] = object_id
            response_item[config.LAST_UPDATED] = last_modified

            # metadata
            response_item['etag'] = etag
            if resource_def['hateoas']:
                response_item['_links'] = {'self': document_link(resource,
                                                                 object_id)}
        else:
            issues.extend(validator.errors)
    except ValidationError as e:
        # TODO should probably log the error and abort 400 instead (when we
        # got logging)
        issues.append(str(e))
    except exceptions.InternalServerError as e:
        raise e
    except Exception as e:
        # consider all other exceptions as Bad Requests
        abort(400, description=debug_error_message(
            'An exception occurred: %s' % e
        ))

    if len(issues):
        response_item['issues'] = issues
        response_item['status'] = config.STATUS_ERR
    else:
        response_item['status'] = config.STATUS_OK

    response = {}
    response[key] = response_item
    return response, last_modified, etag, 200
