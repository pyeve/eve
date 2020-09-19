# -*- coding: utf-8 -*-

"""
    eve.endpoints
    ~~~~~~~~~~~~~

    This module implements the API endpoints. Each endpoint (resource, item,
    home) invokes the appropriate method handler, returning its response
    to the client, properly rendered.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import re

from bson import tz_util
from flask import abort, request, current_app as app, Response

from eve.auth import requires_auth, resource_auth
from eve.methods import get, getitem, post, patch, delete, deleteitem, put
from eve.methods.common import ratelimit
from eve.render import send_response
from eve.utils import config, weak_date, date_to_rfc1123
import eve


def collections_endpoint(**lookup):
    """Resource endpoint handler

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
    method = request.method
    if method in ("GET", "HEAD"):
        response = get(resource, lookup)
    elif method == "POST":
        response = post(resource)
    elif method == "DELETE":
        response = delete(resource, lookup)
    elif method == "OPTIONS":
        send_response(resource, response)
    else:
        abort(405)
    return send_response(resource, response)


def item_endpoint(**lookup):
    """Item endpoint handler

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
    method = request.method
    if method in ("GET", "HEAD"):
        response = getitem(resource, **lookup)
    elif method == "PATCH":
        response = patch(resource, **lookup)
    elif method == "PUT":
        response = put(resource, **lookup)
    elif method == "DELETE":
        response = deleteitem(resource, **lookup)
    elif method == "OPTIONS":
        send_response(resource, response)
    else:
        abort(405)
    return send_response(resource, response)


@ratelimit()
@requires_auth("home")
def home_endpoint():
    """Home/API entry point. Will provide links to each available resource

    .. versionchanged:: 0.5
       Resource URLs are relative to API root.
       Don't list internal resources.

    .. versionchanged:: 0.4
       Prevent versioning collections from being added in links.

    .. versionchanged:: 0.2
       Use new 'resource_title' setting for link titles.

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.
    """
    response = {}
    if config.INFO:
        info = {}
        info["server"] = "Eve"
        info["version"] = eve.__version__
        if config.API_VERSION:
            info["api_version"] = config.API_VERSION
        response[config.INFO] = info

    if config.HATEOAS:
        links = []
        for resource in config.DOMAIN.keys():
            internal = config.DOMAIN[resource]["internal_resource"]
            if not resource.endswith(config.VERSIONS):
                if not bool(internal):
                    links.append(
                        {
                            "href": "%s" % config.URLS[resource],
                            "title": "%s" % config.DOMAIN[resource]["resource_title"],
                        }
                    )
        if config.SCHEMA_ENDPOINT is not None:
            links.append(
                {
                    "href": "%s" % config.SCHEMA_ENDPOINT,
                    "title": "%s" % config.SCHEMA_ENDPOINT,
                }
            )

        response[config.LINKS] = {"child": links}
        return send_response(None, (response,))
    else:
        return send_response(None, (response,))


def error_endpoint(error):
    """Response returned when an error is raised by the API (e.g. my means of
    an abort(4xx).
    """
    headers = []

    try:
        headers.append(error.response.headers)
    except AttributeError:
        pass

    try:
        if error.www_authenticate is not None:
            headers.append(error.www_authenticate)
    except AttributeError:
        pass

    response = {
        config.STATUS: config.STATUS_ERR,
        config.ERROR: {"code": error.code, "message": error.description},
    }
    return send_response(None, (response, None, None, error.code, headers))


def _resource():
    return request.endpoint.split("|")[0]


@requires_auth("media")
def media_endpoint(_id):
    """This endpoint is active when RETURN_MEDIA_AS_URL is True. It retrieves
    a media file and streams it to the client.

    .. versionadded:: 0.6
    """
    if request.method == "OPTIONS":
        return send_response(None, (None))

    file_ = app.media.get(_id)
    if file_ is None:
        return abort(404)

    headers = {
        "Last-Modified": date_to_rfc1123(file_.upload_date),
        "Content-Length": file_.length,
        "Accept-Ranges": "bytes",
    }

    range_header = request.headers.get("Range")
    if range_header:
        status = 206

        size = file_.length
        try:
            m = re.search(r"(\d+)-(\d*)", range_header)
            begin, end = m.groups()
            begin = int(begin)
            end = int(end)
        except:
            begin, end = 0, None

        length = size - begin
        if end is not None:
            length = end - begin + 1

        file_.seek(begin)

        data = file_.read(length)
        headers["Content-Range"] = "bytes {0}-{1}/{2}".format(
            begin, begin + length - 1, size
        )
    else:
        if_modified_since = weak_date(request.headers.get("If-Modified-Since"))
        if if_modified_since:
            if not if_modified_since.tzinfo:
                if_modified_since = if_modified_since.replace(tzinfo=tz_util.utc)

            if if_modified_since > file_.upload_date:
                return Response(status=304)

        data = file_
        status = 200

    response = Response(
        data,
        status=status,
        headers=headers,
        mimetype=file_.content_type,
        direct_passthrough=True,
    )

    return send_response(None, (response,))


@requires_auth("resource")
def schema_item_endpoint(resource):
    """This endpoint is active when SCHEMA_ENDPOINT != None. It returns the
    requested resource's schema definition in JSON format.
    """
    resource_config = app.config["DOMAIN"].get(resource)
    if not resource_config or resource_config.get("internal_resource") is True:
        return abort(404)

    return send_response(None, (resource_config["schema"],))


@requires_auth("home")
def schema_collection_endpoint():
    """This endpoint is active when SCHEMA_ENDPOINT != None. It returns the
    schema definition for all public or request authenticated resources in
    JSON format.
    """
    schemas = {}
    for resource_name, resource_config in app.config["DOMAIN"].items():
        # skip versioned shadow collections
        if resource_name.endswith(config.VERSIONS):
            continue
        # skip internal resources
        internal = resource_config.get("internal_resource", False)
        if internal:
            continue
        # skip resources for which request does not have read authorization
        auth = resource_auth(resource_name)
        if auth and request.method not in resource_config["public_methods"]:
            roles = list(resource_config["allowed_roles"])
            roles += resource_config["allowed_read_roles"]
            if not auth.authorized(roles, resource_name, request.method):
                continue
        # otherwise include this resource in domain wide schema response
        schemas[resource_name] = resource_config["schema"]

    return send_response(None, (schemas,))
