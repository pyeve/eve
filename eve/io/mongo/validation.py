# -*- coding: utf-8 -*-

"""
    eve.io.mongo.validation
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module implements the mongo Validator class, used to validate that
    objects incoming via POST/PATCH requests conform to the API domain.
    An extension of Cerberus Validator.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import re
from eve.utils import config
from bson import ObjectId
from flask import current_app as app
from cerberus import Validator
from cerberus.errors import ERROR_BAD_TYPE


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
        self.object_id = None
        super(Validator, self).__init__(schema, transparent_schema_rules=True)
        if resource:
            self.allow_unknown = config.DOMAIN[resource]['allow_unknown']

    def validate_update(self, document, object_id):
        """ Validate method to be invoked when performing an update, not an
        insert.

        :param document: the document to be validated.
        :param object_id: the unique id of the document.
        """
        self.object_id = object_id
        return super(Validator, self).validate_update(document)

    def _validate_unique(self, unique, field, value):
        """ Enables validation for `unique` schema attribute.

        :param unique: Boolean, wether the field value should be
                       unique or not.
        :param field: field name.
        :param value: field value.
        """
        if unique:
            query = {field: value}
            if self.object_id:
                query[config.ID_FIELD] = {'$ne': ObjectId(self.object_id)}
            if app.data.find_one(self.resource, **query):
                self._error("value '%s' for field '%s' not unique" %
                            (value, field))

    def _validate_data_relation(self, data_relation, field, value):
        """ Enables validation for `data_relation` field attribute. Makes sure
        'value' of 'field' adheres to the referential integrity rule specified
        by 'data_relation'.

        :param data_relation: a dict following keys:
            'collection': foreign collection name
            'field': foreign field name
        :param field: field name.
        :param value: field value.

        .. versionadded: 0.0.5
        """
        query = {data_relation['field']: value}
        if not app.data.find_one(data_relation['collection'], **query):
                self._error("value '%s' for field '%s' must exist in "
                            "collection '%s', field '%s'" %
                            (value, field, data_relation['collection'],
                             data_relation['field']))

    def _validate_type_objectid(self, field, value):
        """ Enables validation for `objectid` schema attribute.

        :param unique: Boolean, wether the field value should be
                       unique or not.
        :param field: field name.
        :param value: field value.
        """
        if not re.match('[a-f0-9]{24}', value):
            self._error(ERROR_BAD_TYPE % (field, 'ObjectId'))
