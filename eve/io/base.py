"""
    eve.io.base
    ~~~~~~~~~~~

    Standard interface implemented by Eve data layers.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from ..utils import config


class DataLayer(object):
    """ Base data layer class. Defines the interface that actual data-access
    classes, being subclasses, must implement. Admittedly, the interface is a
    Mongo rip-off. See the io.mongo package for an implementation example.
    """

    def __init__(self, app):
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None

    def init_app(self, app):
        raise NotImplementedError

    def find(self, resource, where=None, sort=None, page=1,
             max_results=config.PAGING_DEFAULT,
             if_modified_since=None):
        raise NotImplementedError

    def find_one(self, resource, **lookup):
        raise NotImplementedError

    def insert(self, resource, document):
        raise NotImplementedError

    def update(self, resource, id_, updates):
        raise NotImplementedError

    def remove(self, resource, id_):
        raise NotImplementedError
