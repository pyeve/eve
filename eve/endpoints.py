from utils import collection_link, config
from methods import get, getitem, post, patch, delete
from flask import request
from render import send_response


def collections_endpoint(url):
    resource = config.RESOURCES[url]
    response = None
    if request.method == 'GET':
        response = get(resource)
    elif request.method == 'POST':
        response = post(resource)
    elif request.method == 'DELETE':
        # TODO should we support this? it would delete all resource items
        pass

    if response:
        return send_response(resource, *response)


def item_endpoint(url, **lookup):
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
    if response:
        return send_response(resource, *response)


def home_endpoint():
    response = dict()
    links = list()
    for resource in config.DOMAIN.keys():
        links.append("<link rel='child' title='%s' href='%s' />" %
                     (config.URLS[resource], collection_link(resource)))
    response['links'] = links
    return send_response(None, response)
