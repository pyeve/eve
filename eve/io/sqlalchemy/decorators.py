import collections

import flask.ext.sqlalchemy as flask_sqlalchemy

__all__ = ['registerSchema']

def dict_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = dict_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d

class registerSchema(object):
    sqla_type_mapping = {
        flask_sqlalchemy.sqlalchemy.types.Integer: 'integer',
    }
    def __init__(self, resource=None, **kwargs):
        self.resource = resource

    def __call__(self, cls_):
        # FIXME: avoid multiple execution of decorator (metaclass?)
        if hasattr(cls_, '_eve_schema'):
            return cls_

        resource = self.resource or cls_.__name__.lower()
        domain = {
                    resource: {
                        'schema': {}
                    }
        }

        for prop in cls_.__mapper__.iterate_properties:
            schema = domain[resource]['schema'][prop.key] = {}
            if len(prop.columns) > 1:
                # Composite column property
                raise NotImplementedError
            elif len(prop.columns) == 1:
                col = prop.columns[0]
                if isinstance(col, flask_sqlalchemy.sqlalchemy.schema.Column):
                    schema['type'] = self.lookupColumnType(col)
                    schema['unique'] = col.primary_key or col.unique or False
                    schema['required'] = not col.nullable
                    if hasattr(col.type, 'length'):
                        schema['maxlength'] = col.type.length
                elif isinstance(col, flask_sqlalchemy.sqlalchemy.sql.expression.ColumnElement):
                    schema['type'] = 'string'
                    # FIXME Can we do something more here?
                else:
                    schema['type'] = 'string'

        cls_._eve_schema = domain
        self
        # TODO what's next? how to register in config
        return cls_
                
    def lookupColumnType(self, intype):
        for sqla_type, api_type in self.sqla_type_mapping.iteritems():
            if isinstance(intype, sqla_type):
                return api_type
        return 'string'
