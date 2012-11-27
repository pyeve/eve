# -*- coding: utf-8 -*-

"""
    eve.io.mongo.mongo (eve.io.mongo)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The actual implementation of the MongoDB data layer.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import ast
import jsondatetime as json
from flask import abort
from flask.ext.pymongo import PyMongo
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
        """
        args = dict()

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

        spec = dict()
        if req.where:
            try:
                spec = json.loads(req.where)
            except:
                try:
                    spec = parse(req.where)
                except ParseError:
                    abort(400)

        if req.if_modified_since:
            spec[config.LAST_UPDATED] = \
                {'$gt': req.if_modified_since}

        if len(spec) > 0:
            args['spec'] = spec

        return self.driver.db[resource].find(**args)

    def find_one(self, resource, **lookup):
        """Retrieves a single document.

        :param resource: resource name.
        :param **lookup: lookup query.
        """
        try:
            if config.ID_FIELD in lookup:
                lookup[ID_FIELD] = ObjectId(lookup[ID_FIELD])
        except:
            pass
        document = self.driver.db[resource].find_one(lookup)
        #if document:
        #    self.fix_last_updated(document)
        return document

    def insert(self, resource, document):
        """Inserts a document into a resource collection.
        """
        return  self.driver.db[resource].insert(document)

    def update(self, resource, id_, updates):
        """Updates a collection document.
        """
        return self.driver.db[resource].update({ID_FIELD: ObjectId(id_)},
                                               {"$set": updates})

    def remove(self, resource, id_=None):
        """Removes a document or the entire set of documents from a collection.

        .. versionadded:: 0.0.2
            Support for deletion of entire documents collection.
        """
        if id_:
            return self.driver.db[resource].remove({ID_FIELD: ObjectId(id_)})
        else:
            # this will delete all documents in a collection!
            return self.driver.db[resource].remove()
