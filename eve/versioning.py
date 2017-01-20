from flask import current_app as app, abort
from eve.utils import config, debug_error_message, ParsedRequest
from werkzeug.exceptions import BadRequestKeyError


def versioned_id_field(resource_settings):
    """ Shorthand to add two commonly added versioning parameters.

    .. versionadded: 0.4
    """
    return resource_settings['id_field'] + app.config['VERSION_ID_SUFFIX']


def resolve_document_version(document, resource, method, latest_doc=None):
    """ Version number logic for all methods.

    :param document: the document in question.
    :param resource: the resource of the request/document.
    :param method: method coorsponding to the request.
    :param latest_doc: the most recent version of the document.

    .. versionadded:: 0.4
    """
    resource_def = app.config['DOMAIN'][resource]
    version = app.config['VERSION']
    latest_version = app.config['LATEST_VERSION']

    if resource_def['versioning'] is True:
        # especially on collection endpoints, we don't to encure an extra
        # lookup if we are already pulling the latest version
        if method == 'GET' and latest_doc is None:
            if version not in document:
                # well it should be... the api designer must have turned on
                # versioning after data was already in the collection or the
                # collection has been modified without respecting versioning
                document[version] = 1  # the first saved version will be 2
            document[latest_version] = document[version]

        # include latest_doc if the request is for an older version so that we
        # can set the latest_version field in the response
        if method == 'GET' and latest_doc is not None:
            if version not in latest_doc:
                # well it should be... the api designer must have turned on
                # versioning after data was already in the collection or the
                # collection has been modified without respecting versioning
                document[version] = 1  # the first saved version will be 2
                document[latest_version] = document[version]
            else:
                document[latest_version] = latest_doc[version]
                if version not in document:
                    # this version was put in the database before versioning
                    # was turned on or outside of Eve
                    document[version] = 1

        if method == 'POST':
            # this one is easy! it is a new document
            document[version] = 1

        if method == 'PUT' or method == 'PATCH' or \
                (method == 'DELETE' and resource_def['soft_delete'] is True):
            if not latest_doc:
                abort(500, description=debug_error_message(
                    'I need the latest document here!'
                ))
            if version in latest_doc:
                # all is right in the world :)
                document[version] = latest_doc[version] + 1
            else:
                # if versioning was just turned on, then we will start
                # versioning now. if the db was modified outside of Eve or
                # versioning was turned of for a while, version numbers will
                # not be consistent! you have been warned
                document[version] = 1


def late_versioning_catch(document, resource):
    """ Insert versioning copy of document for the previous version of a
    document if it is missing. Intended for PUT and PATCH.

    :param resource: the resource of the request/document.
    :param ids: a list of id number coorsponding to the documents parameter.
    :param document: the documents be written by POST, PUT, or PATCH.

    .. versionadded:: 0.4
    """
    resource_def = app.config['DOMAIN'][resource]
    version = app.config['VERSION']

    if resource_def['versioning'] is True:
        # TODO: Could directly check that there are no shadow copies for this
        # document. If there are shadow copies but the version field is in the
        # stored document, then something is wrong. (Modified outside of Eve?)

        if version not in document:
            # The API maintainer must of turned on versioning after the
            # document was added to the database, so let's add this old version
            # to the shadow collection now as if it was a new document.
            resolve_document_version(document, resource, 'POST')
            insert_versioning_documents(resource, document)


