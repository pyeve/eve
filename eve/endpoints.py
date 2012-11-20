# -*- coding: utf-8 -*-

"""
    eve.endpoints
    ~~~~~~~~~~~~~

    This module implements the API endpoints. Each endpoint (resource, item,
    home) invokes the appropriate method handler, returning its response
    to the client, properly rendered.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from methods import get, getitem, post, patch, delete
from flask import request, abort
from render import send_response
from .utils import collection_link, config


def collections_endpoint(url):
    """ Resource endpoint handler """

    # TODO should we support DELETE? At resource level, it would delete all
    # resource items at once. Maybe enable this option explicitly, via a
    # configuration setting.

    resource = config.RESOURCES[url]
    response = None
    if request.method == 'GET':
        response = get(resource)
    elif request.method == 'POST':
        response = post(resource)
    #elif request.method == 'DELETE':
    #    pass

    if response:
        return send_response(resource, *response)


def item_endpoint(url, **lookup):
    """ Item endpoint handler """
    resource = config.RESOURCES[url]
    response = None
    if request.method == 'GET':
        response = getitem(resource, **lookup)
    elif request.method == 'PATCH' or (request.method == 'POST' and
                                       request.headers.get(
                                           'X-HTTP-Method-Override')):
        response = patch(resource, **lookup)
    elif request.method == 'DELETE':
        response = delete(resource, **lookup)
    elif request.method == 'POST':
        # this method is enabled because we are supporting PATCH via POST with
        # X-HTTP-Method-Override (see above), therefore we must explicitly
        # handle this case.
        abort(405)
    if response:
        return send_response(resource, *response)


def home_endpoint():
    """ Home/API entry point. Will provide a list of links to each resource
    accessible.
    """
    response = dict()
    links = list()
    for resource in config.DOMAIN.keys():
        links.append("<link rel='child' title='%s' href='%s' />" %
                     (config.URLS[resource], collection_link(resource)))
    response['links'] = links
    return send_response(None, response)
