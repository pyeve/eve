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

import copy
from collections import Mapping
from eve.utils import config, str_type
from bson import ObjectId
from flask import current_app as app
from cerberus import Validator
from werkzeug.datastructures import FileStorage
from eve.versioning import get_data_version_relation_document, \
    missing_version_field
from eve.io.mongo.geo import Point, MultiPoint, LineString, Polygon, \
    MultiLineString, MultiPolygon, GeometryCollection


class Validator(Validator):
    """ A cerberus.Validator subclass adding the `unique` contraint to
    Cerberus standard validation.

    :param schema: the validation schema, to be composed according to Cerberus
                   documentation.
    :param resource: the resource name.

    .. versionchanged:: 0.5
       Support for _original_document
       Fix crash bug with Cerberus 0.7.1+ and keyschema rule. See Cerberus #48.

    .. versionchanged:: 0.0.6
       Support for 'allow_unknown' which allows to successfully validate
       unknown key/value pairs.

    .. versionchanged:: 0.0.4
       Support for 'transparent_schema_rules' introduced with Cerberus 0.0.3,
       which allows for insertion of 'default' values in POST requests.
    """
    def __init__(self, schema=None, resource=None):
        self.resource = resource
        self._id = None
        self._original_document = None
        super(Validator, self).__init__(schema, transparent_schema_rules=True)
        if resource:
            self.allow_unknown = config.DOMAIN[resource]['allow_unknown']

    def validate_update(self, document, _id, original_document=None):
        """ Validate method to be invoked when performing an update, not an
        insert.

        :param document: the document to be validated.
        :param _id: the unique id of the document.
        """
        self._id = _id
        self._original_document = original_document
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
            if not isinstance(value, list):
                value = [value]

            data_resource = data_relation['resource']
            for item in value:
                    query = {data_relation['field']: item}
                    if not app.data.find_one(data_resource, None, **query):
                        self._error(
                            field,
                            "value '%s' must exist in resource"
                            " '%s', field '%s'." %
                            (item, data_resource, data_relation['field']))

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
        """
        .. versionchanged:: 0.5
           Not taking defaul values in consideration anymore since they are now
           being resolved after validation (#353).
           Consider the original value if available (#479).

        .. versionadded:: 0.4
        """
        original_value = self._original_document.get(field) \
            if self._original_document else None
        if value != original_value:
            super(Validator, self)._validate_readonly(read_only, field, value)

    def _validate_dependencies(self, document, dependencies, field,
                               break_on_error=False):
        """ With PATCH method, the validator is only provided with the updated
        fields. If an updated field depends on another field in order to be
        edited and the other field was previously set, the validator doesn't
        see it and rejects the update. In order to avoid that we merge the
        proposed changes with the original document before validating
        dependencies.

        .. versionadded:: 0.5
           If a dependency has a default value, skip it as Cerberus does not
           have the notion of default values and would report a missing
           dependency (#353).
           Fix for #363 (see docstring).
        """
        # Ensure `dependencies` is a list
        if isinstance(dependencies, str_type):
            dependencies = [dependencies]
        elif isinstance(dependencies, Mapping):
            dependencies = dependencies.keys()

        # Filter out dependencies with default values
        dependencies = [d for d in dependencies
                        if self.schema[d].get('default') is None]

        dcopy = None
        if self._original_document:
            dcopy = copy.copy(document)
            dcopy.update(self._original_document)
        super(Validator, self)._validate_dependencies(dcopy or document,
                                                      dependencies, field)

    def _validate_type_media(self, field, value):
        """ Enables validation for `media` data type.

        :param field: field name.
        :param value: field value.

        .. versionadded:: 0.3
        """
        if not isinstance(value, FileStorage):
            self._error(field, "file was expected, got '%s' instead." % value)

    def _validate_type_point(self, field, value):
        """ Enables validation for `point` data type.

        :param field: field name.
        :param value: field value.
        """
        try:
            Point(value)
        except TypeError as e:
            self._error(field, "Point not correct %s: %s" % (value, e))

    def _validate_type_linestring(self, field, value):
        """ Enables validation for `linestring` data type.

        :param field: field name.
        :param value: field value.
        """
        try:
            LineString(value)
        except TypeError:
            self._error(field, "LineString not correct %s " % value)

    def _validate_type_polygon(self, field, value):
        """ Enables validation for `polygon` data type.

        :param field: field name.
        :param value: field value.
        """
        try:
            Polygon(value)
        except TypeError:
            self._error(field, "LineString not correct %s " % value)

    def _validate_type_multipoint(self, field, value):
        """ Enables validation for `multipoint` data type.

        :param field: field name.
        :param value: field value.
        """
        try:
            MultiPoint(value)
        except TypeError:
            self._error(field, "MultiPoint not correct" % value)

    def _validate_type_multilinestring(self, field, value):
        """ Enables validation for `multilinestring`data type.

        :param field: field name.
        :param value: field value.
        """
        try:
            MultiLineString(value)
        except TypeError:
            self._error(field, "MultiLineString not  correct" % value)

    def _validate_type_multipolygon(self, field, value):
        """ Enables validation for `multipolygon` data type.

        :param field: field name.
        :param value: field value.
        """
        try:
            MultiPolygon(value)
        except TypeError:
            self._error(field, "MultiPolygon not  correct" % value)

    def _validate_type_geometrycollection(self, field, value):
        """ Enables validation for `geometrycollection`data type

        :param field: field name.
        :param value: field nvalue
        """
        try:
            GeometryCollection(value)
        except TypeError:
            self._error(field, "GeometryCollection not correct" % value)
