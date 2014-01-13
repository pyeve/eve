# -*- coding: utf-8 -*-

"""
    eve.io.mongo.media
    ~~~~~~~~~~~~~~~~~~

    GridFS media storage for Eve-powered APIs.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
from flask import Flask
from eve.io.media import MediaStorage
from eve.io.mongo import Mongo

from gridfs import GridFS


class GridFSMediaStorage(MediaStorage):
    """ The GridFSMediaStorage class stores files into GridFS.

    ..versionadded:: 0.3
    """

    def __init__(self, app=None):
        """
        :param app: the flask application (eve itself). This can be used by
        the class to access, amongst other things, the app.config object to
        retrieve class-specific settings.
        """
        super(GridFSMediaStorage, self).__init__(app)

        self.validate()
        self._fs = None

    def validate(self):
        """ Make sure that the application data layer is a eve.io.mongo.Mongo
        instance.
        """
        if self.app is None:
            raise TypeError('Application object cannot be None')

        if not isinstance(self.app, Flask):
            raise TypeError('Application object must be a Eve application')

    def fs(self):
        """ Provides the instance-level GridFS instance, instantiating it if
        needed.
        """
        if self.app.data is None or not isinstance(self.app.data, Mongo):
            raise TypeError("Application data object must be of eve.io.Mongo "
                            "type.")

        if self._fs is None:
            self._fs = GridFS(self.app.data.driver.db)
        return self._fs

    def get(self, _id):
        """ Returns the file given by unique id. Returns None if no file was
        found.
        """
        _file = None
        try:
            _file = self.fs().get(_id)
        except:
            pass
        return _file

    def put(self, content, filename=None):
        """ Saves a new file in GridFS. Returns the unique id of the stored
        file.
        """
        return self.fs().put(content, filename=filename)

    def delete(self, _id):
        """ Deletes the file referenced by unique id.
        """
        self.fs().delete(_id)

    def exists(self, id_or_document):
        """ Returns True if a file referenced by the unique id or the query
        document already exists, False otherwise.

        Valid query: {'filename': 'file.txt'}
        """
        return self.fs().exists(id_or_document)
