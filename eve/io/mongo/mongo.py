from eve import ID_FIELD
from eve.utils import config
import ast
import jsondatetime as json
from ..base import DataLayer
from flask import abort
from flask.ext.pymongo import PyMongo
from bson import ObjectId
from parser import parse, ParseError


class Mongo(DataLayer):

    def init_app(self, app):
        # mongod must be running or this will raise an exception
        self.driver = PyMongo(app)

    def find(self, resource, req):
        args = dict()

        args['limit'] = req.max_results

        if req.page > 1:
            args['skip'] = (req.page - 1) * req.max_results

        # TODO sort syntax must be coherent with 'where': either mongo-like
        # or 'canonical' (see 'where' below)

        # TODO should validate on unknown sort fields (mongo driver doesn't
        # return an error, it just ignores the command)
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
        return  self.driver.db[resource].insert(document)

    def update(self, resource, id_, updates):
        return self.driver.db[resource].update({ID_FIELD: ObjectId(id_)},
                                               {"$set": updates})

    def remove(self, resource, id_):
        return self.driver.db[resource].remove({ID_FIELD: ObjectId(id_)})
