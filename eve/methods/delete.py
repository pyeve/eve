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
from common import get_document, ratelimit
from flask import abort
from eve.utils import config
from eve.auth import requires_auth


@ratelimit()
@requires_auth('item')
def delete(resource, **lookup):
    """Deletes a resource item. Deletion will occur only if request ETag
    matches the current representation of the item.

    :param resource: name of the resource to which the item(s) belong.
    :param **lookup: item lookup query.

    .. versionchanged:: 0.0.7
       Support for Rate-Limiting.

    .. versionchanged:: 0.0.5
      Pass current resource to ``parse_request``, allowing for proper
      processing of new configuration settings: `filters`, `sorting`, `paging`.

    .. versionchanged:: 0.0.4
       Added the ``requires_auth`` decorator.
    """
    original = get_document(resource, **lookup)
    if not original:
        abort(404)

    app.data.remove(resource, lookup[config.ID_FIELD])
    return {}, None, None, 200


@requires_auth('resource')
def delete_resource(resource):
    """Deletes all item of a resource (collection in MongoDB terms). Won't drop
    indexes. Use with caution!

    .. versionchanged:: 0.0.4
       Added the ``requires_auth`` decorator.

    .. versionadded:: 0.0.2
    """
    app.data.remove(resource)
    return {}, None, None, 200
