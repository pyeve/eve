# -*- coding: utf-8 -*-

"""
    eve.io.sql.sql (eve.io.sql)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The actual implementation of the SQLAlchemy data layer.

    :copyright: (c) 2013 by Tomasz Jezierski (Tefnet)
    :license: BSD, see LICENSE for more details.
"""

import copy
import ast
import simplejson as json
from flask import abort
import flask.ext.sqlalchemy as flask_sqlalchemy
from datetime import datetime
from parser import parse, ParseError, sqla_op
from eve.io.base import DataLayer, ConnectionException
from eve.utils import config
from .structures import SQLAResult, SQLAResultCollection
from .utils import dict_update, validate_filters

db = flask_sqlalchemy.SQLAlchemy()
object_mapper = flask_sqlalchemy.sqlalchemy.orm.object_mapper
class_mapper = flask_sqlalchemy.sqlalchemy.orm.class_mapper


class SQLAJSONDecoder(json.JSONDecoder):
    def decode(self, s):
        # Turn RFC-1123 strings into datetime values.
        rv = super(SQLAJSONDecoder, self).decode(s)
        try:
            key, val = rv.iteritems().next()
            return dict(key=datetime.strptime(val, config.DATE_FORMAT))
        except:
            return rv


class SQL(DataLayer):
    """
    SQLAlchemy data access layer for Eve REST API.
    """
    json_decoder_cls = SQLAJSONDecoder
    driver = db

    def init_app(self, app):
        try:
            self.driver = db  # FIXME: dumb double initialisation of the driver because Eve sets it to None in __init__
            self.driver.app = app
            self.driver.init_app(app)
        except Exception, e:
            raise ConnectionException(e)

    @classmethod
    def lookup_model(cls, model_name):
        """Lookup SQLAlchemy model class by its name
        :param model_name: Name of SQLAlchemy model.
        """
        return cls.driver.Model._decl_class_registry[model_name.capitalize()]

    @classmethod
    def register_schema(cls, app, model_name=None):
        """Register eve schema for SQLAlchemy model(s)
        :param app: Flask application instance.
        :param model_name: Name of SQLAlchemy model (register all models
         if not provided)
        """
        if model_name:
            models = {model_name.capitalize(): cls.driver.Model._decl_class_registry[model_name.capitalize()]}
        else:
            models = cls.driver.Model._decl_class_registry

        for model_name, model_cls in models.iteritems():
            if model_name.startswith('_'):
                continue
            if getattr(model_cls, '_eve_schema', None):
                dict_update(app.config['DOMAIN'], model_cls._eve_schema)

    def find(self, resource, req, sub_resource_lookup):
        """Retrieves a set of documents matching a given request. Queries can
        be expressed in two different formats: the mongo query syntax, and the
        python syntax. The first kind of query would look like: ::

            ?where={"name": "john doe}

        while the second would look like: ::

            ?where=name=="john doe"

        The resultset if paginated.

        :param resource: resource name.
        :param req: a :class:`ParsedRequest`instance.
        """
        args = {
            'sort': ast.literal_eval(req.sort) if req.sort else None
        }

        client_projection = self._client_projection(req)
        datasource, args['spec'], fields, args['sort'] = self._datasource_ex(resource, [],
                                                                             client_projection, args['sort'])
        model = self.lookup_model(datasource)
        if req.where:
            try:
                args['spec'] = self.combine_queries(args['spec'], parse(req.where, model))
            except ParseError:
                abort(400)

        bad_filter = validate_filters(args['spec'], resource)
        if bad_filter:
            abort(400, bad_filter)

        # TODO: actually use the sub_resource_lookup
        # if sub_resource_lookup:
        #     spec.update(sub_resource_lookup)

        if req.if_modified_since:
            updated_filter = sqla_op.gt(getattr(model, config.LAST_UPDATED),
                                        req.if_modified_since)
            args['spec'].append(updated_filter)

        query = self.driver.session.query(model)

        if args['sort']:
            ql = []
            for sort_item in args['sort']:
                ql.append(getattr(model, sort_item[0]) if sort_item[1] == 1 else
                          getattr(model, sort_item[0]).desc())
            args['sort'] = ql

        if req.max_results:
            args['max_results'] = req.max_results
        if req.page > 1:
            args['page'] = req.page

        return SQLAResultCollection(query, fields, **args)

    def find_one(self, resource, req, **lookup):
        # self._mongotize(lookup, resource)

        client_projection = self._client_projection(req)

        datasource, filter_, fields, _ = self._datasource_ex(resource, lookup, client_projection)
        model = self.lookup_model(datasource)
        query = self.driver.session.query(model)

        return SQLAResult(query.filter_by(**filter_).one(), fields)

    def insert(self, resource, doc_or_docs):
        """Inserts a document into a resource collection.
        """
        # rv = []
        # datasource, filter_, _ = self._datasource_ex(resource)
        # model = self.lookup_model(datasource)
        # for document in doc_or_docs:
        #     sqla_document = copy.deepcopy(document)
        #     # remove date if model doesn't have LAST_UPDATED or DATE_CREATED
        #     if not hasattr(model, config.LAST_UPDATED) and \
        #        config.LAST_UPDATED in sqla_document:
        #         del sqla_document[config.LAST_UPDATED]
        #
        #     if not hasattr(model, config.DATE_CREATED) and \
        #        config.DATE_CREATED in sqla_document:
        #         del sqla_document[config.DATE_CREATED]
        #     model_instance = model(**sqla_document)
        #     self.driver.session.add(model_instance)
        #     self.driver.session.commit()
        #     mapper = self.driver.object_mapper(model_instance)
        #     pkey = mapper.primary_key_from_instance(model_instance)
        #     if len(pkey) > 1:
        #         raise ValueError  # TODO: composite primary key
        #     rv.append(pkey[0])
        # return rv
        raise NotImplementedError  # TODO: bring forward the previous implementation to the new changes

    def update(self, resource, id_, updates):
        raise NotImplementedError  # TODO: update support

    def remove(self, resource, id_=None):
        raise NotImplementedError  # TODO: remove support

    def _datasource(self, resource):
        source = copy.copy(config.SOURCES[resource]['source'])
        model = self.lookup_model(source)
        filter_ = config.SOURCES[resource]['filter']
        if isinstance(filter_,(str, unicode)) and len(filter_):
            filter_ = parse(filter_, model)
        else:
            filter_ = []
        projection = copy.copy(config.SOURCES[resource]['projection'])
        sort = copy.copy(config.SOURCES[resource]['default_sort'])
        return source, filter_, projection, sort,

    def _datasource_ex(self, resource, query=None, client_projection=None,
                       client_sort=None):
        datasource, spec, fields_, sort = super(SQL, self)._datasource_ex(resource, query,
                                                                          client_projection, client_sort)
        model = self.lookup_model(datasource)
        if len(fields_) == 0:
            fields = [prop.key for prop in class_mapper(model).iterate_properties]
        else:
            if fields_.values()[0] == 0:
                fields = [prop.key for prop in class_mapper(model).iterate_properties
                          if prop.key not in fields_]
            else:
                fields = [prop.key for prop in class_mapper(model).iterate_properties
                          if prop.key.startswith('_') or prop.key in fields_]
        return datasource, spec, fields, sort

    def combine_queries(self, query_a, query_b):
        # TODO: dumb concatenation of query lists. We really need to check for duplicate queries
        query_a.extend(query_b)
        return query_a

    def is_empty(self, resource):
        datasource, filter_, _, _ = self._datasource(resource)
        model = self.lookup_model(datasource)
        query = self.driver.session.query(model)
        if len(filter_):
            return query.filter_by(*filter_).count() == 0
        else:
            return query.count() == 0