def insert_versioning_documents(resource, documents):
    """ Insert versioning copy of document. Intended for POST, PUT, and PATCH.

    :param resource: the resource of the request/document.
    :param documents: the documents be written by POST, PUT, or PATCH.

    .. versionadded:: 0.4
    """
    resource_def = app.config['DOMAIN'][resource]
    _id = resource_def['id_field']

    # push back versioned items if applicable
    # note: MongoDB doesn't have transactions! if the server dies, no
    # history will be saved.
    if resource_def['versioning'] is True:
        # force input as lists
        if not isinstance(documents, list):
            documents = [documents]

        # if 'user-restricted resource access' is enabled and there's
        # an Auth request active, inject the username into the document
        request_auth_value = None
        auth = resource_def['authentication']
        auth_field = resource_def['auth_field']
        if auth and auth_field:
            request_auth_value = auth.get_request_auth_value()

        # build vesioning documents
        version = app.config['VERSION']
        versioned_documents = []
        for index, document in enumerate(documents):
            ver_doc = {}

            # push normal fields
            fields = versioned_fields(resource_def)
            for field in document:
                if field in fields:
                    ver_doc[field] = document[field]

            # push special fields
            ver_doc[versioned_id_field(resource_def)] = document[_id]
            ver_doc[version] = document[version]

            # push auth_field
            if request_auth_value:
                ver_doc[auth_field] = request_auth_value

            # add document to the stack
            versioned_documents.append(ver_doc)

        # bulk insert
        source = resource_def['datasource']['source']
        versionable_resource_name = source + app.config['VERSIONS']
        app.data.insert(versionable_resource_name, versioned_documents)


def versioned_fields(resource_def):
    """ Returns a list of versioned fields for a resource.

    :param resource_def: a resource definition.

    .. versionchanged:: 0.6
       Added DELETED as versioned field for soft delete (#335)

    .. versionchanged:: 0.5
       ETAG is now a versioned field (#369).

    .. versionadded:: 0.4
    """
    if resource_def['versioning'] is not True:
        return []

    schema = resource_def['schema']

    fields = [f for f in schema
              if schema[f].get('versioned', True) is True and
              f != resource_def['id_field']]

    fields.extend((app.config['LAST_UPDATED'],
                   app.config['ETAG'],
                   app.config['DELETED'],
                   ))

    return fields


def diff_document(resource_def, old_doc, new_doc):
    """ Returns a list of added or modified fields.

    :param resource_def: a resource definition.
    :param old_doc: the document to compare against.
    :param new_doc: the document in question.

    .. versionadded:: 0.4
    """
    diff = {}
    fields = list(resource_def['schema'].keys()) + [
        app.config['VERSION'],
        app.config['LATEST_VERSION'],
        resource_def['id_field'],
        app.config['LAST_UPDATED'],
        app.config['DATE_CREATED'],
        app.config['ETAG'],
        app.config['LINKS']]
    if resource_def['soft_delete'] is True:
        fields.append(app.config['DELETED'])

    for field in fields:
        if field in new_doc and \
                (field not in old_doc or new_doc[field] != old_doc[field]):
            diff[field] = new_doc[field]

    # This method does not show when fields are deleted.

    for field in app.config['VERSION_DIFF_INCLUDE']:
        if field in new_doc:
            diff[field] = new_doc[field]

    return diff


def synthesize_versioned_document(document, delta, resource_def):
    """ Synthesizes a versioned document from the latest document and the
    values of all versioned fields from the old version. This is accomplished
    by first creating a new document with only the un-versioned fields of
    latest document, before updating with versioned fields from the old
    document.

    :param document: the current version of a document.
    :param delta: the versioned fields from a specific document version.
    :param resource_def: a resource definition.

    .. versionchanged:: 0.6.1
       Use shallow copies instead of deepcopies to optimize for performance.
       #732.

    .. versionadded:: 0.4
    """
    versioned_doc = {}
    id_field = versioned_id_field(resource_def)

    if id_field not in delta:
        abort(400, description=debug_error_message(
            'You must include %s in any projection with a version query.'
            % id_field
        ))
    delta[resource_def['id_field']] = delta[id_field]
    del delta[id_field]

    # add unversioned fields from latest document to versioned_doc
    fields = versioned_fields(resource_def)
    for field in document:
        if field not in fields:
            versioned_doc[field] = document[field]

    # add versioned fields
    versioned_doc.update(delta)

    return versioned_doc


