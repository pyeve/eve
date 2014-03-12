import copy
from flask import current_app as app, abort
from eve.utils import config, debug_error_message
from werkzeug.exceptions import BadRequestKeyError

def versioned_id_field():
    """ Shorthand to add two commonly added versioning parameters.

    .. versionadded: 0.4
    """
    return app.config['ID_FIELD']+app.config['VERSION_ID_SUFFIX']

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

    if resource_def['versioning'] == True:
        if method == 'GET' and latest_doc == None:
            # especially on collection endpoints, we don't to encure an extra
            # lookup if we are already pulling the latest version
            if version not in document:
                # well it should be... the api designer must have turned on
                # versioning after data was already in the collection or the
                # collection has been modified without respecting versioning
                document[version] = 0 # the first saved version will be 1
            document[latest_version] = document[version]
        
        if method == 'GET' and latest_doc != None:
            if version not in latest_doc:
                # well it should be... the api designer must have turned on
                # versioning after data was already in the collection or the
                # collection has been modified without respecting versioning
                document[version] = 0 # the first saved version will be 1
                document[latest_version] = document[version]
            else:
                document[latest_version] = latest_doc[version]
                if version not in document:
                    # this version was put in the database before versioning was
                    # turned on or outside of Eve
                    document[version] = 0
        
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
                # versioning was turned of for a while, version numbers will not
                # be consistent! you have been warned
                document[version] = 1

def insert_versioning_documents(resource, ids, documents):
    """ Insert versioning copy of document. Intended for POST, PUT, and PATCH.

    :param resource: the resource of the request/document.
    :param ids: a list of id number coorsponding to the documents parameter.
    :param documents: the documents be written by POST, PUT, or PATCH.

    .. versionadded:: 0.4
    """
    resource_def = app.config['DOMAIN'][resource]

    # push back versioned items if applicable
    # note: MongoDB doesn't have transactions! if the server dies, no
    # history will be saved.
    if resource_def['versioning'] == True:
        # force inputs as lists
        if not isinstance(ids, list):
            ids = [ids]
        if not isinstance(documents, list):
            documents = [documents]
        
        # make sure we have the same number in each list
        if len(ids) != len(documents):
            abort(500, description=debug_error_message(
                'Must have the same number of ids and documents'
            ))
        
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
            ver_doc[versioned_id_field()] = ids[index]
            ver_doc[version] = document[version]
        
            # add document to the stack
            versioned_documents.append(ver_doc)

        # bulk insert
        app.data.insert(resource+app.config['VERSIONS'], versioned_documents)


def versioned_fields(resource_def):
    """ Returns a list of versioned fields for a resource.

    :param resource_def: a resource definition.

    .. versionadded:: 0.4
    """
    fields = []
    if resource_def['versioning'] == True:
        fields.append(app.config['LAST_UPDATED'])
        for field in resource_def['schema']:
            if field not in resource_def['schema'] or \
                resource_def['schema'][field].get('versioned', True) == True:
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
    fields = resource_def['schema'].keys() + [app.config['VERSION'], \
        app.config['LATEST_VERSION'], app.config['ID_FIELD'], \
        app.config['LAST_UPDATED'], app.config['DATE_CREATED'], \
        app.config['ETAG'], app.config['LINKS']]

    for field in fields:
        if field in new_doc and (field not in old_doc or \
            new_doc[field] != old_doc[field]):
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
    if version != 'all' and version != 'diffs' and version != None:
        try:
            version = int(version)
            assert version > 0
        except (ValueError, BadRequestKeyError, AssertionError):
            abort(400, description=debug_error_message(
                'Document version number should be an int greater than 0'
            ))

        # parameters to find specific document version
        lookup[versioned_id_field()] = lookup[app.config['ID_FIELD']]
        del lookup[app.config['ID_FIELD']]
        lookup[config.VERSION] = version

        # synthesize old document from latest and delta
        delta = app.data.find_one(resource+config.VERSIONS, req, **lookup)
        if not delta:
            abort(404)
        document = synthesize_versioned_document(document, delta,
            config.DOMAIN[resource])
        
    return document
