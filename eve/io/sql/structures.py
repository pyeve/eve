# -*- coding: utf-8 -*-

"""
    eve.io.sql.structures
    ~~~~~~~~~~~~

    These classes provide a middle layer to transform a SQLAlchemy query into a series of object
    that Eve understands and can be rendered as JSON.

"""

import collections
import copy
import flask.ext.sqlalchemy as flask_sqlalchemy
from eve.utils import config

object_mapper = flask_sqlalchemy.sqlalchemy.orm.object_mapper


class SQLAResult(collections.MutableMapping):
    """
    Represents a particular item to be returned by Eve. Eve expects a dictionary while SQLAlchemy gives us
    an object. This class provides an interface between the two requirements.

    :param result: the item to be rendered, as a SQLAlchemy object
    :param fields: the fields to be rendered, as a list of strings
    """
    def __init__(self, result, fields):
        self._result = result
        self._fields = [field for field in fields if getattr(self._result, field, None) is not None]

    def __getitem__(self, key):
        # TODO: composite primary key
        return getattr(self._result, key, None)

    def __setitem__(self, key, value):
        setattr(self._result, key, value)
        if key not in self._fields:
            self._fields.append(key)

    def __contains__(self, key):
        return key in self.keys()

    def __delitem__(self, key):
        pass

    def __iter__(self):
        for k in self.keys():
            yield k

    def __len__(self):
        return len(self.keys())

    def keys(self):
        return self._fields

    def _asdict(self):
        return dict(self)

    def copy(self):
        return copy.copy(self)


class SQLAResultCollection(object):
    """
    Collection of results. The object holds onto a Flask-SQLAlchemy query object and serves a generator off it.

    :param query: Base SQLAlchemy query object for the requested resource
    :param fields: fields to be rendered in the response, as a list of strings
    :param spec: filter to be applied to the query
    :param sort: sorting requirements
    :param max_results: number of entries to be returned per page
    :param page: page requested
    """
    def __init__(self, query, fields, **kwargs):
        self._query = query
        self._fields = fields
        self._spec = kwargs.get('spec')
        self._sort = kwargs.get('sort')
        self._max_results = kwargs.get('max_results')
        self._page = kwargs.get('page')
        if self._spec:
            self._query = self._query.filter(*self._spec)
        if self._sort:
            self._query = self._query.order_by(*self._sort)

        # save the count of items to an internal variables before applying the limit to the query as
        # that screws the count returned by it
        self._count = self._query.count()
        if self._max_results:
            self._query = self._query.limit(self._max_results)
            if self._page:
                self._query = self._query.offset((self._page - 1) * self._max_results)

    def __iter__(self):
        for i in self._query:
            yield SQLAResult(i, self._fields)

    def count(self):
        return self._count