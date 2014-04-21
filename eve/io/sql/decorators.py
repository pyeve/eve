import flask.ext.sqlalchemy as flask_sqlalchemy
from eve.utils import config
from .utils import dict_update


__all__ = ['registerSchema']


sqla_type_mapping = {flask_sqlalchemy.sqlalchemy.types.Integer: 'integer'}


def lookup_column_type(intype):
    for sqla_type, api_type in sqla_type_mapping.iteritems():
        if isinstance(intype, sqla_type):
            return api_type
    return 'string'


class registerSchema(object):
    """
    Class decorator that scans a Flask-SQLAlchemy db.Model class, prepare an eve schema
    and attach it to the class attributes.
    """

    def __init__(self, resource=None, **kwargs):
        self.resource = resource

    def __call__(self, cls_):
        if hasattr(cls_, '_eve_schema'):
            return cls_

        resource = self.resource or cls_.__name__.lower()

        domain = {
            resource: {
                'schema': {}
            }
        }

        domain[resource]['item_lookup'] = True

        # Defines the main lookup rules for this resource
        # TODO: Make these respect the ID_FIELD config of Eve
        domain[resource]['item_lookup_field'] = '_id'
        domain[resource]['item_url'] = 'regex("[0-9]+")'

        if hasattr(cls_, '_eve_resource'):
            dict_update(domain[resource], cls_._eve_resource)

        fields = [config.LAST_UPDATED, config.DATE_CREATED]
        for prop in cls_.__mapper__.iterate_properties:
            if prop.key in (config.LAST_UPDATED, config.DATE_CREATED):
                continue
            schema = domain[resource]['schema'][prop.key] = {}
            self.register_column(prop, schema, fields)

        cls_._eve_schema = domain
        cls_._eve_fields = fields
        return cls_

    @staticmethod
    def register_column(prop, schema, fields):
        if len(prop.columns) > 1:
            raise NotImplementedError  # TODO: Composite column property
        elif len(prop.columns) == 1:
            col = prop.columns[0]
            fields.append(prop.key)
            if isinstance(col, flask_sqlalchemy.sqlalchemy.schema.Column):
                schema['type'] = lookup_column_type(col.type)
                schema['unique'] = col.primary_key or col.unique or False
                schema['required'] = not col.nullable if not col.primary_key else False
                if hasattr(col.type, 'length'):
                    schema['maxlength'] = col.type.length
            elif isinstance(col, flask_sqlalchemy.sqlalchemy.sql.expression.ColumnElement):
                schema['type'] = 'string'  # TODO Can we do something more here?
            else:
                schema['type'] = 'string'
            if col.foreign_keys:
                # Unfortunately SQLAlchemy foreign_keys for a column is a set which does not offer indexing
                # Hence we have to first pop the element, get what we want from it and put it back at the end
                foreign_key = col.foreign_keys.pop()
                relation_resource = foreign_key.target_fullname.split('.')[0]
                schema['data_relation'] = {'resource': relation_resource}
                col.foreign_keys.add(foreign_key)
