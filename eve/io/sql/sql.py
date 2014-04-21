# -*- coding: utf-8 -*-

"""
    eve.io.sql.sql (eve.io.sql)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The actual implementation of the SQLAlchemy data layer.

    :copyright: (c) 2013 by Tomasz Jezierski (Tefnet)
    :license: BSD, see LICENSE for more details.
"""

import ast
import simplejson as json
import flask.ext.sqlalchemy as flask_sqlalchemy
from flask import abort
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime
from copy import copy

from eve.io.base import DataLayer, ConnectionException
from eve.utils import config
from .parser import parse, parse_dictionary, ParseError, sqla_op
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
        except Exception, e:
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
        """
        Lookup SQLAlchemy model class by its name

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
                resource = model_name.lower()
                eve_schema = model_cls._eve_schema
                dict_update(app.config['DOMAIN'], eve_schema)

        for k, v in app.config['DOMAIN'].iteritems():
            if 'datasource' in v and 'source' in v['datasource']:
                source = v['datasource']['source']
                source = app.config['DOMAIN'].get(source)
                if source:
                    v['schema'] = source['schema']
                    v['item_lookup_field'] = source['item_lookup_field']
                    v['item_url'] = source['item_url']

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
        model, args['spec'], fields, args['sort'] = self._datasource_ex(resource, [], client_projection, args['sort'])
        if req.where:
            try:
                args['spec'] = self.combine_queries(args['spec'], parse(req.where, model))
            except ParseError:
                abort(400)

        bad_filter = validate_filters(args['spec'], resource)
        if bad_filter:
            abort(400, bad_filter)

        if sub_resource_lookup:
            args['spec'] = self.combine_queries(args['spec'], parse_dictionary(sub_resource_lookup, model))

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
        client_projection = self._client_projection(req)
        model, filter_, fields, _ = self._datasource_ex(resource, [], client_projection)
        filter_ = self.combine_queries(filter_, parse_dictionary(lookup, model))
        query = self.driver.session.query(model)

        try:
            document = query.filter(*filter_).one()
            return SQLAResult(document, fields)
        except NoResultFound:
            abort(404)

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

    def remove(self, resource, lookup):
        model, filter_, _, _ = self._datasource_ex(resource, [])
        filter_ = self.combine_queries(filter_, parse_dictionary(lookup, model))
        query = self.driver.session.query(model)
        if len(filter_):
            query.filter(*filter_).delete()
        else:
            query.delete()
        self.driver.session.commit()

    @staticmethod
    def _source(resource):
        return config.SOURCES[resource]['source']

    def _model(self, resource):
        return self.lookup_model(self._source(resource))

    def _datasource(self, resource):
        """
        Overridden from super to return the actual model class of the database
        table instead of the name of it
        """
        model = self._model(resource)

        # TODO: check this implementation. Overwriting filter in the global config might be tricky
        filter_ = config.SOURCES[resource]['filter']
        if filter_ is None or len(filter_) == 0:
            filter_ = []
        elif isinstance(filter_, (str, unicode)):
            filter_ = parse(filter_, model)
        elif isinstance(filter_, dict):
            filter_ = parse_dictionary(filter_, model)
        elif not isinstance(filter_, list):
            filter_ = []

        projection_ = copy(config.SOURCES[resource]['projection'])
        sort_ = copy(config.SOURCES[resource]['default_sort'])

        return model, filter_, projection_, sort_

    def _datasource_ex(self, resource, query=None, client_projection=None, client_sort=None):

        model, filter_, fields_, sort_ = super(SQL, self)._datasource_ex(resource, query,
                                                                         client_projection, client_sort)

        if fields_.values()[0] == 0:
            fields = [field for field in model._eve_fields if field not in fields_]
        else:
            fields = [field for field in model._eve_fields if field.startswith('_') or field in fields_]
        return model, filter_, fields, sort_

    def combine_queries(self, query_a, query_b):
        # TODO: dumb concatenation of query lists.
        #       We really need to check for duplicate queries
        query_a.extend(query_b)
        return query_a

    def is_empty(self, resource):
        model, filter_, _, _ = self._datasource(resource)
        query = self.driver.session.query(model)
        if len(filter_):
            return query.filter_by(*filter_).count() == 0
        else:
            return query.count() == 0
