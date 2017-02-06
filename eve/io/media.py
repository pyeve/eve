# -*- coding: utf-8 -*-

"""
    eve.io.media
    ~~~~~~~~~~~~

    Media storage for Eve-powered APIs.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""


class MediaStorage(object):
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

    def get(self, id_or_filename, resource=None):
        """ Opens the file given by name or unique id. Note that although the
        returned file is guaranteed to be a File object, it might actually be
        some subclass. Returns None if no file was found.
        """
        raise NotImplementedError

    def put(self, content, filename=None, content_type=None, resource=None):
        """ Saves a new file using the storage system, preferably with the name
        specified. If there already exists a file with this name name, the
        storage system may modify the filename as necessary to get a unique
        name. Depending on the storage system, a unique id or the actual name
        of the stored file will be returned. The content type argument is used
        to appropriately identify the file when it is retrieved.

        .. versionchanged:: 0.5
           Allow filename to be optional (#414).
        """
        raise NotImplementedError

    def delete(self, id_or_filename, resource=None):
        """ Deletes the file referenced by name or unique id. If deletion is
        not supported on the target storage system this will raise
        NotImplementedError instead
        """
        raise NotImplementedError

    def exists(self, id_or_filename, resource=None):
        """ Returns True if a file referenced by the given name or unique id
        already exists in the storage system, or False if the name is available
        for a new file.
        """
        raise NotImplementedError
