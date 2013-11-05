# -*- coding: utf-8 -*-

"""
    eve.io.base
    ~~~~~~~~~~~

    Standard interface implemented by Eve data layers.

    :copyright: (c) 2013 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
from eve.utils import config, debug_error_message
from flask import request, abort
import simplejson as json
from eve.utils import date_to_str
import datetime


class BaseJSONEncoder(json.JSONEncoder):
    """ Propretary JSONEconder subclass used by the json render function.
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
        return json.JSONEncoder.default(self, obj)


class ConnectionException(Exception):
    """Raised when DataLayer subclasses cannot find/activate to their
    database connection

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

    def find(self, resource, req):
        """ Retrieves a set of documents (rows), matching the current request.
        Consumed when a request hits a collection/document endpoint
        (`/people/`).

        :param resource: resource being accessed. You should then use
                         the ``_datasource`` helper function to retrieve both
                         the db collection/table and base query (filter), if
                         any.
        :param req: an instance of ``eve.utils.ParsedRequest``. This contains
                    all the constraints that must be fulfilled in order to
                    satisfy the original request (where and sort parts, paging,
                    etc). Be warned that `where` and `sort` expresions will
                    need proper parsing, according to the syntax that you want
                    to support with your driver. For example ``eve.io.Mongo``
                    supports both Python and Mongo-like query syntaxes.
        """
        raise NotImplementedError

    def find_one(self, resource, **lookup):
        """Retrieves a single document/record. Consumed when a request hits an
        item endpoint (`/people/id/`).

        :param resource: resource being accessed. You should then use the
                         ``_datasource`` helper function to retrieve both the
                         db collection/table and base query (filter), if any.
        :param **lookup: the lookup fields. This will most likely be a record
                         id or, if alternate lookup is supported by the API,
                         the corresponding query.


        """
        raise NotImplementedError

    def find_list_of_ids(self, resource, ids, client_projection=None):
        """Retrieves a list of documents based on a list of primary keys
        The primary key is the field defined in `ID_FIELD`.
        This is a separate function to allow us to use per-database
        optimizations for this type of query

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
        """Inserts a document into a resource collection/table.

        :param resource: resource being accessed. You should then use
                         the ``_datasource`` helper function to retrieve both
                         the actual datasource name.
        :param doc_or_docs: json document or list of json documents to be added
                            to the database.

        .. versionchanged:: 0.0.6
            'document' param renamed to 'doc_or_docs', making support for bulk
            inserts apparent.
        """
        raise NotImplementedError

    def update(self, resource, id_, updates):
        """Updates a collection/table document/row.
        :param resource: resource being accessed. You should then use
                         the ``_datasource`` helper function to retrieve
                         the actual datasource name.
        :param id_: the unique id of the document.
        :param updates: json updates to be performed on the database document
                        (or row).
        """

        raise NotImplementedError

    def replace(self, resource, id_, document):
        """Replaces a collection/table document/row.
        :param resource: resource being accessed. You should then use
                         the ``_datasource`` helper function to retrieve
                         the actual datasource name.
        :param id_: the unique id of the document.
        :param document: the new json document

        .. versionadded:: 0.1.0
        """

        raise NotImplementedError

    def remove(self, resource, id_=None):
        """Removes a document/row or an entire set of documents/rows from a
        database collection/table.

        :param resource: resource being accessed. You should then use
                         the ``_datasource`` helper function to retrieve
                         the actual datasource name.
        :param id_: the unique id of the document to be removed. If `None`,
                    all the documents/rows in the collection/table should be
                    removed.

        """
        raise NotImplementedError

    def combine_queries(self, query_a, query_b):
        """
        Takes two db queries and applies db-specific syntax to produce
        the intersection.

        .. versionadded: 0.1.0
           Support for intelligent combination of db queries
        """
        raise NotImplementedError

    def get_value_from_query(self, query, field_name):
        """
        Parses the given potentially-complex query and returns the value
        being assigned to the field given in `field_name`.

        This mainly exists to deal with more complicated compound queries

        .. versionadded: 0.1.0
           Support for parsing values embedded in compound db queries
        """
        raise NotImplementedError

    def query_contains_field(self, query, field_name):
        """ For the specified field name, does the query contain it?
        Used know whether we need to parse a compound query

        .. versionadded: 0.1.0
           Support for parsing values embedded in compound db queries
        """
        raise NotImplementedError

    def _datasource(self, resource):
        """Returns a tuple with the actual name of the database
        collection/table, base query and projection for the resource being
        accessed.

        :param resource: resource being accessed.
        """

        return (config.SOURCES[resource]['source'],
                config.SOURCES[resource]['filter'],
                config.SOURCES[resource]['projection'])

    def _datasource_ex(self, resource, query=None, client_projection=None):
        """ Returns both db collection and exact query (base filter included)
        to which an API resource refers to

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

        datasource, filter_, projection_ = self._datasource(resource)
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

        if client_projection:
            # only allow fields which are included with the standard projection
            # for the resource (avoid sniffing of private fields)
            fields = dict(
                (field, 1) for (field) in [key for key in client_projection if
                                           key in projection_])
        else:
            fields = projection_

        # If the current HTTP method is in `public_methods` or
        # `public_item_methods`, skip the `auth_field` check

        if request.endpoint == 'collections_endpoint':
            # We need to check against `public_methods`
            public_method_list_to_check = 'public_methods'
        else:
            # We need to check against `public_item_methods`
            public_method_list_to_check = 'public_item_methods'

        # Is the HTTP method not public?
        resource_dict = config.DOMAIN[resource]
        if request.method not in resource_dict[public_method_list_to_check]:
            # We need to run the 'user-restricted resource access' check
            auth_field = resource_dict.get('auth_field', None)
            if auth_field and request.authorization and self.app.auth \
                    and query is not None:
                # If the auth_field *replaces* a field in the query,
                # and the values are /different/, deny the request
                # This prevents the auth_field condition from
                # overwriting the query (issue #77)
                request_auth_value = self.app.auth.request_auth_value
                auth_field_in_query = \
                    self.app.data.query_contains_field(query, auth_field)
                if auth_field_in_query and \
                        self.app.data.get_value_from_query(
                            query, auth_field) != request_auth_value:
                    abort(401, description=debug_error_message(
                        'Incompatible User-Restricted Resource request. '
                        'Request was for "%s"="%s" but `auth_field` '
                        'requires "%s"="%s".' % (
                            auth_field,
                            self.app.data.get_value_from_query(
                                query, auth_field),
                            auth_field,
                            request_auth_value)
                    ))
                else:
                    query = self.app.data.combine_queries(
                        query, {auth_field: request_auth_value}
                    )
        return datasource, query, fields
