# -*- coding: utf-8 -*-

"""
    eve.io.mongo.validation
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module implements the mongo Validator class, used to validate that
    objects incoming via POST/PATCH requests conform to the API domain.
    An extension of Cerberus Validator.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from eve.utils import config
from bson import ObjectId
from flask import current_app as app
from cerberus import Validator
from werkzeug.datastructures import FileStorage
from eve.versioning import get_data_version_relation_document, \
    missing_version_field


class Validator(Validator):
    """ A cerberus.Validator subclass adding the `unique` contraint to
    Cerberus standard validation.

    :param schema: the validation schema, to be composed according to Cerberus
                   documentation.
    :param resource: the resource name.

    .. versionchanged:: 0.0.6
       Support for 'allow_unknown' which allows to successfully validate
       unknown key/value pairs.

    .. versionchanged:: 0.0.4
       Support for 'transparent_schema_rules' introduced with Cerberus 0.0.3,
       which allows for insertion of 'default' values in POST requests.
    """
    def __init__(self, schema, resource=None):
        self.resource = resource
        self._id = None
        super(Validator, self).__init__(schema, transparent_schema_rules=True)
        if resource:
            self.allow_unknown = config.DOMAIN[resource]['allow_unknown']

    def validate_update(self, document, _id):
        """ Validate method to be invoked when performing an update, not an
        insert.

        :param document: the document to be validated.
        :param _id: the unique id of the document.
        """
        self._id = _id
        return super(Validator, self).validate_update(document)

    def validate_replace(self, document, _id):
        """ Validation method to be invoked when performing a document
        replacement. This differs from :func:`validation_update` since in this
        case we want to perform a full :func:`validate` (the new document is to
        be considered a new insertion and required fields needs validation).
        However, like with validate_update, we also want the current _id
        not to be checked when validationg 'unique' values.

        .. versionadded:: 0.1.0
        """
        self._id = _id
        return super(Validator, self).validate(document)

    def _validate_unique(self, unique, field, value):
        """ Enables validation for `unique` schema attribute.

        :param unique: Boolean, wether the field value should be
                       unique or not.
        :param field: field name.
        :param value: field value.

        .. versionchanged:: 0.3
           Support for new 'self._error' signature introduced with Cerberus
           v0.5.

        .. versionchanged:: 0.2
           Handle the case in which ID_FIELD is not of ObjectId type.
        """
        if unique:
            query = {field: value}
            if self._id:
                try:
                    query[config.ID_FIELD] = {'$ne': ObjectId(self._id)}
                except:
                    query[config.ID_FIELD] = {'$ne': self._id}

            if app.data.find_one(self.resource, None, **query):
                self._error(field, "value '%s' is not unique" % value)

    def _validate_data_relation(self, data_relation, field, value):
        """ Enables validation for `data_relation` field attribute. Makes sure
        'value' of 'field' adheres to the referential integrity rule specified
        by 'data_relation'.

        :param data_relation: a dict following keys:
            'collection': foreign collection name
            'field': foreign field name
            'version': True if this relation points to a specific version
            'type': the type for the reference field if 'version': True
        :param field: field name.
        :param value: field value.

        .. versionchanged:: 0.4
           Support for document versioning.

        .. versionchanged:: 0.3
           Support for new 'self._error' signature introduced with Cerberus
           v0.5.

        .. versionchanged:: 0.1.1
           'collection' key renamed to 'resource' (data_relation)

        .. versionadded: 0.0.5
        """
        if 'version' in data_relation and data_relation['version'] is True:
            value_field = data_relation['field']
            version_field = app.config['VERSION']

            # check value format
            if isinstance(value, dict) and value_field in value \
                    and version_field in value:
                resource_def = config.DOMAIN[data_relation['resource']]
                if resource_def['versioning'] is False:
                    self._error(
                        field, "can't save a version with"
                        " data_relation if '%s' isn't versioned" %
                        data_relation['resource'])
                else:
                    search = None

                    # support late versioning
                    if value[version_field] == 1:
                        # there is a chance this document hasn't been saved
                        # since versioning was turned on
                        search = missing_version_field(data_relation, value)

                    if not search:
                        search = get_data_version_relation_document(
                            data_relation, value)

                    if not search:
                        self._error(
                            field, "value '%s' must exist in resource"
                            " '%s', field '%s' at version '%s'." % (
                                value[value_field], data_relation['resource'],
                                data_relation['field'], value[version_field]))
            else:
                self._error(
                    field, "versioned data_relation must be a dict"
                    " with fields '%s' and '%s'" %
                    (value_field, version_field))
        else:
            query = {data_relation['field']: value}
            if not app.data.find_one(data_relation['resource'], None, **query):
                self._error(
                    field,
                    "value '%s' must exist in resource '%s', field '%s'." %
                    (value, data_relation['resource'], data_relation['field']))

    def _validate_type_objectid(self, field, value):
        """ Enables validation for `objectid` data type.

        :param field: field name.
        :param value: field value.

        .. versionchanged:: 0.3
           Support for new 'self._error' signature introduced with Cerberus
           v0.5.

        .. versionchanged:: 0.1.1
           regex check replaced with proper type check.
        """
        if not isinstance(value, ObjectId):
            self._error(field, "value '%s' cannot be converted to a ObjectId"
                        % value)

    def _validate_readonly(self, read_only, field, value):
        """ Since default values are now resolved before validation we make
        sure that a value for a read-only field is considered legit if it
        matches an eventual 'default' setting for the field.

        .. versionadded:: 0.4
        """
        default = config.DOMAIN[self.resource]['schema'][field].get('default')
        if value != default:
            super(Validator, self)._validate_readonly(read_only, field, value)

    def _validate_type_media(self, field, value):
        """ Enables validation for `media` data type.

        :param field: field name.
        :param value: field value.

        .. versionadded:: 0.3
        """
        if not isinstance(value, FileStorage):
            self._error(field, "file was expected, got '%s' instead." % value)
