# -*- coding: utf-8 -*-

"""
    eve.io.sqlalchemy.sqlalchemy (eve.io.sqlalchemy)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The actual implementation of the SQLAlchemy data layer.

    :copyright: (c) 2013 by Tomasz Jezierski (Tefnet)
    :license: BSD, see LICENSE for more details.
"""

import collections
import copy
import ast
import simplejson as json
from flask import abort, request
import flask.ext.sqlalchemy as flask_sqlalchemy
from datetime import datetime
from parser import parse, ParseError
from eve.io.base import DataLayer, ConnectionException
from eve.utils import config

from .utils import dict_update

db = flask_sqlalchemy.SQLAlchemy()
object_mapper = flask_sqlalchemy.sqlalchemy.orm.object_mapper


class SQLAJSONDecoder(json.JSONDecoder):
    def decode(self, s):
        # Turn RFC-1123 strings into datetime values.
        rv = super(SQLAJSONDecoder, self).decode(s)
        try:
            key, val = rv.iteritems().next()
            return dict(key=datetime.strptime(val, config.DATE_FORMAT))
        except:
            return rv


class SQLAResult(collections.MutableMapping):
    def __init__(self, result):
        self._result = result

    def __getitem__(self, key):
        if key == config.ID_FIELD:
            pkey = self._get_pkey()
            if len(pkey) > 1:
                raise ValueError  # TODO: composite primary key
            return pkey[0]
        return getattr(self._result, key)

    def __setitem__(self, key, value):
        setattr(self._result, key, value)

    def __contains__(self, key):
        return key in self.keys()

    def __delitem__(self, key):
        pass

    def __iter__(self):
        for k in self.keys():
            yield k

    def __len__(self):
        return len(self.keys())

    def keys(self):
        return [
            prop.key for prop in object_mapper(self._result).iterate_properties
        ]

    def _asdict(self):
        return dict(self)

    def _get_pkey(self):
        mapper = object_mapper(self._result)
        return mapper.primary_key_from_instance(self._result)


class SQLAResultCollection(object):
    result_item_cls = SQLAResult

    def __init__(self, cursor):
        self._cursor = cursor

    def __iter__(self):
        for i in self._cursor:
            yield SQLAResult(i)

    def count(self):
        return self._cursor.count()


class SQLAlchemy(DataLayer):
    """ SQLAlchemy data access layer for Eve REST API.
    """
    json_decoder_cls = SQLAJSONDecoder
    driver = db

    def init_app(self, app):
        try:
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
            models = [
                model_name,
                cls.driver.Model._decl_class_registry[model_name.capitalize()]
            ]
        else:
            models = cls.driver.Model._decl_class_registry

        for model_name, model_cls in models.iteritems():
            if model_name.startswith('_'):
                continue
            if getattr(model_cls, '_eve_schema', None):
                dict_update(app.config['DOMAIN'], model_cls._eve_schema)

    def find(self, resource, req):
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

        spec = {}
        fields = {}

        if req.projection:
            try:
                fields = json.loads(req.projection)
            except:
                abort(400)

        datasource, spec, fields = self._datasource_ex(resource, spec, fields)
        model = self.lookup_model(datasource)

        if req.where:
            try:
                spec = parse(req.where, model)
            except ParseError:
                abort(400)

        # TODO
        #if req.if_modified_since:
        #    spec[config.LAST_UPDATED] = \
        #        {'$gt': req.if_modified_since}

        # TODO
        #if fields:
        #    pass

        query = self.driver.session.query(model)
        if spec:
            query = query.filter(*spec)

        if req.sort:
            ql = []
            for key, asc in ast.literal_eval(req.sort).iteritems():
                ql.append(
                    getattr(model, key) \
                    if asc == 1 \
                     else getattr(model, key).desc()
                )
            query = query.order_by(*ql)

        if req.max_results:
            query = query.limit(req.max_results)
        if req.page > 1:
            query = query.offset((req.page - 1) * req.max_results)

        return SQLAResultCollection(query)

    def find_one(self, resource, **lookup):
        """Retrieves a single document.

        :param resource: resource name.
        :param **lookup: lookup query.
        """
        datasource, filter_, _ = self._datasource_ex(resource, lookup)
        model = self.lookup_model(datasource)
        query = self.driver.session.query(model)

        return SQLAResult(query.filter_by(**filter_).one())

    def insert(self, resource, doc_or_docs):
        """Inserts a document into a resource collection.
        """
        rv = []
        datasource, filter_, _ = self._datasource_ex(resource)
        model = self.lookup_model(datasource)
        for document in doc_or_docs:
            sqla_document = copy.deepcopy(document)
            # remove date if model doesn't have LAST_UPDATED or DATE_CREATED
            if not hasattr(model, config.LAST_UPDATED) and \
               config.LAST_UPDATED in sqla_document:
                del sqla_document[config.LAST_UPDATED]

            if not hasattr(model, config.DATE_CREATED) and \
               config.DATE_CREATED in sqla_document:
                del sqla_document[config.DATE_CREATED]
            model_instance = model(**sqla_document)
            self.driver.session.add(model_instance)
            self.driver.session.commit()
            mapper = self.driver.object_mapper(model_instance)
            pkey = mapper.primary_key_from_instance(model_instance)
            if len(pkey) > 1:
                raise ValueError  # TODO: composite primary key
            rv.append(pkey[0])
        return rv

    def update(self, resource, id_, updates):
        """Updates a collection document.
        """
        raise NotImplementedError
        # TODO update support

    def remove(self, resource, id_=None):
        """Removes a document or the entire set of documents from a collection.
        """
        raise NotImplementedError

    def _datasource_ex(self, resource, query=None, fields=None):
        """ Returns both db collection and exact query (base filter included)
        to which an API resource refers to
        """

        datasource, filter_, projection_ = self._datasource(resource)
        if filter_:
            if query:
                query.update(filter_)
            else:
                query = filter_

        if projection_:
            if fields:
                fields.update(projection_)
            else:
                fields = projection_

        # if 'user-restricted resource access' is enabled and there's an Auth
        # request active, add the username field to the query
        username_field = config.DOMAIN[resource].get('auth_username_field')
        if username_field and request.authorization and query:
            query.update({username_field: request.authorization.username})

        return datasource, query, fields
