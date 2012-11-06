from flask import current_app as app
from cerberus import Validator, ValidationError, SchemaError
from eve import ID_FIELD
from bson import ObjectId


class Validator(Validator):
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

            if app.data.find_one(self.resource, **query):
                self._error("value '%s' for field '%s' not unique" %
                            (value, field))
