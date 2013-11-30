# -*- coding: utf-8 -*-

"""
    eve.io.mongo
    ~~~~~~~~~~~~

    This package implements the MongoDB data layer.

    :copyright: (c) 2013 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

# flake8: noqa
from eve.io.mongo.mongo import Mongo, MongoJSONEncoder
from eve.io.mongo.validation import Validator
