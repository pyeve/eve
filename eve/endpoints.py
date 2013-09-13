# -*- coding: utf-8 -*-

"""
    eve.endpoints
    ~~~~~~~~~~~~~

    This module implements the API endpoints. Each endpoint (resource, item,
    home) invokes the appropriate method handler, returning its response
    to the client, properly rendered.

    :copyright: (c) 2013 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from eve.methods import get, getitem, post, patch, delete, delete_resource, put
from eve.methods.common import ratelimit
from eve.render import send_response
from eve.auth import requires_auth
from eve.utils import resource_uri, config, request_method, \
    debug_error_message
from flask import abort


def collections_endpoint(url):
    """ Resource endpoint handler

    :param url: the url that led here

    .. versionchanged:: 0.0.7
       Using 'utils.request_method' helper function now.

    .. versionchanged:: 0.0.6
       Support for HEAD requests

    .. versionchanged:: 0.0.2
        Support for DELETE resource method.
    """

    resource = config.RESOURCES[url]
    response = None
    method = request_method()
    if method in ('GET', 'HEAD'):
        response = get(resource)
    elif method == 'POST':
        response = post(resource)
    elif method == 'DELETE':
        response = delete_resource(resource)
    elif method == 'OPTIONS':
        send_response(resource, response)
    else:
        abort(405)
    return send_response(resource, response)


def item_endpoint(url, **lookup):
    """ Item endpoint handler

    :param url: the url that led here
    :param lookup: the query

    .. versionchanged:: 0.1.0
       Support for PUT method.

    .. versionchanged:: 0.0.7
       Using 'utils.request_method' helper function now.

    .. versionchanged:: 0.0.6
       Support for HEAD requests
    """
    resource = config.RESOURCES[url]
    response = None
    method = request_method()
    if method in ('GET', 'HEAD'):
        response = getitem(resource, **lookup)
    elif method == 'PATCH':
        response = patch(resource, **lookup)
    elif method == 'PUT':
        response = put(resource, **lookup)
    elif method == 'DELETE':
        response = delete(resource, **lookup)
    elif method == 'OPTIONS':
        send_response(resource, response)
    else:
        abort(405)
    return send_response(resource, response)


@ratelimit()
@requires_auth('home')
def home_endpoint():
    """ Home/API entry point. Will provide links to each available resource

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.
    """
    if config.HATEOAS:
        response = {}
        links = []
        for resource in config.DOMAIN.keys():
            links.append({'href': '%s' % resource_uri(resource),
                          'title': '%s' % config.URLS[resource]})
        response['_links'] = {'child': links}
        return send_response(None, (response,))
    else:
        abort(404, debug_error_message("HATEOAS is disabled so we have no data"
                                       " to display at the API homepage."))
