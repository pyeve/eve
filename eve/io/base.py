# -*- coding: utf-8 -*-

"""
    eve.io.base
    ~~~~~~~~~~~

    Standard interface implemented by Eve data layers.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from eve.utils import config
from flask import request


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

    .. versionchanged:: 0.0.6
       support for 'projections' has been added. For more information see
       http://docs.mongodb.org/manual/reference/glossary/#term-projection.
       While typically a MongoDB feature, other subclasses could decide to
       provide support for their own projection syntax.

    .. versionchanged:: 0.0.4
       the _datasource helper function has been added.
    """

    def __init__(self, app):
        """ Implements the Flask extension pattern.
        """
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
                query.update(filter_)
            else:
                query = filter_

        if client_projection:
            # only allow fields which are inluded with the standard projection
            # for the resource (avoid sniffing of private fields)
            fields = dict(
                (field, 1) for (field) in filter(projection_.has_key,
                                                 client_projection.keys()))
        else:
            fields = projection_

        # if 'user-restricted resource access' is enabled and there's an Auth
        # request active, add the username field to the query
        username_field = config.DOMAIN[resource].get('auth_username_field')
        if username_field and request.authorization and query is not None:
            query.update({username_field: request.authorization.username})

        return datasource, query, fields
