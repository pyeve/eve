# -*- coding: utf-8 -*-

"""
    eve.methods.patch
    ~~~~~~~~~~~~~~~~~

    This module imlements the PATCH method.

    :copyright: (c) 2013 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app as app, abort
from werkzeug import exceptions
from datetime import datetime
from eve.utils import document_etag, document_link, config, debug_error_message
from eve.auth import requires_auth
from eve.validation import ValidationError
from eve.methods.common import get_document, parse, payload as payload_, \
    ratelimit


@ratelimit()
@requires_auth('item')
def patch(resource, **lookup):
    """Perform a document patch/update. Updates are first validated against
    the resource schema. If validation passes, the document is updated and
    an OK status update is returned. If validation fails, a set of validation
    issues is returned.

    :param resource: the name of the resource to which the document belongs.
    :param **lookup: document lookup query.

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.
       Re-raises `exceptions.Unauthorized`, this could occur if the
       `auth_field` condition fails

    .. versionchanged:: 0.0.9
       More informative error messages.
       Support for Python 3.3.

    .. versionchanged:: 0.0.8
       Let ``werkzeug.exceptions.InternalServerError`` go through as they have
       probably been explicitly raised by the data driver.

    .. versionchanged:: 0.0.7
       Support for Rate-Limiting.

    .. versionchanged:: 0.0.6
       ETag is now computed without the need of an additional db lookup

    .. versionchanged:: 0.0.5
       Support for 'aplication/json' Content-Type.

    .. versionchanged:: 0.0.4
       Added the ``requires_auth`` decorator.

    .. versionchanged:: 0.0.3
       JSON links. Superflous ``response`` container removed.
    """
    payload = payload_()
    if len(payload) > 1:
        # only one update-per-document supported
        abort(400, description=debug_error_message(
            'Only one update-per-document supported'
        ))

    original = get_document(resource, **lookup)
    if not original:
        # not found
        abort(404)

    resource_def = app.config['DOMAIN'][resource]
    schema = resource_def['schema']
    validator = app.validator(schema, resource)

    object_id = original[config.ID_FIELD]
    last_modified = None
    etag = None

    issues = []

    # TODO the list is needed for Py33. Find a less ridiculous alternative?
    key = list(payload.keys())[0]
    value = payload[key]

    response_item = {}

    try:
        updates = parse(value, resource)
        validation = validator.validate_update(updates, object_id)
        if validation:
            # the mongo driver has a different precision than the python
            # datetime. since we don't want to reload the document once it has
            # been updated, and we still have to provide an updated etag,
            # we're going to update the local version of the 'original'
            # document, and we will use it for the etag computation.
            original.update(updates)
            # some datetime precision magic
            updates[config.LAST_UPDATED] = original[config.LAST_UPDATED] = \
                datetime.utcnow().replace(microsecond=0)
            etag = document_etag(original)

            app.data.update(resource, object_id, updates)
            response_item[config.ID_FIELD] = object_id
            last_modified = response_item[config.LAST_UPDATED] = \
                original[config.LAST_UPDATED]

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
    except (exceptions.InternalServerError, exceptions.Unauthorized) as e:
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
