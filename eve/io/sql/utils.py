# -*- coding: utf-8 -*-

"""
    eve.io.sql.utils
    ~~~~~~~~~~~~

"""

import collections
from eve.utils import config


def dict_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            if k in d and isinstance(d[k], collections.Mapping):
                dict_update(d[k], v)
            else:
                d[k] = v
        else:
            d[k] = u[k]


def validate_filters(where, resource):
    allowed = config.DOMAIN[resource]['allowed_filters']
    if '*' not in allowed:
        for filt in where:
            key = filt.left.key
            if key not in allowed:
                return "filter on '%s' not allowed" % key
    return None
