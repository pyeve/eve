# -*- coding: utf-8 -*-

"""
    eve.io.mongo.mongo (eve.io.mongo)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The actual implementation of the MongoDB data layer.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import itertools
from datetime import datetime

import ast
import pymongo
import simplejson as json
from bson import ObjectId
from bson.dbref import DBRef
from copy import copy
from flask import abort, request, g
from .flask_pymongo import PyMongo
from pymongo import WriteConcern
from werkzeug.exceptions import HTTPException
import decimal
from bson import decimal128
from collections import OrderedDict

from eve.auth import resource_auth
from eve.io.base import DataLayer, ConnectionException, BaseJSONEncoder
from eve.io.mongo.parser import parse, ParseError
from eve.utils import (
    config,
    debug_error_message,
    validate_filters,
    str_to_date,
    str_type,
)
from ...versioning import versioned_id_field


class MongoJSONEncoder(BaseJSONEncoder):
    """Proprietary JSONEconder subclass used by the json render function.
    This is needed to address the encoding of special values.

    .. versionchanged:: 0.8.2
       Key-value pair order in DBRef are honored when encoding. Closes #1255.

    .. versionchanged:: 0.6.2
       Do not attempt to serialize callables. Closes #790.

    .. versionadded:: 0.2
    """

    def default(self, obj):
        if isinstance(obj, ObjectId):
            # BSON/Mongo ObjectId is rendered as a string
            return str(obj)
        if callable(obj):
            # when SCHEMA_ENDPOINT is active, 'coerce' rule is likely to
            # contain a lambda/callable which can't be jSON serialized
            # (and we probably don't want it to be exposed anyway). See #790.
            return "<callable>"
        if isinstance(obj, DBRef):
            retval = OrderedDict()
            retval["$ref"] = obj.collection
            retval["$id"] = str(obj.id)
            if obj.database:
                retval["$db"] = obj.database
            return json.RawJSON(json.dumps(retval))
        if isinstance(obj, decimal128.Decimal128):
            return str(obj)
        # delegate rendering to base class method
        return super(MongoJSONEncoder, self).default(obj)


class Mongo(DataLayer):
    """MongoDB data access layer for Eve REST API.

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
        "objectid": lambda value: ObjectId(value) if value else None,
        "datetime": str_to_date,
        "integer": lambda value: int(value) if value is not None else None,
        "float": lambda value: float(value) if value is not None else None,
        "number": lambda val: json.loads(val) if val is not None else None,
        "boolean": lambda v: {"1": True, "true": True, "0": False, "false": False}[
            str(v).lower()
        ],
        "dbref": lambda value: DBRef(
            value["$col"] if "$col" in value else value["$ref"],
            value["$id"],
            value["$db"] if "$db" in value else None,
        )
        if value is not None
        else None,
        "decimal": lambda value: decimal128.Decimal128(decimal.Decimal(str(value)))
        if value is not None
        else None,
    }

    # JSON serializer is a class attribute. Allows extensions to replace it
    # with their own implementation.
    json_encoder_class = MongoJSONEncoder

    operators = set(
        ["$gt", "$gte", "$in", "$lt", "$lte", "$ne", "$nin", "$eq"]
        + ["$or", "$and", "$not", "$nor"]
        + ["$mod", "$regex", "$text", "$where"]
        + ["$options", "$search", "$language", "$caseSensitive"]
        + ["$diacriticSensitive", "$exists", "$type"]
        + ["$geoWithin", "$geoIntersects", "$near", "$nearSphere", "$centerSphere"]
        + ["$geometry", "$maxDistance", "$minDistance", "$box"]
        + ["$all", "$elemMatch", "$size"]
        + ["$bitsAllClear", "$bitsAllSet", "$bitsAnyClear", "$bitsAnySet"]
        + ["$center", "$expr"]
    )

    def init_app(self, app):
        """Initialize PyMongo.

        .. versionchanged:: 0.6
           Use mongo_prefix for multidb support.

        .. versionchanged:: 0.0.9
           Support for Python 3.3.
        """
        # mongod must be running or this will raise an exception
        self.driver = PyMongos(self)
        self.mongo_prefix = None

    def find(self, resource, req, sub_resource_lookup, perform_count=True):
        """Retrieves a set of documents matching a given request. Queries can
        be expressed in two different formats: the mongo query syntax, and the
        python syntax. The first kind of query would look like: ::

            ?where={"name": "john doe"}

        while the second would look like: ::

            ?where=name=="john doe"

        The resultset if paginated.

        :param resource: resource name.
        :param req: a :class:`ParsedRequest`instance.
        :param sub_resource_lookup: sub-resource lookup from the endpoint url.

        .. versionchanged:: 0.6
           Support for multiple databases.
           Filter soft deleted documents by default

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

        .. versionchanged:: 0.2
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

        if req and req.max_results:
            args["limit"] = req.max_results

        if req and req.page > 1:
            args["skip"] = (req.page - 1) * req.max_results

        # TODO sort syntax should probably be coherent with 'where': either
        # mongo-like # or python-like. Currently accepts only mongo-like sort
        # syntax.

        # TODO should validate on unknown sort fields (mongo driver doesn't
        # return an error)

        client_sort = self._convert_sort_request_to_dict(req)
        spec = self._convert_where_request_to_dict(resource, req)

        bad_filter = validate_filters(spec, resource)
        if bad_filter:
            abort(400, bad_filter)

        if sub_resource_lookup:
            spec = self.combine_queries(spec, sub_resource_lookup)

        if (
            config.DOMAIN[resource]["soft_delete"]
            and not (req and req.show_deleted)
            and not self.query_contains_field(spec, config.DELETED)
        ):
            # Soft delete filtering applied after validate_filters call as
            # querying against the DELETED field must always be allowed when
            # soft_delete is enabled
            spec = self.combine_queries(spec, {config.DELETED: {"$ne": True}})

        spec = self._mongotize(spec, resource)

        client_projection = self._client_projection(req)

        datasource, spec, projection, sort = self._datasource_ex(
            resource, spec, client_projection, client_sort
        )

        if req and req.if_modified_since:
            spec[config.LAST_UPDATED] = {"$gt": req.if_modified_since}

        if len(spec) > 0:
            args["filter"] = spec

        if sort is not None:
            args["sort"] = sort

        if projection:
            args["projection"] = projection

        target = self.pymongo(resource).db[datasource]
        try:
            result = target.find(**args)
        except TypeError as e:
            # pymongo raises ValueError when invalid query paramenters are
            # included. We do our best to catch them beforehand but, especially
            # with key/value sort syntax, invalid ones might still slip in.
            self.app.logger.exception(e)
            abort(400, description=debug_error_message(str(e)))

        if perform_count:
            try:
                count = target.count_documents(spec)
            except:
                # fallback to deprecated method. this might happen when the query
                # includes operators not supported by count_documents(). one
                # documented use-case is when we're running on mongo 3.4 and below,
                # which does not support $expr ($expr must replace $where # in
                # count_documents()).

                # 1. Mongo 3.6+; $expr: pass
                # 2. Mongo 3.6+; $where: pass (via fallback)
                # 3. Mongo 3.4; $where: pass (via fallback)
                # 4. Mongo 3.4; $expr: fail (operator not supported by db)

                # See: http://api.mongodb.com/python/current/api/pymongo/collection.html#pymongo.collection.Collection.count
                count = target.count()
        else:
            count = None

        return result, count

    def find_one(
        self,
        resource,
        req,
        check_auth_value=True,
        force_auth_field_projection=False,
        mongo_options=None,
        **lookup
    ):
        """Retrieves a single document.

        :param resource: resource name.
        :param req: a :class:`ParsedRequest` instance.
        :param mongo_options: Dict of parameters to pass to PyMongo with_options.
        :param **lookup: lookup query.

        .. versionchanged:: 0.6
           Support for multiple databases.
           Filter soft deleted documents by default

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
        self._mongotize(lookup, resource)

        client_projection = self._client_projection(req)

        datasource, filter_, projection, _ = self._datasource_ex(
            resource,
            lookup,
            client_projection,
            check_auth_value=check_auth_value,
            force_auth_field_projection=force_auth_field_projection,
        )

        if (
            (config.DOMAIN[resource]["soft_delete"])
            and (not req or not req.show_deleted)
            and (not self.query_contains_field(lookup, config.DELETED))
        ):
            filter_ = self.combine_queries(filter_, {config.DELETED: {"$ne": True}})
        # Here, we feed pymongo with `None` if projection is empty.
        target = self.pymongo(resource).db[datasource]
        if mongo_options:
            return target.with_options(**mongo_options).find_one(
                filter_, projection or None
            )
        else:
            return target.find_one(filter_, projection or None)

    def find_one_raw(self, resource, **lookup):
        """Retrieves a single raw document.

        :param resource: resource name.
        :param **lookup: lookup query.

        .. versionchanged:: 0.6
           Support for multiple databases.

        .. versionadded:: 0.4
        """
        id_field = config.DOMAIN[resource]["id_field"]
        _id = lookup.get(id_field)
        datasource, filter_, _, _ = self._datasource_ex(resource, {id_field: _id}, None)

        lookup = self._mongotize(lookup, resource)

        return self.pymongo(resource).db[datasource].find_one(lookup)

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

        .. versionchanged:: 0.6
           Support for multiple databases.

        .. versionchanged:: 0.1.1
           Using config.ID_FIELD instead of hard coded '_id'.

        .. versionadded:: 0.1.0
        """
        id_field = config.DOMAIN[resource]["id_field"]
        query = {"$or": [{id_field: id_} for id_ in ids]}

        datasource, spec, projection, _ = self._datasource_ex(
            resource, query=query, client_projection=client_projection
        )
        # projection of {} return all fields in MongoDB, but
        # pymongo will only return `_id`. It's a design flaw upstream.
        # Here, we feed pymongo with `None` if projection is empty.
        documents = (
            self.pymongo(resource)
            .db[datasource]
            .find(filter=spec, projection=(projection or None))
        )
        return documents

    def aggregate(self, resource, pipeline, options):
        """
        .. versionadded:: 0.7
        """
        datasource, _, _, _ = self.datasource(resource)
        challenge = self._mongotize({"key": pipeline}, resource)["key"]

        return self.pymongo(resource).db[datasource].aggregate(challenge, **options)

    def insert(self, resource, doc_or_docs):
        """Inserts a document into a resource collection.

        .. versionchanged:: 0.6.1
           Support for PyMongo 3.0.

        .. versionchanged:: 0.6
           Support for multiple databases.

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

        coll = self.get_collection_with_write_concern(datasource, resource)

        if isinstance(doc_or_docs, dict):
            doc_or_docs = [doc_or_docs]

        try:
            return coll.insert_many(doc_or_docs, ordered=True).inserted_ids
        except pymongo.errors.BulkWriteError as e:
            self.app.logger.exception(e)

            # since this is an ordered bulk operation, all remaining inserts
            # are aborted. Be aware that if BULK_ENABLED is True and more than
            # one document is included with the payload, some documents might
            # have been successfully inserted, even if the operation was
            # aborted.

            # report a duplicate key error since this can probably be
            # handled by the client.
            for error in e.details["writeErrors"]:
                # amazingly enough, pymongo does not appear to be exposing
                # error codes as constants.
                if error["code"] == 11000:
                    abort(
                        409,
                        description=debug_error_message(
                            "Duplicate key error at index: %s, message: %s"
                            % (error["index"], error["errmsg"])
                        ),
                    )

            abort(
                500,
                description=debug_error_message(
                    "pymongo.errors.BulkWriteError: %s" % e
                ),
            )

    def _change_request(self, resource, id_, changes, original, replace=False):
        """Performs a change, be it a replace or update.

        .. versionchanged:: 0.8.2
           Return 400 if update/replace with malformed DBRef field. See #1257.

        .. versionchanged:: 0.6.1
           Support for PyMongo 3.0.

        .. versionchanged:: 0.6
           Return 400 if an attempt is made to update/replace an immutable
           field.
        """
        id_field = config.DOMAIN[resource]["id_field"]
        query = {id_field: id_}
        if config.ETAG in original:
            query[config.ETAG] = original[config.ETAG]

        datasource, filter_, _, _ = self._datasource_ex(resource, query)

        coll = self.get_collection_with_write_concern(datasource, resource)
        try:
            result = (
                coll.replace_one(filter_, changes)
                if replace
                else coll.update_one(filter_, changes)
            )
            if (
                config.ETAG in original
                and result
                and result.acknowledged
                and result.modified_count == 0
            ):
                raise self.OriginalChangedError()
        except pymongo.errors.DuplicateKeyError as e:
            abort(
                400,
                description=debug_error_message(
                    "pymongo.errors.DuplicateKeyError: %s" % e
                ),
            )
        except (pymongo.errors.WriteError, pymongo.errors.OperationFailure) as e:
            # server error codes and messages changed between 2.4 and 2.6/3.0.
            server_version = self.driver.db.client.server_info()["version"][:3]
            if (server_version == "2.4" and e.code in (13596, 10148)) or e.code in (
                66,
                16837,
            ):
                # attempt to update an immutable field. this usually
                # happens when a PATCH or PUT includes a mismatching ID_FIELD.
                self.app.logger.warning(e)
                description = (
                    debug_error_message("pymongo.errors.OperationFailure: %s" % e)
                    or "Attempt to update an immutable field. Usually happens "
                    "when PATCH or PUT include a '%s' field, "
                    "which is immutable (PUT can include it as long as "
                    "it is unchanged)." % id_field
                )

                abort(400, description=description)
            else:
                # see comment in :func:`insert()`.
                self.app.logger.exception(e)
                abort(
                    500,
                    description=debug_error_message(
                        "pymongo.errors.OperationFailure: %s" % e
                    ),
                )

    def update(self, resource, id_, updates, original):
        """Updates a collection document.
        .. versionchanged:: 0.6
           Support for multiple databases.

        .. versionchanged:: 5.2
           Raise OriginalChangedError if document is changed from the
           specified original.

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

        return self._change_request(resource, id_, {"$set": updates}, original)

    def replace(self, resource, id_, document, original):
        """Replaces an existing document.
        .. versionchanged:: 0.6
           Support for multiple databases.

        .. versionchanged:: 5.2
           Raise OriginalChangedError if document is changed from the
           specified original.

        .. versionchanged:: 0.3.0
           Custom ID_FIELD lookups would fail. See #203.

        .. versionchanged:: 0.2
           Don't explicitly convert ID_FIELD to ObjectId anymore, so we can
           also process different types (UUIDs etc).

        .. versionadded:: 0.1.0
        """

        return self._change_request(resource, id_, document, original, replace=True)

    def remove(self, resource, lookup):
        """Removes a document or the entire set of documents from a
        collection.

        .. versionchanged:: 0.6.1
           Support for PyMongo 3.0.

        .. versionchanged:: 0.6
           Support for multiple databases.

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
        :returns
            A document (dict) describing the effect of the remove
            or None if write acknowledgement is disabled.
        """
        lookup = self._mongotize(lookup, resource)
        datasource, filter_, _, _ = self._datasource_ex(resource, lookup)

        coll = self.get_collection_with_write_concern(datasource, resource)
        try:
            coll.delete_many(filter_)
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            self.app.logger.exception(e)
            abort(
                500,
                description=debug_error_message(
                    "pymongo.errors.OperationFailure: %s" % e
                ),
            )

    # TODO: The next three methods could be pulled out to form the basis
    # of a separate MonqoQuery class

    def combine_queries(self, query_a, query_b):
        """Takes two db queries and applies db-specific syntax to produce
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
            "$and": [
                {k: v} for k, v in itertools.chain(query_a.items(), query_b.items())
            ]
        }

    def get_value_from_query(self, query, field_name):
        """For the specified field name, parses the query and returns
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
        elif "$and" in query:
            for condition in query["$and"]:
                if field_name in condition:
                    return condition[field_name]
        raise KeyError

    def query_contains_field(self, query, field_name):
        """For the specified field name, does the query contain it?
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
        """Returns True if resource is empty; False otherwise. If there is
        no predefined filter on the resource we're relying on the
        db.collection.count_documents. However, if we do have a predefined
        filter we have to fallback on the find() method, which can be much
        slower.

        .. versionchanged:: 0.6
           Support for multiple databases.

        .. versionadded:: 0.3
        """
        datasource, filter_, _, _ = self.datasource(resource)
        coll = self.pymongo(resource).db[datasource]
        try:
            if not filter_:
                # faster, but we can only afford it if there's now predefined
                # filter on the datasource.
                return coll.count_documents({}) == 0
            else:
                # fallback on find() since we have a filter to apply.
                try:
                    # need to check if the whole resultset is missing, no
                    # matter the IMS header.
                    del filter_[config.LAST_UPDATED]
                except:
                    pass
                return coll.count_documents(filter_) == 0
        except pymongo.errors.OperationFailure as e:
            # see comment in :func:`insert()`.
            self.app.logger.exception(e)
            abort(
                500,
                description=debug_error_message(
                    "pymongo.errors.OperationFailure: %s" % e
                ),
            )

    def _mongotize(self, source, resource, parse_objectid=False):
        """Recursively iterates a JSON dictionary, turning RFC-1123 strings
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
        resource_def = config.DOMAIN[resource]
        schema = resource_def.get("schema")
        id_field = resource_def["id_field"]
        id_field_versioned = versioned_id_field(resource_def)
        query_objectid_as_string = resource_def.get("query_objectid_as_string", False)
        parse_objectid = parse_objectid or not query_objectid_as_string

        def try_cast(k, v, should_parse_objectid):
            try:
                return datetime.strptime(v, config.DATE_FORMAT)
            except:
                if k in (id_field, id_field_versioned) or should_parse_objectid:
                    try:
                        # Convert to unicode because ObjectId() interprets
                        # 12-character strings (but not unicode) as binary
                        # representations of ObjectId's.  See
                        # https://github.com/pyeve/eve/issues/508
                        try:
                            r = ObjectId(unicode(v))
                        except NameError:
                            # We're on Python 3 so it's all unicode already.
                            r = ObjectId(v)
                        return r
                    except:
                        return v
                else:
                    return v

        def get_schema_type(keys, schema):
            def dict_sub_schema(base):
                if base.get("type") == "dict":
                    return base.get("schema")
                return base

            if not isinstance(schema, dict):
                return None
            if not keys:
                return schema.get("type")

            k = keys[0]
            keys = keys[1:]
            schema_type = schema[k].get("type") if k in schema else None
            if schema_type == "list":
                if "items" in schema[k]:
                    items = schema[k].get("items") or []
                    possible_types = [get_schema_type(keys, item) for item in items]
                    if "objectid" in possible_types:
                        return "objectid"
                    else:
                        return next((t for t in possible_types if t), None)
                elif "schema" in schema[k]:
                    # recursively check the schema
                    return get_schema_type(keys, dict_sub_schema(schema[k]["schema"]))
            elif schema_type == "dict":
                if "schema" in schema[k]:
                    return get_schema_type(keys, dict_sub_schema(schema[k]["schema"]))
            else:
                return schema_type

        for k, v in source.items():
            keys = k.split(".")
            schema_type = get_schema_type(keys, schema)
            is_objectid = (schema_type == "objectid") or parse_objectid
            if isinstance(v, dict):
                self._mongotize(v, resource, is_objectid)
            elif isinstance(v, list):
                for i, v1 in enumerate(v):
                    if isinstance(v1, dict):
                        source[k][i] = self._mongotize(v1, resource)
                    else:
                        source[k][i] = try_cast(k, v1, is_objectid)
            elif isinstance(v, str_type):
                source[k] = try_cast(k, v, is_objectid)

        return source

    def _sanitize(self, resource, spec):
        """Makes sure that only allowed operators are included in the query,
        aborts with a 400 otherwise.

        .. versionchanged:: 1.1.0
           Add mongo_query_whitelist config option to extend the list of
           supported operators

        .. versionchanged:: 0.5
           Abort with 400 if unsupported query operators are used. #387.
           DRY.

        .. versionchanged:: 0.0.9
           More informative error messages.
           Allow ``auth_username_field`` to be set to ``ID_FIELD``.

        .. versionadded:: 0.0.7
        """

        def sanitize_keys(spec):
            ops = set([op for op in spec.keys() if op[0] == "$"])
            known = Mongo.operators | set(
                config.DOMAIN[resource]["mongo_query_whitelist"]
            )

            unknown = ops - known
            if unknown:
                abort(
                    400,
                    description=debug_error_message(
                        "Query contains unknown or unsupported operators: %s"
                        % ", ".join(unknown)
                    ),
                )

            if set(spec.keys()) & set(config.MONGO_QUERY_BLACKLIST):
                abort(
                    400,
                    description=debug_error_message(
                        "Query contains operators banned in MONGO_QUERY_BLACKLIST"
                    ),
                )

        if isinstance(spec, dict):
            sanitize_keys(spec)
            for value in spec.values():
                self._sanitize(resource, value)
        if isinstance(spec, list):
            for value in spec:
                self._sanitize(resource, value)

        return spec

    def _convert_sort_request_to_dict(self, req):
        """Converts the contents of a `ParsedRequest`'s `sort` property to
        a dict
        """
        client_sort = {}
        if req and req.sort:
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
                self.app.logger.exception(e)
                abort(400, description=debug_error_message(str(e)))
        return client_sort

    def _convert_where_request_to_dict(self, resource, req):
        """Converts the contents of a `ParsedRequest`'s `where` property to
        a dict
        """
        query = {}
        if req and req.where:
            try:
                query = self._sanitize(resource, json.loads(req.where))
            except HTTPException:
                # _sanitize() is raising an HTTP exception; let it fire.
                raise
            except:
                # couldn't parse as mongo query; give the python parser a shot.
                try:
                    query = parse(req.where)
                except ParseError:
                    abort(
                        400,
                        description=debug_error_message(
                            "Unable to parse `where` clause"
                        ),
                    )
        return query

    def _wc(self, resource):
        """Syntactic sugar for the current collection write_concern setting.

        .. versionadded:: 0.0.8
        """
        return config.DOMAIN[resource]["mongo_write_concern"]

    def current_mongo_prefix(self, resource=None):
        """Returns the active mongo_prefix that should be used to retrieve
        a valid PyMongo instance from the cache. If 'self.mongo_prefix' is set
        it has precedence over both endpoint (resource) and default drivers.
        This allows Auth classes (for instance) to override default settings to
        use a user-reserved db instance.

        Even a standard Flask view can set the mongo_prefix:

            from flask import g

            g.mongo_prefix = 'MONGO2'

        :param resource: endpoint for which a mongo prefix is needed.

        ..versionchanged:: 0.7
          Allow standard Flask views (@app.route) to set the mongo_prefix on
          their own.

        ..versionadded:: 0.6
        """

        # the hack below avoids passing the resource around, which would not be
        # an issue within this module but would force an update to the
        # eve.io.media.MediaStorage interface, possibly breaking compatibility
        # for other database implementations.

        auth = None
        try:
            if resource is None and request and request.endpoint:
                resource = request.endpoint[: request.endpoint.index("|")]
            if request and request.endpoint:
                auth = resource_auth(resource)
        except ValueError:
            pass

        px = auth.get_mongo_prefix() if auth else None

        if px is None:
            px = g.get("mongo_prefix", None)

        if px is None:
            if resource:
                px = config.DOMAIN[resource].get("mongo_prefix", "MONGO")
            else:
                px = "MONGO"

        return px

    def pymongo(self, resource=None, prefix=None):
        """Returns an active PyMongo instance. If 'prefix' is defined then
        it has precedence over the endpoint ('resource') and/or
        'self.mongo_instance'.

        :param resource: endpoint for which a PyMongo instance is requested.
        :param prefix: PyMongo instance key. This has precedence over both
                       'resource' and eventual `self.mongo_prefix'.

        .. versionadded:: 0.6
        """
        px = prefix if prefix else self.current_mongo_prefix(resource=resource)

        if px not in self.driver:
            # instantiate and add to cache
            self.driver[px] = PyMongo(self.app, px)

        # important, we don't want to preserve state between requests
        self.mongo_prefix = None

        try:
            return self.driver[px]
        except Exception as e:
            raise ConnectionException(e)

    def get_collection_with_write_concern(self, datasource, resource):
        """Returns a pymongo Collection with the desired write_concern
        setting.

        PyMongo 3.0+ collections are immutable, yet we still want to allow the
        maintainer to change the write concern setting on the fly, hence the
        clone.

        .. versionadded:: 0.6.1
        """
        wc = WriteConcern(config.DOMAIN[resource]["mongo_write_concern"]["w"])
        return self.pymongo(resource).db[datasource].with_options(write_concern=wc)


class PyMongos(dict):
    """Cache for PyMongo instances. It is just a normal dict which exposes
    a 'db' property for backward compatibility.

    .. versionadded:: 0.6
    """

    def __init__(self, mongo, *args):
        self.mongo = mongo
        dict.__init__(self, args)

    @property
    def db(self):
        """Returns the 'default' PyMongo instance, which is either the
        'Mongo.mongo_prefix' value or 'MONGO'. This property is useful for
        backward compatibility as many custom Auth classes use the now obsolete
        'self.data.driver.db[collection]' pattern.
        """
        return self.mongo.pymongo().db


def ensure_mongo_indexes(app, resource):
    """Make sure 'mongo_indexes' is respected and mongo indexes are created on
    the current database.

    .. versionaddded:: 0.8
    """
    mongo_indexes = app.config["DOMAIN"][resource]["mongo_indexes"]
    if not mongo_indexes:
        return

    for name, value in mongo_indexes.items():
        if isinstance(value, tuple):
            list_of_keys, index_options = value
        else:
            list_of_keys = value
            index_options = {}

        _create_index(app, resource, name, list_of_keys, index_options)


def _create_index(app, resource, name, list_of_keys, index_options):
    """Create a specific index composed of the `list_of_keys` for the
    mongo collection behind the `resource` using the `app.config`
    to retrieve all data needed to find out the mongodb configuration.
    The index is also configured by the `index_options`.

    Index are a list of tuples setting for each one the name of the
    fields and the kind of order used, 1 for ascending and -1 for
    descending.

    For example:
        [('field_name', 1), ('other_field', -1)]

    Other indexes such as "hash", "2d", "text" can be used.

    Index options are a dictionary to set specific behaviour of the
    index.

    For example:
        {"sparse": True}

    .. versionchanged:: 0.8.1
       Add support for IndexKeySpecsConflict error. See #1180.

    .. versionadded:: 0.6

    """
    # it doesn't work as a typical mongodb method run in the request
    # life cycle, it is just called when the app start and it uses
    # pymongo directly.
    collection = app.config["SOURCES"][resource]["source"]

    # get db for given prefix
    try:
        # mongo_prefix might have been set by Auth class instance
        px = g.get("mongo_prefix")
    except:
        px = app.config["DOMAIN"][resource].get("mongo_prefix", "MONGO")

    with app.app_context():
        db = app.data.pymongo(resource, px).db

    kw = copy(index_options)
    kw["name"] = name

    colls = [db[collection]]
    if app.config["DOMAIN"][resource]["versioning"]:
        colls.append(db["%s_versions" % collection])

    for coll in colls:
        try:
            coll.create_index(list_of_keys, **kw)
        except pymongo.errors.OperationFailure as e:
            if e.code in (85, 86):
                # raised when the definition of the index has been changed.
                # (https://github.com/mongodb/mongo/blob/master/src/mongo/base/error_codes.err#L87)

                # by default, drop the old index with old configuration and
                # create the index again with the new configuration.
                coll.drop_index(name)
                coll.create_index(list_of_keys, **kw)
            else:
                raise
