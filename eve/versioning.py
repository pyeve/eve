import copy
from flask import current_app as app, abort
from eve.utils import config, debug_error_message
from werkzeug.exceptions import BadRequestKeyError


def versioned_id_field():
    """ Shorthand to add two commonly added versioning parameters.

    .. versionadded: 0.4
    """
    return app.config['ID_FIELD'] + app.config['VERSION_ID_SUFFIX']


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

        if method == 'PUT' or method == 'PATCH':
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
    _id = app.config['ID_FIELD']

    # push back versioned items if applicable
    # note: MongoDB doesn't have transactions! if the server dies, no
    # history will be saved.
    if resource_def['versioning'] is True:
        # force input as lists
        if not isinstance(documents, list):
            documents = [documents]

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
            ver_doc[versioned_id_field()] = document[_id]
            ver_doc[version] = document[version]

            # add document to the stack
            versioned_documents.append(ver_doc)

        # bulk insert
        app.data.insert(resource + app.config['VERSIONS'], versioned_documents)


def versioned_fields(resource_def):
    """ Returns a list of versioned fields for a resource.

    :param resource_def: a resource definition.

    .. versionchanged:: 0.5
       ETAG is now a versioned field (#369).

    .. versionadded:: 0.4
    """
    schema = resource_def['schema']
    fields = []
    if resource_def['versioning'] is True:
        fields.append(app.config['LAST_UPDATED'])
        fields.append(app.config['ETAG'])
        for field in schema:
            if field not in schema or \
                    schema[field].get('versioned', True) is True:
                fields.append(field)

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
        app.config['ID_FIELD'],
        app.config['LAST_UPDATED'],
        app.config['DATE_CREATED'],
        app.config['ETAG'],
        app.config['LINKS']]

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
    """ Synthesizes an old document from the latest document and the values of
    all versioned fields from the old version. This is accomplished by removing
    all versioned fields from the latest document before updating fields to
    ensure that fields with required=False can be removed.

    :param document: the current version of a document.
    :param delta: the versioned fields from a specific document version.
    :param resource_def: a resource definition.

    .. versionadded:: 0.4
    """
    old_doc = copy.deepcopy(document)

    if versioned_id_field() not in delta:
        abort(400, description=debug_error_message(
            'You must include %s in any projection with a version query.'
            % versioned_id_field()
        ))
    delta[app.config['ID_FIELD']] = delta[versioned_id_field()]
    del delta[versioned_id_field()]

    # remove all versioned fields from document
    fields = versioned_fields(resource_def)
    for field in document:
        if field in fields:
            del old_doc[field]

    # add versioned fields
    old_doc.update(delta)

    return old_doc


def get_old_document(resource, req, lookup, document, version):
    """ Returns an old document if appropriate, otherwise passes the given
    document through.

    :param resource: the name of the resource.
    :param req: the parsed request object.
    :param lookup: a dictionary of lookup parameters.
    :param document: the current version of the document.
    :param version: the value of the version request parameter.

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
        if versioned_id_field() not in lookup:
            lookup[versioned_id_field()] = lookup[app.config['ID_FIELD']]
            del lookup[app.config['ID_FIELD']]
        lookup[config.VERSION] = version

        # synthesize old document from latest and delta
        delta = app.data.find_one(resource + config.VERSIONS, req, **lookup)
        if not delta:
            abort(404)
        document = synthesize_versioned_document(
            document,
            delta,
            config.DOMAIN[resource])

    return document


def get_data_version_relation_document(data_relation, reference, latest=False):
    """ Returns an old document if appropriate, otherwise passes the given
    document through.

    :param data_relation: the schema definition describing the data_relation.
    :param reference: a dictionary with a value_field and a version_field.
    :param latest: if we should obey the version param in reference or not.

    .. versionadded:: 0.4
    """
    value_field = data_relation['field']
    version_field = app.config['VERSION']
    collection = data_relation['resource']
    resource_def = app.config['DOMAIN'][data_relation['resource']]
    query = {}

    # tweak the query if the foreign field is versioned
    if value_field in versioned_fields(resource_def) and latest is False:
        # the field is versioned, search the shadow collection
        collection += app.config['VERSIONS']

        # special consideration for _id overloading
        if value_field == app.config['ID_FIELD']:
            query[value_field + app.config['VERSION_ID_SUFFIX']] = \
                reference[value_field]
        else:
            query[value_field] = reference[value_field]

        # add the version to the query
        query[version_field] = reference[version_field]
    else:
        # the field is not versioned, search the primary doc
        query[value_field] = reference[value_field]
        if latest is False:
            query[version_field] = {'$gte': reference[version_field]}

    return app.data.find_one(collection, None, **query)


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
