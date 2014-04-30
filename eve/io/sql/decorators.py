import flask.ext.sqlalchemy as flask_sqlalchemy

from sqlalchemy.ext import hybrid
from sqlalchemy.orm.attributes import InstrumentedAttribute
from eve.utils import config
from .utils import dict_update


__all__ = ['registerSchema']


sqla_type_mapping = {flask_sqlalchemy.sqlalchemy.types.Integer: 'integer',
                     flask_sqlalchemy.sqlalchemy.types.Float: 'float',
                     flask_sqlalchemy.sqlalchemy.types.Boolean: 'boolean',
                     flask_sqlalchemy.sqlalchemy.types.Date: 'datetime',
                     flask_sqlalchemy.sqlalchemy.types.DateTime: 'datetime',
                     flask_sqlalchemy.sqlalchemy.types.DATETIME: 'datetime'}
                     # TODO: Add the remaining sensible SQL types


def lookup_column_type(intype):
    for sqla_type, api_type in sqla_type_mapping.items():
        if isinstance(intype, sqla_type):
            return api_type
    return 'string'


class registerSchema(object):
    """
    Class decorator that scans a SQLAlchemy Base class, prepare an eve schema
    and attach it to the class attributes.
    """

    def __init__(self, resource=None, **kwargs):
        self.resource = resource

    def __call__(self, cls_):
        resource = self.resource or cls_.__name__.lower()

        domain = {
            resource: {
                'schema': {},
                'datasource': {'source': cls_.__name__},
                'item_lookup': True,
                'item_lookup_field': '_id',  # TODO: Make these respect the ID_FIELD config of Eve
                'item_url': 'regex("[0-9]+")'
            }
        }
        projection = domain[resource]['datasource']['projection'] = {}

        if hasattr(cls_, '_eve_resource'):
            dict_update(domain[resource], cls_._eve_resource)

        for desc in flask_sqlalchemy.sqlalchemy.inspect(cls_).all_orm_descriptors:

            if isinstance(desc, InstrumentedAttribute):
                prop = desc.property
                if prop.key in (config.LAST_UPDATED, config.DATE_CREATED):
                    continue
                schema = domain[resource]['schema'][prop.key] = {}
                self.register_column(prop, schema, projection)

            elif desc.extension_type is hybrid.HYBRID_PROPERTY:
                schema = domain[resource]['schema'][desc.__name__] = {}
                schema['unique'] = False
                schema['required'] = False
                schema['type'] = 'string'
                projection[desc.__name__] = 1

        cls_._eve_schema = domain
        return cls_

    @staticmethod
    def register_column(prop, schema, projection):
        if hasattr(prop, 'collection_class'):
            if hasattr(prop.target, 'name'):
                schema['data_relation'] = {'resource': prop.target.name, 'embeddable': True}
                schema['type'] = 'objectid'
                projection[prop.key] = 0
        else:
            col = prop.columns[0]
            projection[prop.key] = 1
            if isinstance(col, flask_sqlalchemy.sqlalchemy.schema.Column):
                if col.nullable:
                    schema['nullable'] = True
                schema['type'] = lookup_column_type(col.type)
                schema['unique'] = col.primary_key or col.unique or False
                schema['required'] = not col.nullable if not col.primary_key else False
                if hasattr(col.type, 'length') and col.type.length:
                    schema['maxlength'] = col.type.length
                if col.default is not None and hasattr(col.default, 'arg'):
                    schema['default'] = col.default.arg
                    col.default = None
            elif isinstance(col, flask_sqlalchemy.sqlalchemy.sql.expression.ColumnElement):
                schema['type'] = lookup_column_type(col.type)
            else:
                schema['type'] = 'string'
            if col.foreign_keys:
                # Unfortunately SQLAlchemy foreign_keys for a column is a set which does not offer indexing
                # Hence we have to first pop the element, get what we want from it and put it back at the end
                foreign_key = col.foreign_keys.pop()
                schema['type'] = 'objectid'
                schema['data_relation'] = {'resource': foreign_key.column.table.name, 'embeddable': False}
                col.foreign_keys.add(foreign_key)
