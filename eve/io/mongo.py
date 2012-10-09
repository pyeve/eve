import ast
from eve import ID_FIELD, LAST_UPDATED
from eve.utils import config
import jsondatetime as json
from base import DataLayer
from flask.ext.pymongo import PyMongo
from bson import ObjectId


class Mongo(DataLayer):

    def init_app(self, app):
        # mongod must be running or this will raise an exception
        self.driver = PyMongo(app)

    def find(self, resource, req):
        args = dict()

        args['limit'] = req.max_results

        if req.page > 1:
            args['skip'] = (req.page - 1) * req.max_results

        if req.sort:
            args['sort'] = ast.literal_eval(req.sort)

        spec = dict()
        if req.where:
            spec = json.loads(req.where)

        if req.if_modified_since:
            spec[config.LAST_UPDATED] = \
                {'$gt': req.if_modified_since}

        if len(spec) > 0:
            args['spec'] = spec

        cursor = self.driver.db[resource].find(**args)
        for document in cursor:
            self.fix_last_updated(document)
            yield document

    def find_one(self, resource, **lookup):
        try:
            if config.ID_FIELD in lookup:
                lookup[ID_FIELD] = ObjectId(lookup[ID_FIELD])
        except:
            pass
        document = self.driver.db[resource].find_one(lookup)
        if document:
            self.fix_last_updated(document)
        return document

    def insert(self, resource, document):
        return  self.driver.db[resource].insert(document)

    def update(self, resource, id_, updates):
        return self.driver.db[resource].update({ID_FIELD: ObjectId(id_)},
                                               {"$set": updates})

    def remove(self, resource, id_):
        return self.driver.db[resource].remove({ID_FIELD: ObjectId(id_)})

    def fix_last_updated(self, document):
        # flask-pymongo returns timezone-aware values, we strip it out
        # because std lib datetime doesn't provide that and comparisions
        # between the two values would fail
        if document.get(LAST_UPDATED):
            document[LAST_UPDATED] = document[LAST_UPDATED].replace(
                tzinfo=None)
