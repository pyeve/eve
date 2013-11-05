# -*- coding: utf-8 -*-)

"""
    eve.render
    ~~~~~~~~~~

    Implements proper, automated rendering for Eve responses.

    :copyright: (c) 2013 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import time
import datetime
import simplejson as json
from werkzeug import utils
from functools import wraps
from eve.methods.common import get_rate_limit
from eve.utils import date_to_str, config, request_method
from flask import make_response, request, Response, current_app as app

# mapping between supported mime types and render functions.
_MIME_TYPES = [{'mime': ('application/json',), 'renderer': 'render_json'},
               {'mime': ('application/xml', 'text/xml', 'application/x-xml',),
                'renderer': 'render_xml'}]
_DEFAULT_MIME = 'application/json'


def raise_event(f):
    """ Raises both general and resource-level events after the decorated
    function has been executed. Returns both the flask.request object and the
    response payload to the callback.

    .. versionchanged:: 0.1.0
       Support for PUT.

    .. versionchanged:: 0.0.9
       To emphasize the fact that they are tied to a method, in `on_<method>`
       events, <method> is now uppercase.

    .. versionadded:: 0.0.6
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        r = f(*args, **kwargs)
        method = request_method()
        if method in ('GET', 'POST', 'PATCH', 'DELETE', 'PUT'):
            event_name = 'on_' + method
            resource = args[0] if args else None
            # general hook
            getattr(app, event_name)(resource, request, r)
            if resource:
                # resource hook
                getattr(app, event_name + '_' + resource)(request, r)
        return r
    return decorated


@raise_event
def send_response(resource, response):
    """ Prepares the response for the client.

    :param resource: the resource involved.
    :param response: either a flask.Response object or a tuple. The former will
                     simply be forwarded to the client. If the latter a proper
                     response will be prepared, according to directives within
                     the tuple.

    .. versionchanged:: 0.0.6
       Support for HEAD requests.

    .. versionchanged:: 0.0.5
       Handling the case where response is None. Happens when the request
       method is 'OPTIONS', most likely while processing a CORS 'preflight'
       request.

    .. versionchanged:: 0.0.4
       Now a simple dispatcher. Moved the response preparation logic to
       ``_prepare_response``.
    """
    if isinstance(response, Response):
        return response
    else:
        return _prepare_response(resource, *response if response else [None])


def _prepare_response(resource, dct, last_modified=None, etag=None,
                      status=200):
    """ Prepares the response object according to the client request and
    available renderers, making sure that all accessory directives (caching,
    etag, last-modified) are present.

    :param resource: the resource involved.
    :param dct: the dict that should be sent back as a response.
    :param last_modified: Last-Modified header value.
    :param etag: ETag header value.
    :param status: response status.

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.

    .. versionchanged:: 0.0.9
       Support for Python 3.3.

    .. versionchanged:: 0.0.7
       Support for Rate-Limiting.

    .. versionchanged:: 0.0.6
       Support for HEAD requests.

    .. versionchanged:: 0.0.5
       Support for Cross-Origin Resource Sharing (CORS).

    .. versionadded:: 0.0.4
    """
    if request.method == 'OPTIONS':
        resp = app.make_default_options_response()
    else:
        # obtain the best match between client's request and available mime
        # types, along with the corresponding render function.
        mime, renderer = _best_mime()

        # invoke the render function and obtain the corresponding rendered item
        rendered = globals()[renderer](dct)

        # build the main wsgi rensponse object
        resp = make_response(rendered, status)
        resp.mimetype = mime

    # cache directives
    if request.method in ('GET', 'HEAD'):
        if resource:
            cache_control = config.DOMAIN[resource]['cache_control']
            expires = config.DOMAIN[resource]['cache_expires']
        else:
            cache_control = config.CACHE_CONTROL
            expires = config.CACHE_EXPIRES
        if cache_control:
            resp.headers.add('Cache-Control', cache_control)
        if expires:
            resp.expires = time.time() + expires

    # etag and last-modified
    if etag:
        resp.headers.add('ETag', etag)
    if last_modified:
        resp.headers.add('Last-Modified', date_to_str(last_modified))

    # CORS
    if 'Origin' in request.headers and config.X_DOMAINS is not None:
        if isinstance(config.X_DOMAINS, str):
            domains = [config.X_DOMAINS]
        else:
            domains = config.X_DOMAINS

        if config.X_HEADERS is None:
            headers = []
        elif isinstance(config.X_HEADERS, str):
            headers = [config.X_HEADERS]
        else:
            headers = config.X_HEADERS

        methods = app.make_default_options_response().headers['allow']
        resp.headers.add('Access-Control-Allow-Origin', ', '.join(domains))
        resp.headers.add('Access-Control-Allow-Headers', ', '.join(headers))
        resp.headers.add('Access-Control-Allow-Methods', methods)
        resp.headers.add('Access-Control-Allow-Max-Age', 21600)

    # Rate-Limiting
    limit = get_rate_limit()
    if limit and limit.send_x_headers:
        resp.headers.add('X-RateLimit-Remaining', str(limit.remaining))
        resp.headers.add('X-RateLimit-Limit', str(limit.limit))
        resp.headers.add('X-RateLimit-Reset', str(limit.reset))

    return resp


