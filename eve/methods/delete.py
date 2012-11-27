# -*- coding: utf-8 -*-

"""
    eve.methods.delete
    ~~~~~~~~~~~~~~~~~~

    This module imlements the DELETE method, currently supported by the item
    endopints.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app as app
from common import get_document
from flask import abort
from eve.utils import config


def delete(resource, **lookup):
    """Deletes a resource item. Deletion will occur only if request ETag
    matches the current representation of the item.

    :param resource: name of the resource to which the item(s) belong.
    :param **lookup: item lookup query.
    """
    original = get_document(resource, **lookup)
    if not original:
        abort(404)

    app.data.remove(resource, lookup[config.ID_FIELD])
    return dict(), None, None, 200


def delete_resource(resource):
    """Deletes all item of a resource (collection in MongoDB terms). Won't drop
    indexes. Use with caution!

    .. versionadded:: 0.0.2
    """
    app.data.remove(resource)
    return dict(), None, None, 200
