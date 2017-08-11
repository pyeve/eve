# -*- coding: utf-8 -*-

"""
    eve.methods.delete
    ~~~~~~~~~~~~~~~~~~

    This module implements the DELETE method.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app as app, abort
from eve.utils import config, ParsedRequest
from eve.auth import requires_auth
from eve.methods.common import get_document, ratelimit, pre_event, \
    oplog_push, resolve_document_etag
from eve.versioning import versioned_id_field, resolve_document_version, \
    insert_versioning_documents, late_versioning_catch
from datetime import datetime
import copy


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


def deleteitem_internal(resource, concurrency_check=False,
                        suppress_callbacks=False, original=None, **lookup):
    """ Intended for internal delete calls, this method is not rate limited,
    authentication is not checked, pre-request events are not raised, and
    concurrency checking is optional. Deletes a resource item.

    :param resource: name of the resource to which the item(s) belong.
    :param concurrency_check: concurrency check switch (bool)
    :param original: original document if already fetched from the database
    :param **lookup: item lookup query.

    .. versionchanged:: 0.6
       Support for soft delete.

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
    resource_def = config.DOMAIN[resource]
    soft_delete_enabled = resource_def['soft_delete']
    original = get_document(resource, concurrency_check, original, **lookup)
    if not original or (soft_delete_enabled and
                        original.get(config.DELETED) is True):
        abort(404)

    # notify callbacks
    if suppress_callbacks is not True:
        getattr(app, "on_delete_item")(resource, original)
        getattr(app, "on_delete_item_%s" % resource)(original)

    if soft_delete_enabled:
        # Instead of removing the document from the db, just mark it as deleted
        marked_document = copy.deepcopy(original)

        # Set DELETED flag and update metadata
        last_modified = datetime.utcnow().replace(microsecond=0)
        marked_document[config.DELETED] = True
        marked_document[config.LAST_UPDATED] = last_modified

        if config.IF_MATCH:
            resolve_document_etag(marked_document, resource)

        resolve_document_version(marked_document, resource, 'DELETE', original)

        # Update document in database (including version collection if needed)
        id = original[resource_def['id_field']]
        try:
            app.data.replace(resource, id, marked_document, original)
        except app.data.OriginalChangedError:
            if concurrency_check:
                abort(412, description='Client and server etags don\'t match')

        # create previous version if it wasn't already there
        late_versioning_catch(original, resource)
        # and add deleted version
        insert_versioning_documents(resource, marked_document)
        # update oplog if needed
        oplog_push(resource, marked_document, 'DELETE', id)

    else:
        # Delete the document for real

        # media cleanup
        media_fields = app.config['DOMAIN'][resource]['_media']

        # document might miss one or more media fields because of datasource
        # and/or client projection.
        missing_media_fields = [f for f in media_fields if f not in original]
        if len(missing_media_fields):
            # retrieve the whole document so we have all media fields available
            # Should be very a rare occurrence. We can't get rid of the
            # get_document() call since it also deals with etag matching, which
            # is still needed. Also, this lookup should never fail.
            # TODO not happy with this hack. Not at all. Is there a better way?
            original = app.data.find_one_raw(resource, **lookup)

        for field in media_fields:
            if field in original:
                media_field = original[field]
                if isinstance(media_field, list):
                    for file_id in media_field:
                        app.media.delete(file_id, resource)
                else:
                    app.media.delete(original[field], resource)

        id = original[resource_def['id_field']]
        app.data.remove(resource, lookup)

        # TODO: should attempt to delete version collection even if setting is
        # off
        if app.config['DOMAIN'][resource]['versioning'] is True:
            app.data.remove(
                resource + config.VERSIONS,
                {versioned_id_field(resource_def):
                 original[resource_def['id_field']]})

        # update oplog if needed
        oplog_push(resource, original, 'DELETE', id)

    if suppress_callbacks is not True:
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

    resource_def = config.DOMAIN[resource]
    getattr(app, "on_delete_resource")(resource)
    getattr(app, "on_delete_resource_%s" % resource)()
    default_request = ParsedRequest()
    if resource_def['soft_delete']:
        # get_document should always fetch soft deleted documents from the db
        # callers must handle soft deleted documents
        default_request.show_deleted = True
    originals = list(app.data.find(resource, default_request, lookup))
    if not originals:
        abort(404)
    # I add new callback as I want the framework to be retro-compatible
    getattr(app, "on_delete_resource_originals")(resource,
                                                 originals,
                                                 lookup)
    getattr(app, "on_delete_resource_originals_%s" % resource)(originals,
                                                               lookup)
    id_field = resource_def['id_field']

    if resource_def['soft_delete']:
        # I need to check that I have at least some documents not soft_deleted
        # Otherwise, I should abort 404
        # I skip all the soft_deleted documents
        originals = [x for x in originals if x.get(config.DELETED) is not True]
        if not originals:
            # Nothing to be deleted
            abort(404)
        for document in originals:
            lookup[id_field] = document[id_field]
            deleteitem_internal(resource, concurrency_check=False,
                                suppress_callbacks=True,
                                original=document, **lookup)
    else:
        # TODO if the resource schema includes media files, these won't be
        # deleted by use of this global method (it should be disabled). Media
        # cleanup is handled at the item endpoint by the delete() method
        # (see above).
        app.data.remove(resource, lookup)

        # TODO: should attempt to delete version collection even if setting is
        # off
        if resource_def['versioning'] is True:
            app.data.remove(resource + config.VERSIONS, lookup)

    getattr(app, "on_deleted_resource")(resource)
    getattr(app, "on_deleted_resource_%s" % resource)()

    return {}, None, None, 204