def get_old_document(resource, req, lookup, document, version):
    """ Returns an old document if appropriate, otherwise returns a shallow
    copy of the given document.

    :param resource: the name of the resource.
    :param req: the parsed request object.
    :param lookup: a dictionary of lookup parameters.
    :param document: the current version of the document.
    :param version: the value of the version request parameter.

    .. versionchanged:: 0.6.1
       Use shallow copies instead of deepcopies to optimize for performance.
       #732.

    .. versionadded:: 0.4
    """
    if version != 'all' and version != 'diffs' and version is not None:
        try:
            version = int(version)
            assert version > 0
        except (ValueError, BadRequestKeyError, AssertionError):
            abort(400, description=debug_error_message(
                'Document version number should be an int greater than 0'
            ))

        # parameters to find specific document version
        resource_def = config.DOMAIN[resource]
        if versioned_id_field(resource_def) not in lookup:
            lookup[versioned_id_field(resource_def)] \
                = lookup[resource_def['id_field']]
            del lookup[resource_def['id_field']]
        lookup[config.VERSION] = version

        # synthesize old document from latest and delta
        delta = app.data.find_one(resource + config.VERSIONS, req, **lookup)
        if not delta:
            abort(404)
        old_document = synthesize_versioned_document(
            document, delta, resource_def)
    else:
        # perform a shallow copy to allow this document to be used as a delta
        # for synthesize_versioned_document where id_field is removed
        old_document = document.copy()

    return old_document


def get_data_version_relation_document(data_relation, reference, latest=False):
    """ Returns document at the version specified in data_relation, or at the
    latest version if passed `latest=True`. Returns None if data_relation
    cannot be satisfied.

    :param data_relation: the schema definition describing the data_relation.
    :param reference: a dictionary with a value_field and a version_field.
    :param latest: if we should obey the version param in reference or not.

    .. versionadded:: 0.4
    """
    value_field = data_relation['field']
    version_field = app.config['VERSION']
    collection = data_relation['resource']
    versioned_collection = collection + config.VERSIONS
    resource_def = app.config['DOMAIN'][data_relation['resource']]
    id_field = resource_def['id_field']

    # Fetch document data at the referenced version
    query = {version_field: reference[version_field]}
    if value_field == id_field:
        # Versioned documents store the primary id in a different field
        query[versioned_id_field(resource_def)] = reference[value_field]
    elif value_field not in versioned_fields(resource_def):
        # The relation value field is unversioned, and will not be present in
        # the versioned collection. Need to find id field for version query
        req = ParsedRequest()
        if resource_def['soft_delete']:
            req.show_deleted = True
        latest_version = app.data.find_one(
            collection, req, **{value_field: reference[value_field]})
        if not latest_version:
            return None
        query[versioned_id_field(resource_def)] = latest_version[id_field]
    else:
        # Field will be present in the versioned collection
        query[value_field] = reference[value_field]

    referenced_version = app.data.find_one(versioned_collection, None, **query)

    # support late versioning
    if referenced_version is None and reference[version_field] == 1:
        # there is a chance this document hasn't been saved
        # since versioning was turned on
        referenced_version = missing_version_field(data_relation, reference)
        return referenced_version  # v1 is both referenced and latest

    if referenced_version is None:
        return None  # The referenced document version was not found

    # Fetch the latest version of this document to use in version synthesis
    query = {id_field: referenced_version[versioned_id_field(resource_def)]}
    req = ParsedRequest()
    if resource_def['soft_delete']:
        # Still return latest after soft delete. It is needed to synthesize
        # full document version.
        req.show_deleted = True
    latest_version = app.data.find_one(collection, req, **query)
    if latest is True:
        return latest_version

    # Syntheisze referenced version from latest and versioned data
    document = synthesize_versioned_document(
        latest_version, referenced_version, resource_def)
    return document


def missing_version_field(data_relation, reference):
    """ Returns a document if it matches the value_field but doesn't have a
    _version field. This is the scenario when there is data in the database
    before document versioning is turned on.

    :param data_relation: the schema definition describing the data_relation.
    :param reference: a dictionary with a value_field and a version_field.

    .. versionadded:: 0.4
    """
    value_field = data_relation['field']
    version_field = app.config['VERSION']
    collection = data_relation['resource']
    query = {}
    query[value_field] = reference[value_field]
    query[version_field] = {'$exists': False}

    return app.data.find_one(collection, None, **query)