def _best_mime():
    """ Returns the best match between the requested mime type and the
    ones supported by Eve. Along with the mime, also the corresponding
    render function is returns.
    """
    supported = []
    renders = {}
    for mime in _MIME_TYPES:
        for mime_type in mime['mime']:
            supported.append(mime_type)
            renders[mime_type] = mime['renderer']
    best_match = request.accept_mimetypes.best_match(supported) or \
        _DEFAULT_MIME
    return best_match, renders[best_match]


def render_json(data):
    """ JSON render function

    .. versionchanged:: 0.2
       Json encoder class is now inferred by the active data layer, allowing
       for customized, data-aware JSON encoding.

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.
    """
    return json.dumps(data, cls=app.data.json_encoder_class)


def render_xml(data):
    """ XML render function.

    :param data: the data stream to be rendered as xml.

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.

    .. versionchanged:: 0.0.3
       Support for HAL-like hyperlinks and resource descriptors.
    """
    if isinstance(data, list):
        data = {'_items': data}

    xml = ''
    if data:
        xml += xml_root_open(data)
        xml += xml_add_links(data)
        xml += xml_add_items(data)
        xml += xml_root_close()
    return xml


def xml_root_open(data):
    """ Returns the opening tag for the XML root node. If the datastream
    includes informations about resource endpoints (href, title), they will
    be added as node attributes. The resource endpoint is then removed to allow
    for further processing of the datastream.

    :param data: the data stream to be rendered as xml.

    .. versionchanged:: 0.1.0
       Support for optional HATEOAS.

    .. versionchanged:: 0.0.6
       Links are now properly escaped.

    .. versionadded:: 0.0.3
    """
    links = data.get('_links')
    href = title = ''
    if links and 'self' in links:
        self_ = links.pop('self')
        href = ' href="%s" ' % utils.escape(self_['href'])
        if 'title' in self_:
            title = ' title="%s" ' % self_['title']
    return '<resource%s%s>' % (href, title)


def xml_add_links(data):
    """ Returns as many <link> nodes as there are in the datastream. The links
    are then removed from the datastream to allow for further processing.

    :param data: the data stream to be rendered as xml.

    .. versionchanged:: 0.0.6
       Links are now properly escaped.

    .. versionadded:: 0.0.3
    """
    xml = ''
    chunk = '<link rel="%s" href="%s" title="%s" />'
    links = data.pop('_links', {})
    for rel, link in links.items():
        if isinstance(link, list):
            xml += ''.join([chunk % (rel, utils.escape(d['href']), d['title'])
                            for d in link])
        else:
            xml += ''.join(chunk % (rel, utils.escape(link['href']),
                                    link['title']))
    return xml


def xml_add_items(data):
    """ When this function is called the datastream can only contain a `_items`
    list, or a dictionary. If a list, each item is a resource which rendered as
    XML. If a dictionary, it will be rendered as XML.

    :param data: the data stream to be rendered as xml.

    .. versionadded:: 0.0.3
    """
    try:
        xml = ''.join([xml_item(item) for item in data['_items']])
    except:
        xml = xml_dict(data)
    return xml


def xml_item(item):
    """ Represents a single resource (member of a collection) as XML.

    :param data: the data stream to be rendered as xml.

    .. versionadded:: 0.0.3
    """
    xml = xml_root_open(item)
    xml += xml_add_links(item)
    xml += xml_dict(item)
    xml += xml_root_close()
    return xml


def xml_root_close():
    """ Returns the closing tag of the XML root node.

    .. versionadded:: 0.0.3
    """
    return '</resource>'


def xml_dict(data):
    """ Renders a dict as XML.

    :param data: the data stream to be rendered as xml.

    .. versionadded:: 0.0.3
    """
    xml = ''
    for k, v in data.items():
        if isinstance(v, datetime.datetime):
            v = date_to_str(v)
        elif isinstance(v, (datetime.time, datetime.date)):
            v = v.isoformat()
        if not isinstance(v, list):
            v = [v]
        for value in v:
            if isinstance(value, dict):
                links = xml_add_links(value)
                xml += "<%s>" % k
                xml += xml_dict(value)
                xml += links
                xml += "</%s>" % k
            else:
                xml += "<%s>%s</%s>" % (k, value, k)
    return xml
