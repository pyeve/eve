"""
    eve.io.mongo.mongo (eve.io.mongo)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The actual implementation of the MongoDB data layer.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import ast
import itertools
from bson.errors import InvalidId
import simplejson as json
import pymongo
from flask import abort
from flask.ext.pymongo import PyMongo
from werkzeug.exceptions import HTTPException
from bson import ObjectId
from datetime import datetime
from eve.io.mongo.parser import parse, ParseError
from eve.io.base import DataLayer, ConnectionException, BaseJSONEncoder
from eve.utils import config, debug_error_message, validate_filters, \
    str_to_date, str_type


class MongoJSONEncoder(BaseJSONEncoder):
    """ Proprietary JSONEconder subclass used by the json render function.
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

    .. versionchanged:: 0.5
       Properly serialize nullable float and integers. #469.
       Return 400 if unsupported query operators are used. #387.

    .. versionchanged:: 0.4
       Don't serialize to objectid if value is null. #341.

    .. versionchanged:: 0.2
       Provide the specialized json serializer class as ``json_encoder_class``.

    .. versionchanged:: 0.1.1
       'serializers' added.
    """

    serializers = {
        'objectid': lambda value: ObjectId(value) if value else None,
        'datetime': str_to_date,
        'integer': lambda value: int(value) if value is not None else None,
        'float': lambda value: float(value) if value is not None else None,
    }

    # JSON serializer is a class attribute. Allows extensions to replace it
    # with their own implementation.
    json_encoder_class = MongoJSONEncoder

    operators = set(
        ['$gt', '$gte', '$in', '$lt', '$lt', '$lte', '$ne', '$nin'] +
        ['$or', '$and', '$not', '$nor'] +
        ['$mod', '$regex', '$text', '$where'] +
        ['$options', '$search', '$language'] +
        ['$exists', '$type'] +
        ['$geoWithin', '$geoIntersects', '$near', '$nearSphere'] +
        ['$all', '$elemMatch', '$size']
    )

    def init_app(self, app):
        """ Initialize PyMongo.
        .. versionchanged:: 0.0.9
           support for Python 3.3.
        """
        # mongod must be running or this will raise an exception
        try:
            self.driver = PyMongo(app)
        except Exception as e:
            raise ConnectionException(e)

    def find(self, resource, req, sub_resource_lookup):
        """ Retrieves a set of documents matching a given request. Queries can
        be expressed in two different formats: the mongo query syntax, and the
        python syntax. The first kind of query would look like: ::

            ?where={"name": "john doe}

        while the second would look like: ::

            ?where=name=="john doe"

        The resultset if paginated.

        :param resource: resource name.
        :param req: a :class:`ParsedRequest`instance.
        :param sub_resource_lookup: sub-resource lookup from the endpoint url.

        .. versionchanged:: 0.5
           Support for comma delimited sort syntax. Addresses #443.
           Return the error if a blacklisted MongoDB operator is used in query.
           Abort with 400 if unsupported query operator is used. #387.
           Abort with 400 in case of invalid sort syntax. #387.

        .. versionchanged:: 0.4
           'allowed_filters' is now checked before adding 'sub_resource_lookup'
           to the query, as it is considered safe.
           Refactored to use self._client_projection since projection is now
           honored by getitem() as well.

        .. versionchanged:: 0.3
           Support for new _mongotize() signature.

        .. versionchagend:: 0.2
           Support for sub-resources.
           Support for 'default_sort'.

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

        client_sort = {}
        spec = {}

        if req.sort:
            try:
                # assume it's mongo syntax (ie. ?sort=[("name", 1)])
                client_sort = ast.literal_eval(req.sort)
            except ValueError:
                # it's not mongo so let's see if it's a comma delimited string
                # instead (ie. "?sort=-age, name").
                sort = []
                for sort_arg in [s.strip() for s in req.sort.split(",")]:
                    if sort_arg[0] == "-":
                        sort.append((sort_arg[1:], -1))
                    else:
                        sort.append((sort_arg, 1))
                if len(sort) > 0:
                    client_sort = sort
            except Exception as e:
                abort(400, description=debug_error_message(str(e)))

        if req.where:
            try:
                spec = self._sanitize(json.loads(req.where))
            except HTTPException as e:
                # _sanitize() is raising an HTTP exception; let it fire.
                raise
            except:
                # couldn't parse as mongo query; give the python parser a shot.
                try:
                    spec = parse(req.where)
                except ParseError:
                    abort(400, description=debug_error_message(
                        'Unable to parse `where` clause'
                    ))

        bad_filter = validate_filters(spec, resource)
        if bad_filter:
            abort(400, bad_filter)

        if sub_resource_lookup:
            spec = self.combine_queries(spec, sub_resource_lookup)

        spec = self._mongotize(spec, resource)

        client_projection = self._client_projection(req)

        datasource, spec, projection, sort = self._datasource_ex(
            resource,
            spec,
            client_projection,
            client_sort)

        if req.if_modified_since:
            spec[config.LAST_UPDATED] = \
                {'$gt': req.if_modified_since}

        if len(spec) > 0:
            args['spec'] = spec

        if sort is not None:
            args['sort'] = sort

        if projection is not None:
            args['fields'] = projection

        return self.driver.db[datasource].find(**args)

    def find_one(self, resource, req, **lookup):
        """ Retrieves a single document.

        :param resource: resource name.
        :param req: a :class:`ParsedRequest` instance.
        :param **lookup: lookup query.

        .. versionchanged:: 0.4
           Honor client projection requests.

        .. versionchanged:: 0.3.0
           Support for new _mongotize() signature.
           Custom ID_FIELD lookups would raise an exception. See #203.

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
                lookup[config.ID_FIELD] = ObjectId(lookup[config.ID_FIELD])
            except (InvalidId, TypeError):
                # Returns a type error when {'_id': {...}}
                pass

        self._mongotize(lookup, resource)

        client_projection = self._client_projection(req)

        datasource, filter_, projection, _ = self._datasource_ex(
            resource,
            lookup,
            client_projection)

        document = self.driver.db[datasource].find_one(filter_, projection)
        return document

    def find_one_raw(self, resource, _id):
        """ Retrieves a single raw document.

        :param resource: resource name.
        :param id: unique id.

        .. versionadded:: 0.4
        """
        datasource, filter_, _, _ = self._datasource_ex(resource,
                                                        {config.ID_FIELD: _id},
                                                        None)

        document = self.driver.db[datasource].find_one(_id)
        return document

    def find_list_of_ids(self, resource, ids, client_projection=None):
        """ Retrieves a list of documents from the collection given
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

        datasource, spec, projection, _ = self._datasource_ex(
            resource, query=query, client_projection=client_projection
        )

        documents = self.driver.db[datasource].find(
            spec=spec, fields=projection
        )
        return documents

    def insert(self, resource, doc_or_docs):
        """ Inserts a document into a resource collection.

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
        datasource, _, _, _ = self._datasource_ex(resource)
        try:
            return self.driver.db[datasource].insert(doc_or_docs,
                                                     **self._wc(resource))
        except pymongo.errors.DuplicateKeyError as e:
            abort(409, description=debug_error_message(
                'pymongo.errors.DuplicateKeyError: %s' % e
            ))
        except pymongo.errors.InvalidOperation as e:
            abort(500, description=debug_error_message(
                'pymongo.errors.InvalidOperation: %s' % e
            ))
        except pymongo.errors.OperationFailure as e:
            # most likely a 'w' (write_concern) setting which needs an
            # existing ReplicaSet which doesn't exist. Please note that the
            # update will actually succeed (a new ETag will be needed).
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    def update(self, resource, id_, updates):
        """ Updates a collection document.

        .. versionchanged:: 0.4
           Return a 400 on pymongo DuplicateKeyError.

        .. versionchanged:: 0.3.0
           Custom ID_FIELD lookups would fail. See #203.

        .. versionchanged:: 0.2
           Don't explicitly convert ID_FIELD to ObjectId anymore, so we can
           also process different types (UUIDs etc).

        .. versionchanged:: 0.0.9
           More informative error messages.

        .. versionchanged:: 0.0.8
           'write_concern' support.

        .. versionchanged:: 0.0.6
           projection queries ('?projection={"name": 1}')

        .. versionchanged:: 0.0.4
           retrieves the target collection via the new config.SOURCES helper.
        """
        datasource, filter_, _, _ = self._datasource_ex(resource,
                                                        {config.ID_FIELD: id_})

        # TODO consider using find_and_modify() instead. The document might
        # have changed since the ETag was computed. This would require getting
        # the original document as an argument though.
        try:
            self.driver.db[datasource].update(filter_, {"$set": updates},
                                              **self._wc(resource))
        except pymongo.errors.DuplicateKeyError as e:
            abort(400, description=debug_error_message(
                'pymongo.errors.DuplicateKeyError: %s' % e
            ))
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    def replace(self, resource, id_, document):
        """ Replaces an existing document.

        .. versionchanged:: 0.3.0
           Custom ID_FIELD lookups would fail. See #203.

        .. versionchanged:: 0.2
           Don't explicitly converto ID_FIELD to ObjectId anymore, so we can
           also process different types (UUIDs etc).

        .. versionadded:: 0.1.0
        """
        datasource, filter_, _, _ = self._datasource_ex(resource,
                                                        {config.ID_FIELD: id_})

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

    def remove(self, resource, lookup):
        """ Removes a document or the entire set of documents from a
        collection.

        .. versionchanged:: 0.3
           Support lookup arg, which allows to properly delete sub-resources
           (only delete documents that meet a certain constraint).

        .. versionchanged:: 0.2
           Don't explicitly converto ID_FIELD to ObjectId anymore, so we can
           also process different types (UUIDs etc).

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
        lookup = self._mongotize(lookup, resource)
        datasource, filter_, _, _ = self._datasource_ex(resource, lookup)
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
        """ Takes two db queries and applies db-specific syntax to produce
        the intersection.

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
        Used know whether we need to parse a compound query.

        .. versionadded: 0.1.0
           Support for parsing values embedded in compound db queries
        """
        try:
            self.get_value_from_query(query, field_name)
        except KeyError:
            return False
        return True

    def is_empty(self, resource):
        """ Returns True if resource is empty; False otherwise. If there is no
        predefined filter on the resource we're relying on the
        db.collection.count(). However, if we do have a predefined filter we
        have to fallback on the find() method, which can be much slower.

        .. versionadded:: 0.3
        """
        datasource, filter_, _, _ = self._datasource(resource)
        coll = self.driver.db[datasource]
        try:
            if not filter_:
                # faster, but we can only affrd it if there's now predefined
                # filter on the datasource.
                return coll.count() == 0
            else:
                # fallback on find() since we have a filter to apply.
                try:
                    # need to check if the whole resultset is missing, no
                    # matter the IMS header.
                    del filter_[config.LAST_UPDATED]
                except:
                    pass
                return coll.find(filter_).count() == 0
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            abort(500, description=debug_error_message(
                'pymongo.errors.OperationFailure: %s' % e
            ))

    def _mongotize(self, source, resource):
        """ Recursively iterates a JSON dictionary, turning RFC-1123 strings
        into datetime values and ObjectId-link strings into ObjectIds.

        .. versionchanged:: 0.3
           'query_objectid_as_string' allows to bypass casting string types
           to objectids.

        .. versionchanged:: 0.1.1
           Renamed from _jsondatetime to _mongotize, as it now handles
           ObjectIds too.

        .. versionchanged:: 0.1.0
           Datetime conversion was failing on Py2, since 0.0.9 :P

        .. versionchanged:: 0.0.9
           support for Python 3.3.

        .. versionadded:: 0.0.4
        """
        schema = config.DOMAIN[resource]
        skip_objectid = schema.get('query_objectid_as_string', False)

        def try_cast(v):
            try:
                return datetime.strptime(v, config.DATE_FORMAT)
            except:
                if not skip_objectid:
                    try:
                        # Convert to unicode because ObjectId() interprets
                        # 12-character strings (but not unicode) as binary
                        # representations of ObjectId's.  See
                        # https://github.com/nicolaiarocci/eve/issues/508
                        try:
                            r = ObjectId(unicode(v))
                        except NameError:
                            # We're on Python 3 so it's all unicode # already.
                            r = ObjectId(v)
                        return r
                    except:
                        return v
                else:
                    return v

        for k, v in source.items():
            if isinstance(v, dict):
                self._mongotize(v, resource)
            elif isinstance(v, list):
                for i, v1 in enumerate(v):
                    if isinstance(v1, dict):
                        source[k][i] = self._mongotize(v1, resource)
                    else:
                        source[k][i] = try_cast(v1)
            elif isinstance(v, str_type):
                source[k] = try_cast(v)

        return source

    def _sanitize(self, spec):
        """ Makes sure that only allowed operators are included in the query,
        aborts with a 400 otherwise.

        .. versionchanged:: 0.5
           Abort with 400 if unsupported query operators are used. #387.
           DRY.

        .. versionchanged:: 0.0.9
           More informative error messages.
           Allow ``auth_username_field`` to be set to ``ID_FIELD``.

        .. versionadded:: 0.0.7
        """
        def sanitize_keys(spec):
            ops = set([op for op in spec.keys() if op[0] == '$'])
            unknown = ops - Mongo.operators
            if unknown:
                abort(400, description=debug_error_message(
                    'Query contains unknown or unsupported operators: %s' %
                    ', '.join(unknown)
                ))

            if set(spec.keys()) & set(config.MONGO_QUERY_BLACKLIST):
                abort(400, description=debug_error_message(
                    'Query contains operators banned in MONGO_QUERY_BLACKLIST'
                ))

        sanitize_keys(spec)
        for value in spec.values():
            if isinstance(value, dict):
                sanitize_keys(value)
        return spec

    def _wc(self, resource):
        """ Syntactic sugar for the current collection write_concern setting.

        .. versionadded:: 0.0.8
        """
        return config.DOMAIN[resource]['mongo_write_concern']

    def _client_projection(self, req):
        """ Returns a properly parsed client projection if available.

        :param req: a :class:`ParsedRequest` instance.

        .. versionadded:: 0.4
        """
        client_projection = {}
        if req and req.projection:
            try:
                client_projection = json.loads(req.projection)
                if not isinstance(client_projection, dict):
                    raise Exception('The projection parameter has to be a '
                                    'dict')
            except:
                abort(400, description=debug_error_message(
                    'Unable to parse `projection` clause'
                ))
        return client_projection
