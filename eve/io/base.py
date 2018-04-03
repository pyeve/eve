# -*- coding: utf-8 -*-

"""
    eve.io.base
    ~~~~~~~~~~~

    Standard interface implemented by Eve data layers.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import datetime
import simplejson as json
from copy import copy
from flask import request, abort
from eve.utils import date_to_str
from eve.auth import auth_field_and_value
from eve.utils import config, auto_fields, debug_error_message


class BaseJSONEncoder(json.JSONEncoder):
    """ Proprietary JSONEconder subclass used by the json render function.
    This is needed to address the encoding of special values.
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            # convert any datetime to RFC 1123 format
            return date_to_str(obj)
        elif isinstance(obj, (datetime.time, datetime.date)):
            # should not happen since the only supported date-like format
            # supported at dmain schema level is 'datetime' .
            return obj.isoformat()
        elif isinstance(obj, set):
            # convert set objects to encodable lists
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class ConnectionException(Exception):
    """ Raised when DataLayer subclasses cannot find/activate to their
    database connection.

    :param driver_exception: the original exception raised by the source db
                             driver
    """
    def __init__(self, driver_exception=None):
        self.driver_exception = driver_exception

    def __str__(self):
        msg = ("Error initializing the driver. Make sure the database server"
               "is running. ")
        if self.driver_exception:
            msg += "Driver exception: %s" % repr(self.driver_exception)
        return msg


