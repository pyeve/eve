# -*- coding: utf-8 -*-

"""
    eve.methods.delete
    ~~~~~~~~~~~~~~~~~~

    This module imlements the DELETE method.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app as app, abort
from eve.utils import config
from eve.auth import requires_auth
from eve.methods.common import get_document, ratelimit, pre_event, \
    resource_media_fields
from eve.versioning import versioned_id_field


@ratelimit()
@requires_auth('item')
@pre_event
def delete(resource, **lookup):
    """ Deletes a resource item. Deletion will occur only if request ETag
    matches the current representation of the item.

    :param resource: name of the resource to which the item(s) belong.
    :param **lookup: item lookup query.

    .. versionchanged:: 0.4
       Support for document versioning.
       'on_delete_item' events raised before performing the delete.
       'on_deleted_item' events raised after performing the delete.

    .. versionchanged:: 0.3
       Delete media files as needed.
       Pass the explicit query filter to the data driver, as it does not
       support the id argument anymore.

    .. versionchanged:: 0.2
       Raise pre_<method> event.

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

    # notify callbacks
    getattr(app, "on_delete_item")(resource, original)
    getattr(app, "on_delete_item_%s" % resource)(original)

    app.data.remove(resource, {config.ID_FIELD: original[config.ID_FIELD]})
    # TODO: should attempt to delete version collection even if setting is off
    if app.config['DOMAIN'][resource]['versioning'] is True:
        app.data.remove(
            resource + config.VERSIONS,
            {versioned_id_field(): original[config.ID_FIELD]})

    # media cleanup
    media_fields = resource_media_fields(original, resource)
    for field in media_fields:
        app.media.delete(original[field])

    getattr(app, "on_deleted_item")(resource, original)
    getattr(app, "on_deleted_item_%s" % resource)(original)

    return {}, None, None, 200


@requires_auth('resource')
@pre_event
def delete_resource(resource, lookup):
    """ Deletes all item of a resource (collection in MongoDB terms). Won't
    drop indexes. Use with caution!

    .. versionchanged:: 0.4
       Support for document versioning.
       'on_delete_resource' raised before performing the actual delete.
       'on_deleted_resource' raised after performing the delete

    .. versionchanged:: 0.3
       Support for the lookup filter, which allows for develtion of
       sub-resources (only delete documents that match a given condition).

    .. versionchanged:: 0.0.4
       Added the ``requires_auth`` decorator.

    .. versionadded:: 0.0.2
    """
    getattr(app, "on_delete_resource")(resource)
    getattr(app, "on_delete_resource_%s" % resource)()

    # TODO if the resource schema includes media files, these won't be deleted
    # by use of this global method (if should be disabled). Media cleanup is
    # handled at the item endpoint by the delete() method (see above).
    app.data.remove(resource, lookup)

    # TODO: should attempt to delete version collection even if setting is off
    if app.config['DOMAIN'][resource]['versioning'] is True:
        app.data.remove(resource + config.VERSIONS, lookup)

    getattr(app, "on_deleted_resource")(resource)
    getattr(app, "on_deleted_resource_%s" % resource)()

    return {}, None, None, 200
