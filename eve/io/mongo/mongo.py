"""
    eve.io.mongo.mongo (eve.io.mongo)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The actual implementation of the MongoDB data layer.

    :copyright: (c) 2013 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import sys
import ast
import itertools
from bson.errors import InvalidId
import simplejson as json
import pymongo
from flask import abort
from flask.ext.pymongo import PyMongo
from bson import ObjectId
from datetime import datetime
from eve import ID_FIELD
from eve.io.mongo.parser import parse, ParseError
from eve.io.base import DataLayer, ConnectionException, BaseJSONEncoder
from eve.utils import config, debug_error_message, validate_filters, \
    str_to_date


class MongoJSONEncoder(BaseJSONEncoder):
    """ Propretary JSONEconder subclass used by the json render function.
    This is needed to address the encoding of special values.

    .. versionadded:: 0.2
    """
    def default(self, obj):
        if isinstance(obj, ObjectId):
            # BSON/Mongo ObjectId is rendered as a string
            return str(obj)
        else:
            # delegate rendering to base class method
            return super(MongoJSONEncoder, self).default(obj)


class Mongo(DataLayer):
    """ MongoDB data access layer for Eve REST API.

    .. versionchanged:: 0.2
       Provide the specialized json serializer class as ``json_encoder_class``.

    .. versionchanged:: 0.1.1
       'serializers' added.
    """

    serializers = {
        'objectid': ObjectId,
        'datetime': str_to_date
    }

    # JSON serializer  s a class attribute. Allows extensions to replace it
    # with their own implementation.
    json_encoder_class = MongoJSONEncoder

    def init_app(self, app):
        """
        .. versionchanged:: 0.0.9
           support for Python 3.3.
        """
        # mongod must be running or this will raise an exception
        try:
            self.driver = PyMongo(app)
        except Exception as e:
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

        .. versionchanged:: 0.1.1
           Better query handling. We're now properly casting objectid-like
           strings to ObjectIds. Also, we're casting both datetimes and
           objectids even when the query was originally in python syntax.

        .. versionchanged:: 0.0.9
           More informative error messages.

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
                spec = self._sanitize(json.loads(req.where))
            except:
                try:
                    spec = parse(req.where)
                except ParseError:
                    abort(400, description=debug_error_message(
                        'Unable to parse `where` clause'
                    ))
            spec = self._mongotize(spec)

        bad_filter = validate_filters(spec, resource)
        if bad_filter:
            abort(400, bad_filter)

        if req.projection:
            try:
                client_projection = json.loads(req.projection)
            except:
                abort(400, description=debug_error_message(
                    'Unable to parse `projection` clause'
                ))

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

        .. versionchanged:: 0.1.0
           ID_FIELD to ObjectID conversion is done before `_datasource_ex` is
           called.

        .. versionchanged:: 0.0.6
           Only retrieve fields in the resource schema

        .. versionchanged:: 0.0.4
           retrieves the target collection via the new config.SOURCES helper.
        """
        if config.ID_FIELD in lookup:
            try:
                lookup[ID_FIELD] = ObjectId(lookup[ID_FIELD])
            except (InvalidId, TypeError):
                # Returns a type error when {'_id': {...}}
                pass

        datasource, filter_, projection = self._datasource_ex(resource, lookup)

        document = self.driver.db[datasource].find_one(filter_, projection)
        return document

    def find_list_of_ids(self, resource, ids, client_projection=None):
        """Retrieves a list of documents from the collection given
        by `resource`, matching the given list of ids.

        This query is generated to *preserve the order* of the elements
        in the `ids` list. An alternative would be to use the `$in` operator
        and accept non-dependable ordering for a slight performance boost
        see <https://jira.mongodb.org/browse/SERVER-7528?focusedCommentId=
        181518&page=com.atlassian.jira.plugin.system.issuetabpanels:comment
        -tabpanel#comment-181518>

        To preserve order, we use a query of the form
            db.collection.find( { $or:[ { _id:ObjectId(...) },
                { _id:ObjectId(...) }...] } )

        Instead of the simpler
            {'_id': {'$in': ids}}

        -- via http://stackoverflow.com/a/13185509/1161906

        :param resource: resource name.
        :param ids: a list of ObjectIds corresponding to the documents
        to retrieve
        :param client_projection: a specific projection to use
        :return: a list of documents matching the ids in `ids` from the
        collection specified in `resource`

        .. versionchanged:: 0.1.1
           Using config.ID_FIELD instead of hard coded '_id'.

        .. versionadded:: 0.1.0
        """
        query = {'$or': [
            {config.ID_FIELD: id_} for id_ in ids
        ]}

        datasource, spec, projection = self._datasource_ex(
            resource, query=query, client_projection=client_projection
        )

        documents = self.driver.db[datasource].find(
            spec=spec, fields=projection
        )
        return documents

    def insert(self, resource, doc_or_docs):
        """Inserts a document into a resource collection.

        .. versionchanged:: 0.0.9
           More informative error messages.

        .. versionchanged:: 0.0.8
           'write_concern' support.

        .. versionchanged:: 0.0.6
           projection queries ('?projection={"name": 1}')
           'document' param renamed to 'doc_or_docs', making support for bulk
           inserts apparent.

        .. versionchanged:: 0.0.4
           retrieves the target collection via the new config.SOURCES helper.
        """
        datasource, _, _ = self._datasource_ex(resource)
        try:
            return self.driver.db[datasource].insert(doc_or_docs,
                                                     **self._wc(resource))
        except pymongo.errors.OperationFailure as e:
            # most likely a 'w' (write_concern) setting which needs an
            # existing ReplicaSet which doesn't exist. Please note that the
            # update will actually succeed (a new ETag will be needed).
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    def update(self, resource, id_, updates):
        """Updates a collection document.

        .. versionchanged:: 0.0.9
           More informative error messages.

        .. versionchanged:: 0.0.8
           'write_concern' support.

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
        try:
            self.driver.db[datasource].update(filter_, {"$set": updates},
                                              **self._wc(resource))
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    def replace(self, resource, id_, document):
        """Replaces an existing document.

        .. versionadded:: 0.1.0
        """
        datasource, filter_, _ = self._datasource_ex(resource,
                                                     {ID_FIELD: ObjectId(id_)})

        # TODO consider using find_and_modify() instead. The document might
        # have changed since the ETag was computed. This would require getting
        # the original document as an argument though.
        try:
            self.driver.db[datasource].update(filter_, document,
                                              **self._wc(resource))
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    def remove(self, resource, id_=None):
        """Removes a document or the entire set of documents from a collection.

        .. versionchanged:: 0.0.9
           More informative error messages.

        .. versionchanged:: 0.0.8
           'write_concern' support.

        .. versionchanged:: 0.0.6
           projection queries ('?projection={"name": 1}')

        .. versionchanged:: 0.0.4
           retrieves the target collection via the new config.SOURCES helper.

        .. versionadded:: 0.0.2
            Support for deletion of entire documents collection.
        """
        query = {ID_FIELD: ObjectId(id_)} if id_ else None
        datasource, filter_, _ = self._datasource_ex(resource, query)
        try:
            self.driver.db[datasource].remove(filter_, **self._wc(resource))
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    # TODO: The next three methods could be pulled out to form the basis
    # of a separate MonqoQuery class

    def combine_queries(self, query_a, query_b):
        """
        Takes two db queries and applies db-specific syntax to produce
        the intersection

        This is used because we can't just dump one set of query operators
        into another.

        Consider for example if the dataset contains a custom datasource
        pattern like --
           'filter': {'username': {'$exists': True}}

        If we simultaneously try to filter on the field `username`,
        then doing
            query_a.update(query_b)
        would lose information.

        This implementation of the function just combines everything in the
        two dicts using the `$and` operator.

        Note that this is exactly same as performing dict.update() except
        when multiple operators are operating on the /same field/.

        Example:
            combine_queries({'username': {'$exists': True}},
                            {'username': 'mike'})
        {'$and': [{'username': {'$exists': True}}, {'username': 'mike'}]}

        .. versionadded: 0.1.0
           Support for intelligent combination of db queries
        """
        # Chain the operations with the $and operator
        return {
            '$and': [
                {k: v} for k, v in itertools.chain(query_a.items(),
                                                   query_b.items())
            ]
        }

    def get_value_from_query(self, query, field_name):
        """ For the specified field name, parses the query and returns
        the value being assigned in the query.

        For example,
            get_value_from_query({'_id': 123}, '_id')
        123

        This mainly exists to deal with more complicated compound queries
            get_value_from_query(
                {'$and': [{'_id': 123}, {'firstname': 'mike'}],
                '_id'
            )
        123

        .. versionadded: 0.1.0
           Support for parsing values embedded in compound db queries
        """
        if field_name in query:
            return query[field_name]
        elif '$and' in query:
            for condition in query['$and']:
                if field_name in condition:
                    return condition[field_name]
        raise KeyError

    def query_contains_field(self, query, field_name):
        """ For the specified field name, does the query contain it?
        Used know whether we need to parse a compound query

        .. versionadded: 0.1.0
           Support for parsing values embedded in compound db queries
        """
        try:
            self.get_value_from_query(query, field_name)
        except KeyError:
            return False
        return True

    def _mongotize(self, source):
        """ Recursively iterates a JSON dictionary, turning RFC-1123 strings
        into datetime values and ObjectId-link strings into ObjectIds.

        .. versionchanged:: 0.1.1
           Renamed from _jsondatetime to _mongotize, as it now handles
           ObjectIds too.

        .. versionchanged:: 0.1.0
           Datetime conversion was failing on Py2, since 0.0.9 :P

        .. versionchanged:: 0.0.9
           support for Python 3.3.

        .. versionadded:: 0.0.4
        """
        if sys.version_info[0] == 3:
            _str_type = str
        else:
            _str_type = basestring  # noqa

        def try_cast(v):
            try:
                return datetime.strptime(v, config.DATE_FORMAT)
            except:
                try:
                    return ObjectId(v)
                except:
                    return v

        for k, v in source.items():
            if isinstance(v, dict):
                self._mongotize(v)
            elif isinstance(v, list):
                i = 0
                for v1 in v:
                    if isinstance(v1, dict):
                        source[k][i] = self._mongotize(v1)
                    else:
                        source[k][i] = try_cast(v1)
                    i += 1
            elif isinstance(v, _str_type):
                source[k] = try_cast(v)

        return source

    def _sanitize(self, spec):
        """ Makes sure that only allowed operators are included in the query,
        aborts with a 400 otherwise.

        .. versionchanged:: 0.0.9
           More informative error messages.
           Allow ``auth_username_field`` to be set to ``ID_FIELD``.

        .. versionadded:: 0.0.7
        """
        if set(spec.keys()) & set(config.MONGO_QUERY_BLACKLIST):
            abort(400, description=debug_error_message(
                'Query contains operators banned in MONGO_QUERY_BLACKLIST'
            ))
        for value in spec.values():
            if isinstance(value, dict):
                if set(value.keys()) & set(config.MONGO_QUERY_BLACKLIST):
                    abort(400, description=debug_error_message(
                        'Query contains operators banned '
                        'in MONGO_QUERY_BLACKLIST'
                    ))
        return spec

    def _wc(self, resource):
        """ Syntactic sugar for the current collection write_concern setting.

        .. versionadded:: 0.0.8
        """
        return config.DOMAIN[resource]['mongo_write_concern']
