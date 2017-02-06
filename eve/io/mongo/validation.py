# -*- coding: utf-8 -*-

"""
    eve.io.mongo.validation
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module implements the mongo Validator class, used to validate that
    objects incoming via POST/PATCH requests conform to the API domain.
    An extension of Cerberus Validator.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import copy
from bson import ObjectId
from bson.dbref import DBRef
from collections import Mapping
from flask import current_app as app
from werkzeug.datastructures import FileStorage
from cerberus import Validator

from eve.auth import auth_field_and_value
from eve.io.mongo.geo import Point, MultiPoint, LineString, Polygon, \
    MultiLineString, MultiPolygon, GeometryCollection
from eve.utils import config, str_type
from eve.versioning import get_data_version_relation_document


class Validator(Validator):
    """ A cerberus.Validator subclass adding the `unique` contraint to
    Cerberus standard validation.

    :param schema: the validation schema, to be composed according to Cerberus
                   documentation.
    :param resource: the resource name.

    .. versionchanged:: 0.6.1
       __init__ signature update for cerberus v0.8.1 compatibility.
       Disable 'transparent_schema_rules' by default in favor of explicit
       validators for rules unsupported by cerberus. This can be overridden
       globally or on a per-resource basis through a config option.

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
    def __init__(self, schema=None, resource=None, allow_unknown=False,
                 transparent_schema_rules=False):
        self.resource = resource
        self._id = None
        self._original_document = None

        if resource:
            transparent_schema_rules = \
                config.DOMAIN[resource]['transparent_schema_rules']
            allow_unknown = config.DOMAIN[resource]['allow_unknown']
        super(Validator, self).__init__(
            schema,
            transparent_schema_rules=transparent_schema_rules,
            allow_unknown=allow_unknown)

    def validate_update(self, document, _id, original_document=None):
        """ Validate method to be invoked when performing an update, not an
        insert.

        :param document: the document to be validated.
        :param _id: the unique id of the document.
        """
        self._id = _id
        self._original_document = original_document
        return super(Validator, self).validate_update(document)

    def validate_replace(self, document, _id, original_document=None):
        """ Validation method to be invoked when performing a document
        replacement. This differs from :func:`validation_update` since in this
        case we want to perform a full :func:`validate` (the new document is to
        be considered a new insertion and required fields needs validation).
        However, like with validate_update, we also want the current _id
        not to be checked when validationg 'unique' values.

        .. versionadded:: 0.1.0
        """
        self._id = _id
        self._original_document = original_document
        return super(Validator, self).validate(document)

    def _validate_default(self, unique, field, value):
        """ Fake validate function to let cerberus accept "default"
            as keyword in the schema

        .. versionadded:: 0.6.2
        """
        pass

    def _validate_versioned(self, unique, field, value):
        """ Fake validate function to let cerberus accept "versioned"
            as keyword in the schema

        .. versionadded:: 0.6.2
        """
        pass

    def _validate_unique_to_user(self, unique, field, value):
        """ Validates that a value is unique to the active user. Active user is
        the user authenticated for current request. See #646.

        .. versionadded: 0.6
        """

        auth_field, auth_value = auth_field_and_value(self.resource)

        # if an auth value has been set for this request, then make sure it is
        # taken into account when checking for value uniqueness.
        query = {auth_field: auth_value} if auth_field else {}

        self._is_value_unique(unique, field, value, query)

    def _validate_unique(self, unique, field, value):
        """ Enables validation for `unique` schema attribute.

        :param unique: Boolean, wether the field value should be
                       unique or not.
        :param field: field name.
        :param value: field value.

        .. versionchanged:: 0.6
           Validates field value uniqueness against the whole datasource,
           indipendently of the request method. See #646.

        .. versionchanged:: 0.3
           Support for new 'self._error' signature introduced with Cerberus
           v0.5.

        .. versionchanged:: 0.2
           Handle the case in which ID_FIELD is not of ObjectId type.
        """
        self._is_value_unique(unique, field, value, {})

    def _is_value_unique(self, unique, field, value, query):
        """ Validates that a field value is unique.

        .. versionchanged:: 0.6.2
           Exclude soft deleted documents from uniqueness check. Closes #831.

        .. versionadded:: 0.6
        """
        if unique:
            query[field] = value

            resource_config = config.DOMAIN[self.resource]

            # exclude soft deleted documents if applicable
            if resource_config['soft_delete']:
                # be aware that, should a previously (soft) deleted document be
                # restored, and because we explicitly ignore soft deleted
                # documents while validating 'unique' fields, there is a chance
                # that a unique field value will end up being now duplicated
                # in two documents: the restored one, and the one which has
                # been stored with the same field value while the original
                # document was in 'deleted' state.

                # we make sure to also include documents which are missing the
                # DELETED field. This happens when soft deletes are enabled on
                # an a resource with existing documents.
                query[config.DELETED] = {'$ne': True}

            # exclude current document
            if self._id:
                id_field = resource_config['id_field']
                query[id_field] = {'$ne': self._id}

            # we perform the check on the native mongo driver (and not on
            # app.data.find_one()) because in this case we don't want the usual
            # (for eve) query injection to interfere with this validation. We
            # are still operating within eve's mongo namespace anyway.

            datasource, _, _, _ = app.data.datasource(self.resource)
            if app.data.driver.db[datasource].find_one(query):
                self._error(field, "value '%s' is not unique" % value)

    def _validate_data_relation(self, data_relation, field, value):
        """ Enables validation for `data_relation` field attribute. Makes sure
        'value' of 'field' adheres to the referential integrity rule specified
        by 'data_relation'.

        :param data_relation: a dict following keys:
            'resource': foreign resource name
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
                    query = {data_relation['field']: item.id
                             if isinstance(item, DBRef) else item}
                    if not app.data.find_one(data_resource, None, **query):
                        self._error(
                            field,
                            "value '%s' must exist in resource"
                            " '%s', field '%s'." %
                            (item.id if isinstance(item, DBRef) else item,
                             data_resource, data_relation['field']))

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

    def _validate_type_dbref(self, field, value):
        """ Enables validation for `DBRef` data type.

        :param field: field name.
        :param value: field value.

        """
        if not isinstance(value, DBRef):
            self._error(field, "value '%s' cannot be converted to a DBRef"
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

        .. versionchanged:: 0.6.1
           Fix: dependencies on sub-document fields are now properly
           processed (#706).

        .. versionchanged:: 0.6
           Fix: Only evaluate dependencies that don't have valid default
           values.

        .. versionchanged:: 0.5.1
           Fix: dependencies with value checking seems broken #547.

        .. versionadded:: 0.5
           If a dependency has a default value, skip it as Cerberus does not
           have the notion of default values and would report a missing
           dependency (#353).
           Fix for #363 (see docstring).
        """
        if dependencies is None:
            return True

        if isinstance(dependencies, str_type):
            dependencies = [dependencies]

        defaults = {}
        for d in dependencies:
            root = d.split('.')[0]
            default = self.schema[root].get('default')
            if default and root not in document:
                defaults[root] = default

        if isinstance(dependencies, Mapping):
            # Only evaluate dependencies that don't have *valid* defaults
            for k, v in defaults.items():
                if v in dependencies[k]:
                    del(dependencies[k])
        else:
            # Only evaluate dependencies that don't have defaults values
            dependencies = [d for d in dependencies if d not in
                            defaults.keys()]

        dcopy = None
        if self._original_document:
            dcopy = copy.copy(document)
            dcopy.update(self._original_document)
        return super(Validator, self)._validate_dependencies(dcopy or document,
                                                             dependencies,
                                                             field,
                                                             break_on_error)

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

    def _error(self, field, _error):
        """ Change the default behaviour so that, if VALIDATION_ERROR_AS_LIST
        is enabled, single validation errors are returned as a list. See #536.

        :param field: field name
        :param _error: field error(s)

        .. versionadded:: 0.6
        """
        super(Validator, self)._error(field, _error)
        if config.VALIDATION_ERROR_AS_LIST:
            err = self._errors[field]
            if not isinstance(err, list):
                self._errors[field] = [err]
