# -*- coding: utf-8 -*-
from io import BytesIO

"""
    eve.io.sql.media
    ~~~~~~~~~~~~

    Media storage for Eve-powered APIs.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""


class SQLBlobMediaStorage(object):
    """ The MediaStorage class provides a standardized API for storing files,
    along with a set of default behaviors that all other storage systems can
    inherit or override as necessary.

    ..versioneadded:: 0.3
    """

    def __init__(self, app=None):
        """
        :param app: the flask application (eve itself). This can be used by
        the class to access, amongst other things, the app.config object to
        retrieve class-specific settings.
        """
        self.app = app

    def get(self, content):
        """ Opens the file given by name or unique id. Note that although the
        returned file is guaranteed to be a File object, it might actually be
        some subclass. Returns None if no file was found.
        """
        return BytesIO(content)

    def put(self, content, filename=None, content_type=None):
        """ Saves a new file using the storage system, preferably with the name
        specified. If there already exists a file with this name name, the
        storage system may modify the filename as necessary to get a unique
        name. Depending on the storage system, a unique id or the actual name
        of the stored file will be returned. The content type argument is used
        to appropriately identify the file when it is retrieved.
        """
        content.stream.seek(0)
        return content.stream.read()

    def delete(self, id_or_filename):
        """ Deletes the file referenced by name or unique id. If deletion is
        not supported on the target storage system this will raise
        NotImplementedError instead
        """
        if not id_or_filename:  # there is nothing to remove
            return

    def exists(self, id_or_filename):
        """ Returns True if a file referenced by the given name or unique id
        already exists in the storage system, or False if the name is available
        for a new file.
        """
        raise NotImplementedError
