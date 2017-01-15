# -*- coding: utf-8 -*-

"""
    eve.methods.post
    ~~~~~~~~~~~~~~~~

    This module imlements the POST method, supported by the resources
    endopints.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime
from flask import current_app as app, abort
from eve.utils import config, parse_request, debug_error_message
from eve.auth import requires_auth
from eve.defaults import resolve_default_values
from eve.validation import ValidationError
from eve.methods.common import parse, payload, ratelimit, \
    pre_event, store_media_files, resolve_user_restricted_access, \
    resolve_embedded_fields, build_response_document, marshal_write_response, \
    resolve_sub_resource_path, resolve_document_etag, oplog_push, resource_link
from eve.versioning import resolve_document_version, \
    insert_versioning_documents


@ratelimit()
@requires_auth('resource')
@pre_event
def post(resource, payl=None):
    """
    Default function for handling POST requests, it has decorators for
    rate limiting, authentication and for raising pre-request events. After the
    decorators are applied forwards to call to :func:`post_internal`

    .. versionchanged:: 0.5
       Split original post() into post/post_internal combo.
    """
    return post_internal(resource, payl, skip_validation=False)


def post_internal(resource, payl=None, skip_validation=False):
    """
    Intended for internal post calls, this method is not rate limited,
    authentication is not checked and pre-request events are not raised.
    Adds one or more documents to a resource. Each document is validated
    against the domain schema. If validation passes the document is inserted
    and ID_FIELD, LAST_UPDATED and DATE_CREATED along with a link to the
    document are returned. If validation fails, a list of validation issues
    is returned.

    :param resource: name of the resource involved.
    :param payl: alternative payload. When calling post() from your own code
                 you can provide an alternative payload. This can be useful,
                 for example, when you have a callback function hooked to a
                 certain endpoint, and want to perform additional post() calls
                 from there.

                 Please be advised that in order to successfully use this
                 option, a request context must be available.

                 See https://github.com/nicolaiarocci/eve/issues/74 for a
                 discussion, and a typical use case.
    :param skip_validation: skip payload validation before write (bool)

    .. versionchanged:: 0.7
       Add support for Location header. Closes #795.

    .. versionchanged:: 0.6
       Fix: since v0.6, skip_validation = True causes a 422 response (#726).

    .. versionchanged:: 0.6
       Initialize DELETED field when soft_delete is enabled.

    .. versionchanged:: 0.5
       Back to resolving default values after validaton as now the validator
       can properly validate dependency even when some have default values. See
       #353.
       Push updates to the OpLog.
       Original post() has been split into post() and post_internal().
       ETAGS are now stored with documents (#369).

    .. versionchanged:: 0.4
       Resolve default values before validation is performed. See #353.
       Support for document versioning.

    .. versionchanged:: 0.3
       Return 201 if at least one document has been successfully inserted.
       Fix #231 auth field not set if resource level authentication is set.
       Support for media fields.
       When IF_MATCH is disabled, no etag is included in the payload.
       Support for new validation format introduced with Cerberus v0.5.

    .. versionchanged:: 0.2
       Use the new STATUS setting.
       Use the new ISSUES setting.
       Raise 'on_pre_<method>' event.
       Explictly resolve default values instead of letting them be resolved
       by common.parse. This avoids a validation error when a read-only field
       also has a default value.
       Added ``on_inserted*`` events after the database insert

    .. versionchanged:: 0.1.1
       auth.request_auth_value is now used to store the auth_field value.

    .. versionchanged:: 0.1.0
       More robust handling of auth_field.
       Support for optional HATEOAS.

    .. versionchanged: 0.0.9
       Event hooks renamed to be more robuts and consistent: 'on_posting'
       renamed to 'on_insert'.
       You can now pass a pre-defined custom payload to the funcion.

    .. versionchanged:: 0.0.9
       Storing self.app.auth.userid in auth_field when 'user-restricted
       resource access' is enabled.

    .. versionchanged: 0.0.7
       Support for Rate-Limiting.
       Support for 'extra_response_fields'.

       'on_posting' and 'on_posting_<resource>' events are raised before the
       documents are inserted into the database. This allows callback functions
       to arbitrarily edit/update the documents being stored.

    .. versionchanged:: 0.0.6
       Support for bulk inserts.

       Please note: validation constraints are checked against the database,
       and not between the payload documents themselves. This causes an
       interesting corner case: in the event of a multiple documents payload
       where two or more documents carry the same value for a field where the
       'unique' constraint is set, the payload will validate successfully, as
       there are no duplicates in the database (yet). If this is an issue, the
       client can always send the documents once at a time for insertion, or
       validate locally before submitting the payload to the API.

    .. versionchanged:: 0.0.5
       Support for 'application/json' Content-Type .
       Support for 'user-restricted resource access'.

    .. versionchanged:: 0.0.4
       Added the ``requires_auth`` decorator.

    .. versionchanged:: 0.0.3
       JSON links. Superflous ``response`` container removed.
    """

    date_utc = datetime.utcnow().replace(microsecond=0)
    resource_def = app.config['DOMAIN'][resource]
    schema = resource_def['schema']
    validator = None if skip_validation else app.validator(schema, resource)
    documents = []
    results = []
    failures = 0
    id_field = resource_def['id_field']

    if config.BANDWIDTH_SAVER is True:
        embedded_fields = []
    else:
        req = parse_request(resource)
        embedded_fields = resolve_embedded_fields(resource, req)

    # validation, and additional fields
    if payl is None:
        payl = payload()

    if isinstance(payl, dict):
        payl = [payl]

    if not payl:
        # empty bulkd insert
        abort(400, description=debug_error_message(
            'Empty bulk insert'
        ))

    if len(payl) > 1 and not config.DOMAIN[resource]['bulk_enabled']:
        abort(400, description=debug_error_message(
            'Bulk insert not allowed'
        ))

    for value in payl:
        document = []
        doc_issues = {}
        try:
            document = parse(value, resource)
            resolve_sub_resource_path(document, resource)
            if skip_validation:
                validation = True
            else:
                validation = validator.validate(document)
            if validation:  # validation is successful
                # validator might be not available if skip_validation. #726.
                if validator:
                    # Apply coerced values
                    document = validator.document

                # Populate meta and default fields
                document[config.LAST_UPDATED] = \
                    document[config.DATE_CREATED] = date_utc

                if config.DOMAIN[resource]['soft_delete'] is True:
                    document[config.DELETED] = False

                resolve_user_restricted_access(document, resource)
                resolve_default_values(document, resource_def['defaults'])
                store_media_files(document, resource)
                resolve_document_version(document, resource, 'POST')
            else:
                # validation errors added to list of document issues
                doc_issues = validator.errors
        except ValidationError as e:
            doc_issues['validation exception'] = str(e)
        except Exception as e:
            # most likely a problem with the incoming payload, report back to
            # the client as if it was a validation issue
            app.logger.exception(e)
            doc_issues['exception'] = str(e)

        if len(doc_issues):
            document = {
                config.STATUS: config.STATUS_ERR,
                config.ISSUES: doc_issues,
            }
            failures += 1

        documents.append(document)

    if failures:
        # If at least one document got issues, the whole request fails and a
        # ``422 Bad Request`` status is return.
        for document in documents:
            if config.STATUS in document \
               and document[config.STATUS] == config.STATUS_ERR:
                results.append(document)
            else:
                results.append({config.STATUS: config.STATUS_OK})

        return_code = config.VALIDATION_ERROR_STATUS
    else:
        # notify callbacks
        getattr(app, "on_insert")(resource, documents)
        getattr(app, "on_insert_%s" % resource)(documents)

        # compute etags here as documents might have been updated by callbacks.
        resolve_document_etag(documents, resource)

        # bulk insert
        ids = app.data.insert(resource, documents)

        # update oplog if needed
        oplog_push(resource, documents, 'POST')

        # assign document ids
        for document in documents:
            # either return the custom ID_FIELD or the id returned by
            # data.insert().
            id_ = document.get(id_field, ids.pop(0))
            document[id_field] = id_

            # build the full response document
            result = document
            build_response_document(
                result, resource, embedded_fields, document)

            # add extra write meta data
            result[config.STATUS] = config.STATUS_OK

            # limit what actually gets sent to minimize bandwidth usage
            result = marshal_write_response(result, resource)
            results.append(result)

        # insert versioning docs
        insert_versioning_documents(resource, documents)

        # notify callbacks
        getattr(app, "on_inserted")(resource, documents)
        getattr(app, "on_inserted_%s" % resource)(documents)
        # request was received and accepted; at least one document passed
        # validation and was accepted for insertion.

        return_code = 201

    if len(results) == 1:
        response = results.pop(0)
    else:
        response = {
            config.STATUS: config.STATUS_ERR if failures else config.STATUS_OK,
            config.ITEMS: results,
        }

    if failures:
        response[config.ERROR] = {
            "code": return_code,
            "message": "Insertion failure: %d document(s) contain(s) error(s)"
            % failures,
        }

    location_header = None if return_code != 201 or not documents else \
        [('Location', '%s/%s' % (resource_link(), documents[0][id_field]))]

    return response, None, None, return_code, location_header
