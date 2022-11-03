# -*- coding: utf-8 -*-

"""
    eve.validation
    ~~~~~~~~~~~~~~

    Helper module. Allows eve submodules (methods.patch/post) to be fully
    datalayer-agnostic. Specialized Validator classes are implemented in the
    datalayer submodules.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import copy

import cerberus
import cerberus.errors
from cerberus import DocumentError, SchemaError  # noqa

from eve.utils import config


class Validator(cerberus.Validator):
    def __init__(self, *args, **kwargs):
        if not config.VALIDATION_ERROR_AS_LIST:
            kwargs["error_handler"] = SingleErrorAsStringErrorHandler

        self.is_update_operation = False
        super().__init__(*args, **kwargs)

    def validate_update(
        self, document, document_id, persisted_document=None, normalize_document=True
    ):
        """Validate method to be invoked when performing an update, not an
        insert.

        :param document: the document to be validated.
        :param document_id: the unique id of the document.
        :param persisted_document: the persisted document to be updated.
        :param normalize_document: whether apply normalization during patch.
        """
        self.is_update_operation = True
        self.document_id = document_id
        self.persisted_document = persisted_document
        return super().validate(
            document, update=True, normalize=normalize_document
        )

    def validate_replace(self, document, document_id, persisted_document=None):
        """Validation method to be invoked when performing a document
        replacement. This differs from :func:`validation_update` since in this
        case we want to perform a full :func:`validate` (the new document is to
        be considered a new insertion and required fields needs validation).
        However, like with validate_update, we also want the current document_id
        not to be checked when validating 'unique' values.

        :param document: the document to be validated.
        :param document_id: the unique id of the document.
        :param persisted_document: the persisted document to be updated.

        .. versionadded:: 0.1.0
        """
        self.document_id = document_id
        self.persisted_document = persisted_document
        return super().validate(document)

    def _normalize_default(self, mapping, schema, field):
        """{'nullable': True}"""

        # fields with no default are of no use here
        if "default" not in schema[field]:
            return

        # if the request already contains the field, we don't set any default
        if field in mapping:
            return

        # Field already set, we don't want to override with a default on an update
        if self.is_update_operation and field in self.persisted_document:
            return

        # If we reach here we are processing a field that has a default in the schema
        # and the request doesn't explicitly set it. So we are in one of this cases:
        #
        #   - An initial POST
        #   - A PATCH to an existing document where the field is not set
        #   - A PUT to a document where the field maybe is set

        super()._normalize_default(mapping, schema, field)

    def _normalize_default_setter(self, mapping, schema, field):
        """{'oneof': [
        {'type': 'callable'},
        {'type': 'string'}
        ]}"""
        if not self.persisted_document or field not in self.persisted_document:
            super()._normalize_default_setter(mapping, schema, field)

    def _validate_dependencies(self, dependencies, field, value):
        """{'type': ['dict', 'hashable', 'list']}"""
        persisted = self._filter_persisted_fields_not_in_document(dependencies)
        if persisted:
            dcopy = copy.copy(self.document)
            for field in persisted:
                dcopy[field] = self.persisted_document[field]
            validator = self._get_child_validator()
            validator.validate(dcopy, update=self.update)
            self._error(validator._errors)
        else:
            super()._validate_dependencies(dependencies, field, value)

    def _filter_persisted_fields_not_in_document(self, fields):
        def persisted_but_not_in_document(field):
            return (
                field not in self.document
                and self.persisted_document
                and field in self.persisted_document
            )

        return [field for field in fields if persisted_but_not_in_document(field)]

    def _validate_readonly(self, read_only, field, value):
        """{'type': 'boolean'}"""
        persisted_value = (
            self.persisted_document.get(field) if self.persisted_document else None
        )
        if value != persisted_value:
            super()._validate_readonly(read_only, field, value)

    @property
    def resource(self):
        return self._config.get("resource", None)

    @resource.setter
    def resource(self, value):
        self._config["resource"] = value

    @property
    def document_id(self):
        return self._config.get("document_id", None)

    @document_id.setter
    def document_id(self, value):
        self._config["document_id"] = value

    @property
    def persisted_document(self):
        return self._config.get("persisted_document", None)

    @persisted_document.setter
    def persisted_document(self, value):
        self._config["persisted_document"] = value


class SingleErrorAsStringErrorHandler(cerberus.errors.BasicErrorHandler):
    """Default Cerberus error handler for Eve.

    Since Cerberus 1.0, error messages for fields will always be returned as
    lists, even in the case of a single error. To maintain compatibility with
    clients, this error handler will unpack single-element error lists unless
    the config item VALIDATION_ERROR_AS_LIST is True.
    """

    @property
    def pretty_tree(self):
        pretty = super().pretty_tree
        self._unpack_single_element_lists(pretty)
        return pretty

    def _unpack_single_element_lists(self, tree):
        for field in tree:
            error_list = tree[field]
            if len(error_list) > 0 and isinstance(tree[field][-1], dict):
                self._unpack_single_element_lists(tree[field][-1])
            if len(tree[field]) == 1:
                tree[field] = tree[field][0]
