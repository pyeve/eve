# -*- coding: utf-8 -*-

"""
    eve.methods.patch
    ~~~~~~~~~~~~~~~~~

    This module imlements the PATCH method, supported by the resources
    endopints.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app as app
from datetime import datetime
from common import get_document, parse
from flask import abort, request
from eve.utils import document_etag, document_link, config
from eve.validation import ValidationError


def patch(resource, **lookup):
    """Perform a document patch/update. Updates are first validated against
    the resource schema. If validation passes, the document is updated and
    an OK status update is returned. If validation fails, a set of validation
    issues is returned.

    :param resource: the name of the resource to which the document belongs.
    :param **lookup: document lookup query.

    .. versionchanged:: 0.0.3
       JSON links. Superflous ``response`` container removed.
    """
    if len(request.form) > 1 or len(request.form) == 0:
        # only one update-per-document supported
        abort(400)

    original = get_document(resource, **lookup)
    if not original:
        # not found
        abort(404)

    schema = app.config['DOMAIN'][resource]['schema']
    validator = app.validator(schema, resource)

    object_id = original[config.ID_FIELD]
    last_modified = None
    etag = None

    issues = list()

    key = request.form.keys()[0]
    value = request.form[key]

    response_item = dict()

    try:
        updates = parse(value, resource)
        validation = validator.validate_update(updates, object_id)
        if validation:
            updates[config.LAST_UPDATED] = datetime.utcnow()
            app.data.update(resource, object_id, updates)

            # TODO computing etag without reloading the document
            # would be ideal. However, for reasons that need fruther
            # investigation, an etag computed on original.update(updates)
            # won't provide the same result as the saved document.
            # this has probably comething to do with a) the different
            # precision between the BSON (milliseconds) python datetime and,
            # b), the string representation of the documents (being dicts)
            # not matching.
            #
            # TL;DR: find a way to compute a reliable etag without reloading
            updated = app.data.find_one(resource,
                                        **{config.ID_FIELD: object_id})
            updated[config.LAST_UPDATED] = \
                updated[config.LAST_UPDATED].replace(tzinfo=None)
            etag = document_etag(updated)

            response_item[config.ID_FIELD] = object_id
            last_modified = response_item[config.LAST_UPDATED] = \
                updated[config.LAST_UPDATED]

            # metadata
            response_item['etag'] = etag
            response_item['_links'] = {'self': document_link(resource,
                                                             object_id)}
        else:
            issues.extend(validator.errors)
    except ValidationError, e:
        # TODO should probably log the error and abort 400 instead (when we
        # got logging)
        issues.append(str(e))
    except Exception, e:
        abort(400)

    if len(issues):
        response_item['issues'] = issues
        response_item['status'] = config.STATUS_ERR
    else:
        response_item['status'] = config.STATUS_OK

    response = dict()
    response[key] = response_item
    return response, last_modified, etag, 200