class DataLayer(object):
    """ Base data layer class. Defines the interface that actual data-access
    classes, being subclasses, must implement. Implemented as a Flask
    extension.

    Admittedly, this interface is a Mongo rip-off. See the io.mongo
    package for an implementation example.

    .. versionchanged:: 0.2
       Allow subclasses to provide their own specialized json encoder.

    .. versionchanged:: 0.1.1
       'serializers' dictionary added.

    .. versionchanged:: 0.1.0
       Support for PUT method.

    .. versionchanged:: 0.0.6
       support for 'projections' has been added. For more information see
       http://docs.mongodb.org/manual/reference/glossary/#term-projection.
       While typically a MongoDB feature, other subclasses could decide to
       provide support for their own projection syntax.

    .. versionchanged:: 0.0.4
       the _datasource helper function has been added.
    """

    class OriginalChangedError(Exception):
        pass

    # if custom serialize functions are needed, add them to the 'serializers'
    # dictionary, eg:
    # serializers = {'objectid': ObjectId, 'datetime': serialize_date}
    serializers = {}

    # json.JSONEncoder subclass for serializing data to json.
    # Subclasses should provide their own specialized encoder (see
    # eve.io.mongo.MongoJSONEncoder).
    json_encoder_class = BaseJSONEncoder

    def __init__(self, app):
        """ Implements the Flask extension pattern.

        .. versionchanged:: 0.2
           Explicit initialize self.driver to None.
        """
        self.driver = None
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None

    def init_app(self, app):
        """ This is where you want to initialize the db driver so it will be
        alive through the whole instance lifespan.
        """
        raise NotImplementedError

    def find(self, resource, req, sub_resource_lookup):
        """ Retrieves a set of documents (rows), matching the current request.
        Consumed when a request hits a collection/document endpoint
        (`/people/`).

        :param resource: resource being accessed. You should then use
                         the ``datasource`` helper function to retrieve both
                         the db collection/table and base query (filter), if
                         any.
        :param req: an instance of ``eve.utils.ParsedRequest``. This contains
                    all the constraints that must be fulfilled in order to
                    satisfy the original request (where and sort parts, paging,
                    etc). Be warned that `where` and `sort` expressions will
                    need proper parsing, according to the syntax that you want
                    to support with your driver. For example ``eve.io.Mongo``
                    supports both Python and Mongo-like query syntaxes.
        :param sub_resource_lookup: sub-resource lookup from the endpoint url.

        .. versionchanged:: 0.3
           Support for sub-resources.
        """
        raise NotImplementedError

    def aggregate(self, resource, pipeline, options):
        """ Perform an aggregation on the resource datasource and returns
        the result. Only implent this if the underlying db engine supports
        aggregation operations.

        :param resource: resource being accessed. You should then use
                         the ``datasource`` helper function to retrieve
                         the db collection/table consumed by the resource.
        :param pipeline: aggregation pipeline to be executed.
        :param options: aggregation options to be considered.

        .. versionadded:: 0.7
        """
        raise NotImplementedError

    def find_one(self, resource, req, check_auth_value=True,
                 force_auth_field_projection=False, **lookup):
        """ Retrieves a single document/record. Consumed when a request hits an
        item endpoint (`/people/id/`).

        :param resource: resource being accessed. You should then use the
                         ``datasource`` helper function to retrieve both the
                         db collection/table and base query (filter), if any.
        :param req: an instance of ``eve.utils.ParsedRequest``. This contains
                    all the constraints that must be fulfilled in order to
                    satisfy the original request (where and sort parts, paging,
                    etc). As we are going to only look for one document here,
                    the only req attribute that you want to process here is
                    ``req.projection``.
        :param check_auth_value: a boolean flag indicating if the find
                                 operation should consider user-restricted
                                 resource access. Defaults to ``True``.
        :param force_auth_field_projection: a boolean flag indicating if the
                                            find operation should always
                                            include the user-restricted
                                            resource access field (if
                                            configured). Defaults to ``False``.

        :param **lookup: the lookup fields. This will most likely be a record
                         id or, if alternate lookup is supported by the API,
                         the corresponding query.


        .. versionchanged:: 0.4
           Added the 'req' argument.
        """
        raise NotImplementedError

    def find_one_raw(self, resource, **lookup):
        """ Retrieves a single, raw document. No projections or datasource
        filters are being applied here. Just looking up the document using the
        same lookup.

        :param resource: resource name.
        :param ** lookup: lookup query.

        .. versionadded:: 0.4
        """
        raise NotImplementedError

    def find_list_of_ids(self, resource, ids, client_projection=None):
        """ Retrieves a list of documents based on a list of primary keys
        The primary key is the field defined in `ID_FIELD`.
        This is a separate function to allow us to use per-database
        optimizations for this type of query.

        :param resource: resource name.
        :param ids: a list of ids corresponding to the documents
        to retrieve
        :param client_projection: a specific projection to use
        :return: a list of documents matching the ids in `ids` from the
        collection specified in `resource`

        .. versionadded:: 0.1.0
        """
        raise NotImplementedError

    def insert(self, resource, doc_or_docs):
        """ Inserts a document into a resource collection/table.

        :param resource: resource being accessed. You should then use
                         the ``datasource`` helper function to retrieve both
                         the actual datasource name.
        :param doc_or_docs: json document or list of json documents to be added
                            to the database.

        .. versionchanged:: 0.0.6
            'document' param renamed to 'doc_or_docs', making support for bulk
            inserts apparent.
        """
        raise NotImplementedError

    def update(self, resource, id_, updates, original):
        """ Updates a collection/table document/row.
        :param resource: resource being accessed. You should then use
                         the ``datasource`` helper function to retrieve
                         the actual datasource name.
        :param id_: the unique id of the document.
        :param updates: json updates to be performed on the database document
                        (or row).
        :param original: definition of the json document that should be
        updated.
        :raise OriginalChangedError: raised if the database layer notices a
        change from the supplied `original` parameter.
        """
        raise NotImplementedError

    def replace(self, resource, id_, document, original):
        """ Replaces a collection/table document/row.
        :param resource: resource being accessed. You should then use
                         the ``datasource`` helper function to retrieve
                         the actual datasource name.
        :param id_: the unique id of the document.
        :param document: the new json document
        :param original: definition of the json document that should be
        updated.
        :raise OriginalChangedError: raised if the database layer notices a
        change from the supplied `original` parameter.
        .. versionadded:: 0.1.0
        """
        raise NotImplementedError

    def remove(self, resource, lookup):
        """ Removes a document/row or an entire set of documents/rows from a
        database collection/table.

        :param resource: resource being accessed. You should then use
                         the ``datasource`` helper function to retrieve
                         the actual datasource name.
        :param lookup: a dict with the query that documents must match in order
                       to qualify for deletion. For single document deletes,
                       this is usually the unique id of the document to be
                       removed.

        .. versionchanged:: 0.3
           '_id' arg removed; replaced with 'lookup'.
        """
        raise NotImplementedError

    def combine_queries(self, query_a, query_b):
        """ Takes two db queries and applies db-specific syntax to produce
        the intersection.

        .. versionadded: 0.1.0
           Support for intelligent combination of db queries
        """
        raise NotImplementedError

    def get_value_from_query(self, query, field_name):
        """ Parses the given potentially-complex query and returns the value
        being assigned to the field given in `field_name`.

        This mainly exists to deal with more complicated compound queries

        .. versionadded: 0.1.0
           Support for parsing values embedded in compound db queries
        """
        raise NotImplementedError

    def query_contains_field(self, query, field_name):
        """ For the specified field name, does the query contain it?
        Used know whether we need to parse a compound query.

        .. versionadded: 0.1.0
           Support for parsing values embedded in compound db queries
        """
        raise NotImplementedError

    def is_empty(self, resource):
        """ Returns True if the collection is empty; False otherwise. While
        a user could rely on self.find() method to achieve the same result,
        this method can probably take advantage of specific datastore features
        to provide better performance.

        Don't forget, a 'resource' could have a pre-defined filter. If that is
        the case, it will have to be taken into consideration when performing
        the is_empty() check (see eve.io.mongo.mongo.py implementation).

        :param resource: resource being accessed. You should then use
                         the ``datasource`` helper function to retrieve
                         the actual datasource name.

        .. versionadded: 0.3
        """
        raise NotImplementedError

    def datasource(self, resource):
        """ Returns a tuple with the actual name of the database
        collection/table, base query and projection for the resource being
        accessed.

        :param resource: resource being accessed.

        .. versionchanged:: 0.6
           Name change: from _datasource to datasource.

        .. versionchanged:: 0.5
           If allow_unknown is enabled for the resource, don't return any
           projection for the document. Addresses #397 and #250.

        .. versionchanged:: 0.4
           Return copies to avoid accidental tampering. Fix #258.

        .. versionchanged:: 0.2
           Support for 'default_sort'.
        """
        dsource = config.SOURCES[resource]

        source = copy(dsource['source'])
        filter_ = copy(dsource['filter'])
        sort = copy(dsource['default_sort'])
        projection = copy(dsource['projection'])

        return source, filter_, projection, sort,

    def _datasource_ex(self, resource, query=None, client_projection=None,
                       client_sort=None, check_auth_value=True,
                       force_auth_field_projection=False):
        """ Returns both db collection and exact query (base filter included)
        to which an API resource refers to.

        .. versionchanged:: 0.5.2
           Make User Restricted Resource Access work with HMAC Auth too.

        .. versionchanged:: 0.5
           Let client projection work when 'allow_unknown' is active (#497).

        .. versionchanged:: 0.4
           Always return required/auto fields (issue 282.)

        .. versionchanged:: 0.3
           Field exclusion support in client projections.
           Honor auth_field even when client query is missing.
           Only inject auth_field in queries when we are not creating new
           documents.
           'auth_field' and 'request_auth_value' fetching is now delegated to
           auth.auth_field_and value().

        .. versionchanged:: 0.2
           Difference between resource and item endpoints is now determined
           by the presence of a '|' in request.endpoint.
           Support for 'default_sort'.

        .. versionchanged:: 0.1.1
           auth.request_auth_value is now used to store the auth_field value.

        .. versionchanged:: 0.1.0
           Calls `combine_queries` to merge query and filter_
           Updated logic performing `auth_field` check

        .. versionchanged:: 0.0.9
           Storing self.app.auth.userid in auth_field when 'user-restricted
           resource access' is enabled.
           Support for Python 3.3.

        .. versionchanged:: 0.0.6
           'auth_username_field' is injected even in empty queries.
           Projection queries ('?projection={"name": 1}')

        .. versionchanged:: 0.0.5
           Support for 'user-restricted resource access'.

        .. versionadded:: 0.0.4
        """

        datasource, filter_, projection_, sort_ = self.datasource(resource)
        if client_sort:
            sort = client_sort
        else:
            # default sort is activated only if 'sorting' is enabled for the
            # resource.
            # TODO Consider raising a validation error on startup instead?
            sort = sort_ if sort_ and config.DOMAIN[resource]['sorting'] else \
                None

        if filter_:
            if query:
                # Can't just dump one set of query operators into another
                # e.g. if the dataset contains a custom datasource pattern
                #   'filter': {'username': {'$exists': True}}
                # and we try to filter on the field `username`,
                # which is correct?

                # Solution: call the db driver `combine_queries` operation
                # which will apply db-specific syntax to produce the
                # intersection of the two queries
                query = self.combine_queries(query, filter_)
            else:
                query = filter_

        fields = projection_
        if client_projection:
            if projection_:
                # only allow fields which are included with the standard
                # projection for the resource (avoid sniffing of private
                # fields)
                keep_fields = auto_fields(resource)
                if 1 in client_projection.values():
                    # inclusive projection - all values are 0 unless spec. or
                    # auto
                    fields = dict([(field, field in keep_fields) for field in
                                   fields.keys()])
                for field, value in client_projection.items():
                    field_base = field.split('.')[0]
                    if field_base not in keep_fields and field_base in fields:
                        fields[field] = value
            else:
                # there's no standard projection so we assume we are in a
                # allow_unknown = True
                fields = client_projection
        # always drop exclusion projection, thus avoid mixed projection not
        # supported by db driver
        fields = dict([(field, 1) for field, value in fields.items() if
                       value])

        # If the current HTTP method is in `public_methods` or
        # `public_item_methods`, skip the `auth_field` check

        # Only inject the auth_field in the query when not creating new
        # documents.
        if request and request.method != 'POST' and (
            check_auth_value or force_auth_field_projection
        ):
            auth_field, request_auth_value = auth_field_and_value(resource)
            if auth_field:
                if request_auth_value and check_auth_value:
                    if query:
                        # If the auth_field *replaces* a field in the query,
                        # and the values are /different/, deny the request
                        # This prevents the auth_field condition from
                        # overwriting the query (issue #77)
                        auth_field_in_query = \
                            self.app.data.query_contains_field(query,
                                                               auth_field)
                        if auth_field_in_query and \
                            self.app.data.get_value_from_query(
                                query, auth_field) != request_auth_value:
                            desc = 'Incompatible User-Restricted Resource ' \
                                   'request.'
                            abort(401, description=desc)
                        else:
                            query = self.app.data.combine_queries(
                                query, {auth_field: request_auth_value}
                            )
                    else:
                        query = {auth_field: request_auth_value}
                if force_auth_field_projection:
                    fields[auth_field] = 1
        return datasource, query, fields, sort

    def _client_projection(self, req):
        """ Returns a properly parsed client projection if available.

        :param req: a :class:`ParsedRequest` instance.

        .. versionchanged:: 0.6.1
           Moved from the mongo layer up to the DataLayer base class (#724).

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
