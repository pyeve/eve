# -*- coding: utf-8 -*-

"""
    eve.io.mongo.flask_pymongo
    ~~~~~~~~~~~~~~~~~~~

    Flask extension to create Mongo connection and database based on
    configuration.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app
from pymongo import MongoClient, uri_parser


class PyMongo(object):
    """
    Creates Mongo connection and database based on Flask configuration.
    """

    def __init__(self, app, config_prefix='MONGO'):
        if 'pymongo' not in app.extensions:
            app.extensions['pymongo'] = {}

        if config_prefix in app.extensions['pymongo']:
            raise Exception('duplicate config_prefix "%s"' % config_prefix)

        self.config_prefix = config_prefix

        def key(suffix):
            return '%s_%s' % (config_prefix, suffix)

        def config_to_kwargs(mapping):
            """
            Convert config options to kwargs according to provided mapping
            information.
            """
            kwargs = {}
            for option, arg in mapping.items():
                if key(option) in app.config:
                    kwargs[arg] = app.config[key(option)]
            return kwargs

        app.config.setdefault(key('HOST'), 'localhost')
        app.config.setdefault(key('PORT'), 27017)
        app.config.setdefault(key('DBNAME'), app.name)
        app.config.setdefault(key('WRITE_CONCERN'), {'w': 1})
        client_kwargs = {
            'appname': app.name,
            'connect': True,
            'tz_aware': True,
        }
        if key('OPTIONS') in app.config:
            client_kwargs.update(app.config[key('OPTIONS')])

        if key('WRITE_CONCERN') in app.config:
            # w, wtimeout, j and fsync
            client_kwargs.update(app.config[key('WRITE_CONCERN')])

        uri_parser.validate_options(client_kwargs)

        if key('URI') in app.config:
            host = app.config[key('URI')]
            # raises an exception if uri is invalid
            mongo_settings = uri_parser.parse_uri(host)
            dbname = mongo_settings.get('database')
            if not dbname:
                dbname = app.config[key('DBNAME')]
        else:
            dbname = app.config[key('DBNAME')]
            host = app.config[key('HOST')]
            client_kwargs['port'] = app.config[key('PORT')]

        client_kwargs['host'] = host

        if key('DOCUMENT_CLASS') in app.config:
            client_kwargs['document_class'] = app.config[key('DOCUMENT_CLASS')]

        cx = MongoClient(**client_kwargs)
        db = cx[dbname]

        if key('USERNAME') in app.config:
            app.config.setdefault(key('PASSWORD'), None)
            username = app.config[key('USERNAME')]
            password = app.config[key('PASSWORD')]
            auth = (username, password)
            if any(auth) and not all(auth):
                raise Exception(
                    'Must set both USERNAME and PASSWORD or neither')
            if any(auth):
                auth_mapping = {
                    'AUTH_MECHANISM': 'mechanism',
                    'AUTH_SOURCE': 'source',
                    'AUTH_MECHANISM_PROPERTIES': 'authMechanismProperties',
                }
                auth_kwargs = config_to_kwargs(auth_mapping)
                db.authenticate(username, password, **auth_kwargs)

        app.extensions['pymongo'][config_prefix] = (cx, db)

    @property
    def cx(self):
        """
        Automatically created :class:`~pymongo.Connection` object corresponding
        to the provided configuration parameters.
        """
        if self.config_prefix not in current_app.extensions['pymongo']:
            raise Exception('flask_pymongo extensions is not initialized')
        return current_app.extensions['pymongo'][self.config_prefix][0]

    @property
    def db(self):
        """
        Automatically created :class:`~pymongo.Database` object
        corresponding to the provided configuration parameters.
        """
        if self.config_prefix not in current_app.extensions['pymongo']:
            raise Exception('flask_pymongo extensions is not initialized')
        return current_app.extensions['pymongo'][self.config_prefix][1]
