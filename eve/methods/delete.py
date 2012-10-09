from flask import current_app as app
from eve import ID_FIELD
from common import get_document
from flask import abort


def delete(resource, **lookup):
    original = get_document(resource, **lookup)
    if not original:
        abort(404)

    app.data.remove(resource, lookup[ID_FIELD])
    return dict(), None, None, 200
