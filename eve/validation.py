import sys
import flask
from datetime import datetime
from eve import ID_FIELD
from bson import ObjectId

if sys.version_info[0] == 3:
    _str_type = str
    _int_types = (int,)
else:
    _str_type = basestring
    _int_types = (int, long)


class ValidationError(Exception):
    pass


class DictValidator(object):
    def __init__(self, schema):
        self.schema = schema

    def validate_update(self, document):
        return self._validate(document, insert=False)

    def validate(self, document):
        return self._validate(document, insert=True)

    def _validate(self, document, insert):

        self.errors = list()
        self.insert = insert

        if self.schema is None:
            raise ValidationError('validation schema missing.')

        if document:
            self.document = document

        if self.document is None:
            raise ValidationError('document to be validated is missing.')
        elif not isinstance(self.document, dict):
            raise ValidationError('document must be a dict.')
        else:
            for field, value in self.document.items():

                definition = self.schema.get(field)
                if definition:
                    for rule in definition.keys():
                        validatorname = "_validate_" + rule.replace(" ", "_")
                        validator = getattr(self, validatorname, None)
                        if validator:
                            validator(definition[rule], field, value)
                else:
                    self._error("unknown field '%s'" % field)

            if self.insert:
                self._validate_required_fields()

        return len(self.errors) == 0

    def _error(self, _error):
        if isinstance(_error, _str_type):
            self.errors.append(_error)
        else:
            self.errors.extend(_error)

    def _validate_required_fields(self):
        required = list(field for field, definition in self.schema.items()
                        if definition.get('required') is True)
        missing = set(required) - set(self.document.keys())
        if len(missing):
            self._error("required field(s) are missing: %s" %
                        ', '.join(missing))

    def _validate_readonly(self, read_only, field, value):
        if read_only:
            self._error("field '%s' is read-only" % field)

    def _validate_type(self, data_type, field, value):
        validator = getattr(self, "_validate_type_" + data_type, None)
        if validator:
            validator(field, value)
        else:
            self._error("unrecognized data-type '%s' for field '%s'" %
                       (data_type, field))

    def _validate_type_string(self, field, value):
        if not isinstance(value, _str_type):
            self._error("value of field '%s' must be of string type" % field)

    def _validate_type_integer(self, field, value):
        if not isinstance(value, _int_types):
            self._error("value of field '%s' must be of integer type" % field)

    def _validate_type_boolean(self, field, value):
        if not isinstance(value, bool):
            self._error("value of field '%s' must be of boolean type" % field)

    def _validate_type_array(self, field, value):
        if not isinstance(value, list):
            self._error("value for field '%s' must be of array (list) type" %
                        field)

    def _validate_type_datetime(self, field, value):
        if not isinstance(value, datetime):
            self._error("value of field '%s' must be a datetime" % field)

    def _validate_type_dict(self, field, value):
        if not isinstance(value, dict):
            self._error("value for field '%s' must be of dict type" %
                        field)

    def _validate_type_list(self, field, value):
        if not isinstance(value, list):
            self._error("value for field '%s' must be of list type" %
                        field)

    def _validate_maxlength(self, max_length, field, value):
        if isinstance(value, _str_type):
            if len(value) > max_length:
                self._error("max length for field '%s' is %d" %
                           (field, max_length))

    def _validate_minlength(self, min_length, field, value):
        if isinstance(value, _str_type):
            if len(value) < min_length:
                self._error("min length for field '%s' is %d" %
                           (field, min_length))

    def _validate_allowed(self, allowed_values, field, value):
        if isinstance(value, list):
            disallowed = set(value) - set(allowed_values)
            if disallowed:
                self._error("unallowed values %s for field '%s'" %
                            (list(disallowed), field))

    def _validate_schema(self, schema, field, value):
        validator = Validator(schema)
        if not validator.validate(value):
            self._error(["'%s': " % field + error
                         for error in validator.errors])

    def _validate_items(self, items, field, value):
        if isinstance(items, dict):
            self._validate_items_schema(items, field, value)
        elif isinstance(items, list):
            self._validate_items_list(items, field, value)

    def _validate_items_list(self, schemas, field, values):
        if len(schemas) != len(values):
            self._error("'%s': length of list should be %d" %
                        (field, len(schemas)))
        else:
            for i in range(len(schemas)):
                key = "_data" + str(i)
                validator = Validator({key: schemas[i]})
                if not validator.validate({key: values[i]}):
                    self._error(["'%s': " % field + error
                                for error in validator.errors])

    def _validate_items_schema(self, schema, field, value):
        validator = Validator(schema)
        for item in value:
            if not validator.validate(item):
                self._error(["'%s': " % field + error
                            for error in validator.errors])


class Validator(DictValidator):
    # TODO validate VAT, CIN, etc.
    def __init__(self, schema, resource):
        self.resource = resource
        super(Validator, self).__init__(schema)

    def validate_update(self, document, object_id):
        self.object_id = object_id
        return super(Validator, self).validate_update(document)

    def _validate_unique(self, unique, field, value):
        if unique:
            query = {field: value}
            if self.object_id:
                query[ID_FIELD] = {'$ne': ObjectId(self.object_id)}

            if flask.current_app.data.find_one(self.resource, **query):
                self._error("value '%s' for field '%s' not unique" %
                            (value, field))
