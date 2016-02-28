# -*- coding: utf-8 -*-

"""
    eve.io.mongo
    ~~~~~~~~~~~~

    This package implements the MongoDB data layer.

    :copyright: (c) 2016 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

# flake8: noqa
from eve.io.mongo.mongo import Mongo, MongoJSONEncoder, create_index
from eve.io.mongo.validation import Validator
from eve.io.mongo.media import GridFSMediaStorage
