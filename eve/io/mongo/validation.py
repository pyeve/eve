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
from bson import ObjectId, decimal128
from bson.dbref import DBRef
from flask import current_app as app
from werkzeug.datastructures import FileStorage

from eve.auth import auth_field_and_value
from eve.io.mongo.geo import (
    Point,
    MultiPoint,
    LineString,
    Polygon,
    MultiLineString,
    MultiPolygon,
    GeometryCollection,
    Feature,
    FeatureCollection,
)
from eve.utils import config
from eve.validation import Validator
from eve.versioning import get_data_version_relation_document


class Validator(Validator):
    """A cerberus.Validator subclass adding the `unique` contraint to
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

    def _validate_versioned(self, unique, field, value):
        """{'type': 'boolean'}"""
        pass

    def _validate_unique_to_user(self, unique, field, value):
        """{'type': 'boolean'}"""
        auth_field, auth_value = auth_field_and_value(self.resource)

        # if an auth value has been set for this request, then make sure it is
        # taken into account when checking for value uniqueness.
        query = {auth_field: auth_value} if auth_field else {}

        self._is_value_unique(unique, field, value, query)

    def _validate_unique_within_resource(self, unique, field, value):
        """{'type': 'boolean'}"""
        _, filter_, _, _ = app.data.datasource(self.resource)
        if filter_ is None:
            filter_ = {}
        self._is_value_unique(unique, field, value, filter_)

    def _validate_unique(self, unique, field, value):
        """{'type': 'boolean'}"""
        self._is_value_unique(unique, field, value, {})

    def _is_value_unique(self, unique, field, value, query):
        """Validates that a field value is unique.

        .. versionchanged:: 0.6.2
           Exclude soft deleted documents from uniqueness check. Closes #831.

        .. versionadded:: 0.6
        """
        if unique:

            # In order to create the right query to check for unique values
            # We need to obtain the schema path for the current field
            # excluding any list fields in between.
            schema = self.root_schema
            document_field_path = list(self.document_path) + [field]
            field_schema_path = []

            while document_field_path:
                current_schema_path_type = schema.get("type")
                path = document_field_path.pop(0)
                if current_schema_path_type == "dict":
                    schema = schema["schema"][path]
                    field_schema_path.append(path)
                elif schema.get("type") == "list":
                    schema = schema["schema"]
                else:
                    schema = schema[path]
                    field_schema_path.append(path)

            query[".".join(field_schema_path)] = value
            resource_config = config.DOMAIN[self.resource]

            # exclude soft deleted documents if applicable
            if resource_config["soft_delete"]:
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
                query[config.DELETED] = {"$ne": True}

            # exclude current document
            if self.document_id:
                id_field = resource_config["id_field"]
                query[id_field] = {"$ne": self.document_id}

            # we perform the check on the native mongo driver (and not on
            # app.data.find_one()) because in this case we don't want the usual
            # (for eve) query injection to interfere with this validation. We
            # are still operating within eve's mongo namespace anyway.

            datasource, _, _, _ = app.data.datasource(self.resource)
            if app.data.driver.db[datasource].find_one(query):
                self._error(field, "value '%s' is not unique" % value)

    def _validate_data_relation(self, data_relation, field, value):
        """{'type': 'dict',
        'schema': {
           'resource': {'type': 'string', 'required': True},
           'field': {'type': 'string', 'required': True},
           'embeddable': {'type': 'boolean', 'default': False},
           'version': {'type': 'boolean', 'default': False}
        }}"""
        if not value and self.schema[field].get("nullable"):
            return

        if "version" in data_relation and data_relation["version"] is True:
            value_field = data_relation["field"]
            version_field = app.config["VERSION"]

            # check value format
            if (
                isinstance(value, dict)
                and value_field in value
                and version_field in value
            ):
                resource_def = config.DOMAIN[data_relation["resource"]]
                if resource_def["versioning"] is False:
                    self._error(
                        field,
                        "can't save a version with"
                        " data_relation if '%s' isn't versioned"
                        % data_relation["resource"],
                    )
                else:
                    search = get_data_version_relation_document(data_relation, value)

                    if not search:
                        self._error(
                            field,
                            "value '%s' must exist in resource"
                            " '%s', field '%s' at version '%s'."
                            % (
                                value[value_field],
                                data_relation["resource"],
                                data_relation["field"],
                                value[version_field],
                            ),
                        )
            else:
                self._error(
                    field,
                    "versioned data_relation must be a dict"
                    " with fields '%s' and '%s'" % (value_field, version_field),
                )
        else:
            if not isinstance(value, list):
                value = [value]

            data_resource = data_relation["resource"]
            for item in value:
                query = {
                    data_relation["field"]: item.id if isinstance(item, DBRef) else item
                }
                if not app.data.find_one(data_resource, None, **query):
                    self._error(
                        field,
                        "value '%s' must exist in resource"
                        " '%s', field '%s'."
                        % (
                            item.id if isinstance(item, DBRef) else item,
                            data_resource,
                            data_relation["field"],
                        ),
                    )


def is_valid_objectid(field, value, error):
    if not ObjectId.is_valid(value):
        error(field, "Must be a valid objectid")


def is_valid_decimal(field, value, error):
    if not isinstance(value, decimal128.Decimal128):
        error(field, "Must be a valid decimal number")


def is_valid_dbref(field, value, error):
    if not isinstance(value, DBRef):
        error(field, "Must be a valid dbref")


def is_valid_media(field, value, error):
    if not isinstance(value, FileStorage):
        error(field, "Must be a valid filestorage")


def is_valid_point(field, value, error):
    try:
        Point(value)
    except TypeError:
        error(field, "Must be a valid point")


def is_valid_linestring(field, value, error):
    try:
        LineString(value)
    except TypeError:
        error(field, "Must be a valid linestring")


def is_valid_polygon(field, value, error):
    try:
        Polygon(value)
    except TypeError:
        error(field, "Must be a valid polygon")


def is_valid_multipoint(field, value, error):
    try:
        MultiPoint(value)
    except TypeError:
        error(field, "Must be a valid multipoint")


def is_valid_multilinestring(field, value, error):
    try:
        MultiLineString(value)
    except TypeError:
        error(field, "Must be a valid multilinestring")


def is_valid_multipolygon(field, value, error):
    try:
        MultiPolygon(value)
    except TypeError:
        error(field, "Must be a valid multipolygon")


def is_valid_geometrycollection(field, value, error):
    try:
        GeometryCollection(value)
    except TypeError:
        error(field, "Must be a valid geometrycollection")


def is_valid_feature(field, value, error):
    try:
        Feature(value)
    except TypeError:
        error(field, "Must be a valid feature")


def is_valid_featurecollection(field, value, error):
    try:
        FeatureCollection(value)
    except TypeError:
        error(field, "Must be a valid featurecollection")
