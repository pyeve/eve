# -*- coding: utf-8 -*-

"""
    eve.io.mongo.mongo (eve.io.mongo)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The actual implementation of the MongoDB data layer.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import ast
import simplejson as json
from flask import abort
from flask.ext.pymongo import PyMongo
from datetime import datetime
from bson import ObjectId
from parser import parse, ParseError
from eve.io.base import DataLayer, ConnectionException
from eve import ID_FIELD
from eve.utils import config


class Mongo(DataLayer):
    """ MongoDB data access layer for Eve REST API.
    """

    def init_app(self, app):
        # mongod must be running or this will raise an exception
        try:
            self.driver = PyMongo(app)
        except Exception, e:
            raise ConnectionException(e)

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

        .. versionchanged:: 0.0.7
           Abort with a 400 if the query includes blacklisted  operators.

        .. versionchanged:: 0.0.6
           Only retrieve fields in the resource schema
           Support for projection queries ('?projection={"name": 1}')

        .. versionchanged:: 0.0.5
           handles the case where req.max_results is None because pagination
           has been disabled.

        .. versionchanged:: 0.0.4
           retrieves the target collection via the new config.SOURCES helper.
        """
        args = dict()

        if req.max_results:
            args['limit'] = req.max_results

        if req.page > 1:
            args['skip'] = (req.page - 1) * req.max_results

        # TODO sort syntax should probably be coherent with 'where': either
        # mongo-like # or python-like. Currently accepts only mongo-like sort
        # syntax.

        # TODO should validate on unknown sort fields (mongo driver doesn't
        # return an error)
        if req.sort:
            args['sort'] = ast.literal_eval(req.sort)

        client_projection = {}
        spec = {}

        if req.where:
            try:
                spec = self._sanitize(
                    self._jsondatetime(json.loads(req.where)))
            except:
                try:
                    spec = parse(req.where)
                except ParseError:
                    abort(400)

        if req.projection:
            try:
                client_projection = json.loads(req.projection)
            except:
                abort(400)

        datasource, spec, projection = self._datasource_ex(resource, spec,
                                                           client_projection)

        if req.if_modified_since:
            spec[config.LAST_UPDATED] = \
                {'$gt': req.if_modified_since}

        if len(spec) > 0:
            args['spec'] = spec

        if projection is not None:
            args['fields'] = projection

        return self.driver.db[datasource].find(**args)

    def find_one(self, resource, **lookup):
        """Retrieves a single document.

        :param resource: resource name.
        :param **lookup: lookup query.

        .. versionchanged:: 0.0.6
           Only retrieve fields in the resource schema

        .. versionchanged:: 0.0.4
           retrieves the target collection via the new config.SOURCES helper.
        """
        try:
            if config.ID_FIELD in lookup:
                lookup[ID_FIELD] = ObjectId(lookup[ID_FIELD])
        except:
            pass

        datasource, filter_, projection = self._datasource_ex(resource, lookup)
        document = self.driver.db[datasource].find_one(filter_, projection)
        return document

    def insert(self, resource, doc_or_docs):
        """Inserts a document into a resource collection.

        .. versionchanged:: 0.0.6
           projection queries ('?projection={"name": 1}')
           'document' param renamed to 'doc_or_docs', making support for bulk
           inserts apparent.

        .. versionchanged:: 0.0.4
           retrieves the target collection via the new config.SOURCES helper.
        """
        datasource, filter_, _ = self._datasource_ex(resource)
        return self.driver.db[datasource].insert(doc_or_docs)

    def update(self, resource, id_, updates):
        """Updates a collection document.

        .. versionchanged:: 0.0.6
           projection queries ('?projection={"name": 1}')

        .. versionchanged:: 0.0.4
           retrieves the target collection via the new config.SOURCES helper.
        """
        datasource, filter_, _ = self._datasource_ex(resource,
                                                     {ID_FIELD: ObjectId(id_)})

        # TODO consider using find_and_modify() instead. The document might
        # have changed since the ETag was computed. This would require getting
        # the original document as an argument though.

        return self.driver.db[datasource].update(filter_, {"$set": updates})

    def remove(self, resource, id_=None):
        """Removes a document or the entire set of documents from a collection.

        .. versionchanged:: 0.0.6
           projection queries ('?projection={"name": 1}')

        .. versionchanged:: 0.0.4
           retrieves the target collection via the new config.SOURCES helper.

        .. versionadded:: 0.0.2
            Support for deletion of entire documents collection.
        """
        query = {ID_FIELD: ObjectId(id_)} if id_ else None
        datasource, filter_, _ = self._datasource_ex(resource, query)
        return self.driver.db[datasource].remove(filter_)

    def _jsondatetime(self, source):
        """ Recursively iterates a JSON dictionary, turning RFC-1123 strings
        into datetime values.

        .. versionadded:: 0.0.4
        """

        for k, v in source.items():
            if isinstance(v, dict):
                self._jsondatetime(v)
            elif isinstance(v, basestring):
                try:
                    source[k] = datetime.strptime(v, config.DATE_FORMAT)
                except:
                    pass

        return source

    def _sanitize(self, spec):
        """ Makes sure that only allowed operators are included in the query,
        aborts with a 400 otherwise.

        .. versionadded:: 0.0.7
        """
        if set(spec.keys()) & set(config.MONGO_QUERY_BLACKLIST):
            abort(400)
        for value in spec.values():
            if isinstance(value, dict):
                if set(value.keys()) & set(config.MONGO_QUERY_BLACKLIST):
                    abort(400)
        return spec
