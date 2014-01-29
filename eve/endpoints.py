# -*- coding: utf-8 -*-

"""
    eve.endpoints
    ~~~~~~~~~~~~~

    This module implements the API endpoints. Each endpoint (resource, item,
    home) invokes the appropriate method handler, returning its response
    to the client, properly rendered.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from eve.methods import get, getitem, post, patch, delete, delete_resource, put
from eve.methods.common import ratelimit
from eve.render import send_response
from eve.auth import requires_auth
from eve.utils import resource_uri, config, request_method, \
    debug_error_message
from flask import abort, request


def collections_endpoint(**lookup):
    """ Resource endpoint handler

    :param url: the url that led here

    .. versionchanged:: 0.3
       Pass lookup query down to delete_resource, so it can properly process
       sub-resources.

    .. versionchanged:: 0.2
       Relying on request.endpoint to retrieve the resource being consumed.

    .. versionchanged:: 0.1.1
       Relying on request.path for determining the current endpoint url.

    .. versionchanged:: 0.0.7
       Using 'utils.request_method' helper function now.

    .. versionchanged:: 0.0.6
       Support for HEAD requests

    .. versionchanged:: 0.0.2
        Support for DELETE resource method.
    """

    resource = _resource()
    response = None
    method = request_method()
    if method in ('GET', 'HEAD'):
        response = get(resource, lookup)
    elif method == 'POST':
        response = post(resource)
    elif method == 'DELETE':
        response = delete_resource(resource, lookup)
    elif method == 'OPTIONS':
        send_response(resource, response)
    else:
        abort(405)
    return send_response(resource, response)


def item_endpoint(**lookup):
    """ Item endpoint handler

    :param url: the url that led here
    :param lookup: sub resource query

    .. versionchanged:: 0.2
       Support for sub-resources.
       Relying on request.endpoint to retrieve the resource being consumed.

    .. versionchanged:: 0.1.1
       Relying on request.path for determining the current endpoint url.

    .. versionchanged:: 0.1.0
       Support for PUT method.

    .. versionchanged:: 0.0.7
       Using 'utils.request_method' helper function now.

    .. versionchanged:: 0.0.6
       Support for HEAD requests
    """
    resource = _resource()
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

    .. versionchanged:: 0.2
       Use new 'resource_title' setting for link titles.

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.
    """
    if config.HATEOAS:
        response = {}
        links = []
        for resource in config.DOMAIN.keys():
            links.append({'href': '%s' % resource_uri(resource),
                          'title': '%s' %
                          config.DOMAIN[resource]['resource_title']})
        response[config.LINKS] = {'child': links}
        return send_response(None, (response,))
    else:
        abort(404, debug_error_message("HATEOAS is disabled so we have no data"
                                       " to display at the API homepage."))


def _resource():
    return request.endpoint.split('|')[0]
