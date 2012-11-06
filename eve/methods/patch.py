from flask import current_app as app
from datetime import datetime
from eve import LAST_UPDATED, ID_FIELD, STATUS_ERR, STATUS_OK
from eve.utils import document_etag, document_link
from eve.validation import ValidationError
from common import get_document, parse
from flask import abort, request


def patch(resource, **lookup):
    if len(request.form) > 1 or len(request.form) == 0:
        abort(400)

    original = get_document(resource, **lookup)
    if not original:
        abort(404)

    schema = app.config['DOMAIN'][resource]['schema']
    validator = app.validator(schema, resource)

    object_id = original[ID_FIELD]
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
            updates[LAST_UPDATED] = datetime.utcnow()
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
            updated = app.data.find_one(resource, **{ID_FIELD: object_id})
            updated[LAST_UPDATED] = updated[LAST_UPDATED].replace(tzinfo=None)
            etag = document_etag(updated)

            response_item[ID_FIELD] = object_id
            last_modified = response_item[LAST_UPDATED] = updated[LAST_UPDATED]
            response_item['etag'] = etag
            response_item['link'] = document_link(resource, object_id)
        else:
            issues.append(validator.errors)
    except ValidationError, e:
        # TODO should probably log the error and abort 400 instead (when we
        # got logging)
        issues.append(str(e))
    except Exception, e:
        abort(400)

    if len(issues):
        response_item['issues'] = issues
        response_item['status'] = STATUS_ERR
    else:
        response_item['status'] = STATUS_OK

    response = dict()
    response[key] = response_item
    return response, last_modified, etag, 200
