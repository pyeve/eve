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

ERROR_BAD_RESOURCE_LINK = "'%s' must be an ObjectID of an item of type %s"
ERROR_INVALID_RESOURCE_LINK = "'%s' is not a recognized resource"

class Validator(Validator):
    """ A cerberus.Validator subclass adding the `unique` contraint to
    Cerberus standard validation.

    :param schema: the validation schema, to be composed according to Cerberus
                   documentation.
    :param resource: the resource name.

    .. versionchanged:: 0.0.4
       Support for 'transparent_schema_rules' introduced with Cerberus 0.0.3,
       which allows for insertion of 'default' values in POST requests.
    """
    def __init__(self, schema, resource=None):
        self.resource = resource
        self.object_id = None
        super(Validator, self).__init__(schema,
                                        transparent_schema_rules=True)

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

    def _validate_type_objectid(self, field, value):
        """ Enables validation for `objectid` type.

        :param field: field name.
        :param value: field value.
        """
        if not re.match('[a-f0-9]{24}', value):
            self._error(ERROR_BAD_TYPE % (field, 'ObjectId'))

    def _validate_resource(self, resource_name, field, value):
        """ Enables validation for `resource` schema attribute.

        :param resource_type: the referenced resource
        :param field: field name.
        :param value: field value.
        """

        print resource_name
        print config.DOMAIN
        print [resource for resource in config.DOMAIN]
        print [(config.DOMAIN[resource]['item_title'].lower(), resource) for resource in config.DOMAIN]

        query = {config.ID_FIELD: ObjectId(value)}
        item_names = dict([(config.DOMAIN[resource]['item_title'].lower(), resource) for resource in config.DOMAIN])

        if resource_name not in item_names:
            self._error(ERROR_INVALID_RESOURCE_LINK % (resource_name,))
        elif not app.data.find_one(item_names[resource_name],**query):
            self._error(ERROR_BAD_RESOURCE_LINK % (field, resource_name))