import flask.ext.sqlalchemy as flask_sqlalchemy
from eve.utils import config
from .utils import dict_update


__all__ = ['registerSchema']


class registerSchema(object):
    """
    Class decorator that scans a Flask-SQLAlchemy db.Model class, prepare an eve schema
    and attach it to the class attributes.
    """

    sqla_type_mapping = {
        flask_sqlalchemy.sqlalchemy.types.Integer: 'integer',
    }

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

        if hasattr(cls_, '_eve_resource'):
            dict_update(domain[resource], cls_._eve_resource)

        for prop in cls_.__mapper__.iterate_properties:
            if prop.key in (config.LAST_UPDATED, config.DATE_CREATED):
                continue
            schema = domain[resource]['schema'][prop.key] = {}
            if len(prop.columns) > 1:
                raise NotImplementedError  # Composite column property
            elif len(prop.columns) == 1:
                col = prop.columns[0]
                if isinstance(col, flask_sqlalchemy.sqlalchemy.schema.Column):
                    schema['type'] = self.lookupColumnType(col.type)
                    schema['unique'] = col.primary_key or col.unique or False
                    schema['required'] = not col.nullable if not col.primary_key else False
                    if hasattr(col.type, 'length'):
                        schema['maxlength'] = col.type.length
                elif isinstance(col, flask_sqlalchemy.sqlalchemy.sql.expression.ColumnElement):
                    schema['type'] = 'string'
                    # TODO Can we do something more here?
                else:
                    schema['type'] = 'string'

        cls_._eve_schema = domain
        return cls_

    def lookupColumnType(self, intype):
        for sqla_type, api_type in self.sqla_type_mapping.iteritems():
            if isinstance(intype, sqla_type):
                return api_type
        return 'string'
