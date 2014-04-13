# -*- coding: utf-8 -*-

"""
    Normal settings file for Eve.

    Differently from a configuration file for an Eve application backed by Mongo we don't need
    to define the schema as this will be provided by the registerSchema decorator attached to the
    tables definition, see tables.py.

"""


# substitute <path for db file> with a real path to save the SQLite database file
SQLALCHEMY_DATABASE_URI = 'sqlite://<path for db file>'

# The following two lines will output the SQL statements executed by SQLAlchemy. Useful while debugging
# and in development. Turned off by default
# --------
# SQLALCHEMY_ECHO = True
# SQLALCHEMY_RECORD_QUERIES = True

DEBUG = True
 
DOMAIN = {
    'people': {
        'item_title': 'person',
        'additional_lookup': {
            'url': '[0-9]+',
            'field': '_id'
        },
        'cache_control': 'max-age=10,must-revalidate',
        'cache_expires': 10,
        'resource_methods': ['GET']
    }
}