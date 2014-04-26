# -*- coding: utf-8 -*-

"""
    eve.io.sql.validation
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module implements the SQLAlchemy Validator class,
    used to validate that objects incoming via POST/PATCH requests
    conform to the API domain.
    An extension of Cerberus Validator.

    :copyright: (c) 2013 by Nicola Iarocci, Tomasz Jezierski (Tefnet).
    :license: BSD, see LICENSE for more details.
"""

from cerberus import Validator
from eve.utils import config
from flask import current_app as app
from eve.versioning import get_data_version_relation_document, missing_version_field


class ValidatorSQL(Validator):
    """ A cerberus.Validator subclass adding the `unique` constraint to
    Cerberus standard validation.

    :param schema: the validation schema, to be composed according to Cerberus
                   documentation.
    :param resource: the resource name.
    """
    def __init__(self, schema, resource=None):
        self.resource = resource
        self.object_id = None
        super(ValidatorSQL, self).__init__(schema, transparent_schema_rules=True)

    def validate_update(self, document, object_id):
        """ Validate method to be invoked when performing an update, not an
        insert.

        :param document: the document to be validated.
        :param object_id: the unique id of the document.
        """
        self.object_id = object_id
        return super(ValidatorSQL, self).validate_update(document)

    def validate_replace(self, document, _id):
        self._id = _id
        if super(ValidatorSQL, self).validate(document) is False:
            return False
        # SQL is a fixed schema db so query for rows where fields haven't been set return None or null in json
        # In order for the etag computation to work when replacing entries with incomplete documents we need
        # to insert the missing fields as None
        document.update({k: None for k in self.schema.keys() if k not in document and k != '_id'})
        return True


    def _validate_unique(self, unique, field, value):
        """ Enables validation for `unique` schema attribute.

        :param unique: Boolean, wether the field value should be
                       unique or not.
        :param field: field name.
        :param value: field value.
        """
        if unique:
            query = {field: value}
            if app.data.find_one(self.resource, None, **query):
                self._error(field, "value '%s' is not unique" % value)

    def _validate_data_relation(self, data_relation, field, value):
        if 'version' in data_relation and data_relation['version'] is True:
            value_field = data_relation['field']
            version_field = app.config['VERSION']

            # check value format
            if isinstance(value, dict) and value_field in value and version_field in value:
                resource_def = config.DOMAIN[data_relation['resource']]
                if resource_def['versioning'] is False:
                    self._error(field, "can't save a version with data_relation if '%s' isn't versioned" %
                                data_relation['resource'])
                else:
                    # support late versioning
                    if value[version_field] == 0:
                        # there is a chance this document hasn't been saved
                        # since versioning was turned on
                        search = missing_version_field(data_relation, value)
                    else:
                        search = get_data_version_relation_document(data_relation, value)
                    if not search:
                        self._error(field, "value '%s' must exist in resource '%s', field '%s' at version '%s'." % (
                                    value[value_field], data_relation['resource'],
                                    data_relation['field'], value[version_field]))
            else:
                self._error(field, "versioned data_relation must be a dict with fields '%s' and '%s'" %
                            (value_field, version_field))
        else:
            query = {data_relation['field']: value}
            if not app.data.find_one(data_relation['resource'], None, **query):
                self._error(field, "value '%s' must exist in resource '%s', field '%s'." %
                            (value, data_relation['resource'], data_relation['field']))

    def _validate_type_objectid(self, field, value):
        """ Enables validation for `objectid` schema attribute.

        :param unique: Boolean, wether the field value should be
                       unique or not.
        :param field: field name.
        :param value: field value.
        """
        # TODO ?
        pass
