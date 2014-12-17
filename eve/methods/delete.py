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
from eve.methods.common import get_document, ratelimit, pre_event, oplog_push
from eve.versioning import versioned_id_field


@ratelimit()
@requires_auth('item')
@pre_event
def deleteitem(resource, **lookup):
    """
    Default function for handling DELETE requests, it has decorators for
    rate limiting, authentication and for raising pre-request events.
    After the decorators are applied forwards to call to
    :func:`deleteitem_internal`

    .. versionchanged:: 0.5
       Split into deleteitem() and deleteitem_internal().
    """
    return deleteitem_internal(resource, concurrency_check=True, **lookup)


def deleteitem_internal(resource, concurrency_check=False, **lookup):
    """ Intended for internal delete calls, this method is not rate limited,
    authentication is not checked, pre-request events are not raised, and
    concurrency checking is optional. Deletes a resource item.

    :param resource: name of the resource to which the item(s) belong.
    :param concurrency_check: concurrency check switch (bool)
    :param **lookup: item lookup query.

    .. versionchanged:: 0.5
       Return 204 NoContent instead of 200.
       Push updates to OpLog.
       Original deleteitem() has been split into deleteitem() and
       deleteitem_internal().

    .. versionchanged:: 0.4
       Fix #284: If you have a media field, and set datasource projection to
       0 for that field, the media will not be deleted.
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
    original = get_document(resource, concurrency_check, **lookup)
    if not original:
        abort(404)

    # notify callbacks
    getattr(app, "on_delete_item")(resource, original)
    getattr(app, "on_delete_item_%s" % resource)(original)

    # media cleanup
    media_fields = app.config['DOMAIN'][resource]['_media']

    # document might miss one or more media fields because of datasource and/or
    # client projection.
    missing_media_fields = [f for f in media_fields if f not in original]
    if len(missing_media_fields):
        # retrieve the whole document so we have all media fields available.
        # Should be very a rare occurence. We can't get rid of the
        # get_document() call since it also deals with etag matching, which is
        # still needed. Also, this lookup should never fail.
        # TODO not happy with this hack. Not at all. Is there a better way?
        original = app.data.find_one_raw(resource, original[config.ID_FIELD])

    for field in media_fields:
        if field in original:
            app.media.delete(original[field])

    id = original[config.ID_FIELD]
    app.data.remove(resource, {config.ID_FIELD: id})

    # update oplog if needed
    oplog_push(resource, original, 'DELETE', id)

    # TODO: should attempt to delete version collection even if setting is off
    if app.config['DOMAIN'][resource]['versioning'] is True:
        app.data.remove(
            resource + config.VERSIONS,
            {versioned_id_field(): original[config.ID_FIELD]})

    getattr(app, "on_deleted_item")(resource, original)
    getattr(app, "on_deleted_item_%s" % resource)(original)

    return {}, None, None, 204


@requires_auth('resource')
@pre_event
def delete(resource, **lookup):
    """ Deletes all item of a resource (collection in MongoDB terms). Won't
    drop indexes. Use with caution!

    .. versionchanged:: 0.5
       Return 204 NoContent instead of 200.

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
    # by use of this global method (it should be disabled). Media cleanup is
    # handled at the item endpoint by the delete() method (see above).
    app.data.remove(resource, lookup)

    # TODO: should attempt to delete version collection even if setting is off
    if app.config['DOMAIN'][resource]['versioning'] is True:
        app.data.remove(resource + config.VERSIONS, lookup)

    getattr(app, "on_deleted_resource")(resource)
    getattr(app, "on_deleted_resource_%s" % resource)()

    return {}, None, None, 204
