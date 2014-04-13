# -*- coding: utf-8 -*-

"""
    eve.io.sql.utils
    ~~~~~~~~~~~~

"""

import collections
from eve.utils import config


def dict_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = dict_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def validate_filters(where, resource):
    """ Report any filter which is not allowed by  `allowed_filters`

    :param where: the where clause, as list of SQLAlchemy binary expressions.
    :param resource: the resource being inspected.

    .. versionadded: 0.0.9
    """
    allowed = config.DOMAIN[resource]['allowed_filters']
    if '*' not in allowed:
        for filt in where:
            key = filt.left.key
            if key not in allowed:
                return "filter on '%s' not allowed" % key
    return None
