# -*- coding: utf-8 -*-

"""
    eve.render
    ~~~~~~~~~~

    Implements proper, automated rendering for Eve responses.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import re
import time
import datetime
import simplejson as json
from werkzeug import utils
from functools import wraps
from eve.methods.common import get_rate_limit
from eve.utils import date_to_str, date_to_rfc1123, config, \
    debug_error_message, import_from_string
from flask import make_response, request, Response, current_app as app, abort

try:
    from collections import OrderedDict  # noqa
except ImportError:
    # Python 2.6 needs this back-port
    from backport_collections import OrderedDict


def raise_event(f):
    """ Raises both general and resource-level events after the decorated
    function has been executed. Returns both the flask.request object and the
    response payload to the callback.

    .. versionchanged:: 0.2
       Renamed 'on_<method>' hooks to 'on_post_<method>' for coherence
       with new 'on_pre_<method>' hooks.

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
        method = request.method
        if method in ('GET', 'POST', 'PATCH', 'DELETE', 'PUT'):
            event_name = 'on_post_' + method
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
                      status=200, headers=None):
    """ Prepares the response object according to the client request and
    available renderers, making sure that all accessory directives (caching,
    etag, last-modified) are present.

    :param resource: the resource involved.
    :param dct: the dict that should be sent back as a response.
    :param last_modified: Last-Modified header value.
    :param etag: ETag header value.
    :param status: response status.

    .. versionchanged:: 0.7
       Add support for regexes in X_DOMAINS_RE. Closes #660, #974.
       ETag value now surrounded by double quotes. Closes #794.

    .. versionchanged:: 0.6
       JSONP Support.

    .. versionchanged:: 0.4
       Support for optional extra headers.
       Fix #381. 500 instead of 404 if CORS is enabled.

    .. versionchanged:: 0.3
       Support for X_MAX_AGE.

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
        mime, renderer_cls = _best_mime()

        # invoke the render function and obtain the corresponding rendered item
        rendered = renderer_cls().render(dct)

        # JSONP
        if config.JSONP_ARGUMENT:
            jsonp_arg = config.JSONP_ARGUMENT
            if jsonp_arg in request.args and 'json' in mime:
                callback = request.args.get(jsonp_arg)
                rendered = "%s(%s)" % (callback, rendered)

        # build the main wsgi response object
        resp = make_response(rendered, status)
        resp.mimetype = mime

    # extra headers
    if headers:
        for header, value in headers:
            if header != 'Content-Type':
                resp.headers.add(header, value)

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
        resp.headers.add('ETag', '"' + etag + '"')
    if last_modified:
        resp.headers.add('Last-Modified', date_to_rfc1123(last_modified))

    # CORS
    origin = request.headers.get('Origin')
    if origin and (config.X_DOMAINS or config.X_DOMAINS_RE):
        if config.X_DOMAINS is None:
            domains = []
        elif isinstance(config.X_DOMAINS, str):
            domains = [config.X_DOMAINS]
        else:
            domains = config.X_DOMAINS

        if config.X_DOMAINS_RE is None:
            domains_re = []
        elif isinstance(config.X_DOMAINS_RE, str):
            domains_re = [config.X_DOMAINS_RE]
        else:
            domains_re = config.X_DOMAINS_RE

        # precompile regexes and ignore invalids
        domains_re_compiled = []
        for domain_re in domains_re:
            try:
                domains_re_compiled.append(re.compile(domain_re))
            except re.error:
                continue

        if config.X_HEADERS is None:
            headers = []
        elif isinstance(config.X_HEADERS, str):
            headers = [config.X_HEADERS]
        else:
            headers = config.X_HEADERS

        if config.X_EXPOSE_HEADERS is None:
            expose_headers = []
        elif isinstance(config.X_EXPOSE_HEADERS, str):
            expose_headers = [config.X_EXPOSE_HEADERS]
        else:
            expose_headers = config.X_EXPOSE_HEADERS

        # The only accepted value for Access-Control-Allow-Credentials header
        # is "true"
        allow_credentials = config.X_ALLOW_CREDENTIALS is True

        methods = app.make_default_options_response().headers.get('allow', '')

        if '*' in domains:
            resp.headers.add('Access-Control-Allow-Origin', origin)
            resp.headers.add('Vary', 'Origin')
        elif any(origin == domain for domain in domains):
            resp.headers.add('Access-Control-Allow-Origin', origin)
        elif any(domain.match(origin) for domain in domains_re_compiled):
            resp.headers.add('Access-Control-Allow-Origin', origin)
        else:
            resp.headers.add('Access-Control-Allow-Origin', '')
        resp.headers.add('Access-Control-Allow-Headers', ', '.join(headers))
        resp.headers.add('Access-Control-Expose-Headers',
                         ', '.join(expose_headers))
        resp.headers.add('Access-Control-Allow-Methods', methods)
        resp.headers.add('Access-Control-Max-Age', config.X_MAX_AGE)
        if allow_credentials:
            resp.headers.add('Access-Control-Allow-Credentials', "true")

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

    .. versionchanged:: 0.8
       Support for optional renderers via RENDERERS. XML and JSON
       configuration keywords removed.

    .. versionchanged:: 0.3
       Support for optional renderers via XML and JSON configuration keywords.
    """
    supported = []
    renders = {}
    for renderer_cls in app.config.get('RENDERERS'):
        renderer = import_from_string(renderer_cls)
        for mime_type in renderer.mime:
            supported.append(mime_type)
            renders[mime_type] = renderer

    if len(supported) == 0:
        abort(500, description=debug_error_message(
            'Configuration error: no supported mime types')
        )

    best_match = request.accept_mimetypes.best_match(supported) or \
        supported[0]
    return best_match, renders[best_match]


class Renderer(object):
    """ Base class for all the renderers. Renderer should set valid `mime`
    attr and have `.render()` method implemented.

    """
    mime = tuple()

    def render(self, data):
        raise NotImplementedError('Renderer .render() method is not '
                                  'implemented')


class JSONRenderer(Renderer):
    """ JSON renderer class based on `simplejson` package.

    """
    mime = ('application/json',)

    def render(self, data):
        """ JSON render function

        :param data: the data stream to be rendered as json.

        .. versionchanged:: 0.2
           Json encoder class is now inferred by the active data layer,
           allowing for customized, data-aware JSON encoding.

        .. versionchanged:: 0.1.0
           Support for optional HATEOAS.
        """
        set_indent = None

        # make pretty prints available
        if 'GET' in request.method and 'pretty' in request.args:
            set_indent = 4
        return json.dumps(data, indent=set_indent,
                          cls=app.data.json_encoder_class,
                          sort_keys=config.JSON_SORT_KEYS)


class XMLRenderer(Renderer):
    """ XML renderer class.

    """
    mime = ('application/xml', 'text/xml', 'application/x-xml',)
    tag = 'XML'

    def render(self, data):
        """ XML render function.

        :param data: the data stream to be rendered as xml.

        .. versionchanged:: 0.4
           Support for pagination info (_meta).

        .. versionchanged:: 0.2
           Use the new ITEMS configuration setting.

        .. versionchanged:: 0.1.0
           Support for optional HATEOAS.

        .. versionchanged:: 0.0.3
           Support for HAL-like hyperlinks and resource descriptors.
        """
        if isinstance(data, list):
            data = {config.ITEMS: data}

        xml = ''
        if data:
            xml += self.xml_root_open(data)
            xml += self.xml_add_links(data)
            xml += self.xml_add_meta(data)
            xml += self.xml_add_items(data)
            xml += self.xml_root_close()
        return xml

    @classmethod
    def xml_root_open(cls, data):
        """ Returns the opening tag for the XML root node. If the datastream
        includes informations about resource endpoints (href, title), they will
        be added as node attributes. The resource endpoint is then removed to
        allow for further processing of the datastream.

        :param data: the data stream to be rendered as xml.

        .. versionchanged:: 0.1.0
           Support for optional HATEOAS.

        .. versionchanged:: 0.0.6
           Links are now properly escaped.

        .. versionadded:: 0.0.3
        """
        links = data.get(config.LINKS)
        href = title = ''
        if links and 'self' in links:
            self_ = links.pop('self')
            href = ' href="%s" ' % utils.escape(self_['href'])
            if 'title' in self_:
                title = ' title="%s" ' % self_['title']
        return '<resource%s%s>' % (href, title)

    @classmethod
    def xml_add_meta(cls, data):
        """ Returns a meta node with page, total, max_results fields.

        :param data: the data stream to be rendered as xml.

        .. versionchanged:: 0.5
           Always return ordered items (#441).

        .. versionadded:: 0.4
        """
        xml = ''
        meta = []
        if data.get(config.META):
            ordered_meta = OrderedDict(sorted(data[config.META].items()))
            for name, value in ordered_meta.items():
                meta.append('<%s>%d</%s>' % (name, value, name))
        if meta:
            xml = '<%s>%s</%s>' % (config.META, ''.join(meta), config.META)
        return xml

    @classmethod
    def xml_add_links(cls, data):
        """ Returns as many <link> nodes as there are in the datastream. The
        links are then removed from the datastream to allow for further
        processing.

        :param data: the data stream to be rendered as xml.

        .. versionchanged:: 0.5
           Always return ordered items (#441).

        .. versionchanged:: 0.0.6
           Links are now properly escaped.

        .. versionadded:: 0.0.3
        """
        xml = ''
        chunk = '<link rel="%s" href="%s" title="%s" />'
        links = data.pop(config.LINKS, {})
        ordered_links = OrderedDict(sorted(links.items()))
        for rel, link in ordered_links.items():
            if isinstance(link, list):
                xml += ''.join([chunk % (rel, utils.escape(d['href']),
                                         utils.escape(d['title']))
                                for d in link])
            else:
                xml += ''.join(chunk % (rel, utils.escape(link['href']),
                                        link['title']))
        return xml

    @classmethod
    def xml_add_items(cls, data):
        """ When this function is called the datastream can only contain
         a `_items` list, or a dictionary. If a list, each item is a resource
        which rendered as XML. If a dictionary, it will be rendered as XML.

        :param data: the data stream to be rendered as xml.

        .. versionadded:: 0.0.3
        """
        try:
            xml = ''.join([cls.xml_item(item) for item in data[config.ITEMS]])
        except:
            xml = cls.xml_dict(data)
        return xml

    @classmethod
    def xml_item(cls, item):
        """ Represents a single resource (member of a collection) as XML.

        :param data: the data stream to be rendered as xml.

        .. versionadded:: 0.0.3
        """
        xml = cls.xml_root_open(item)
        xml += cls.xml_add_links(item)
        xml += cls.xml_dict(item)
        xml += cls.xml_root_close()
        return xml

    @classmethod
    def xml_root_close(cls):
        """ Returns the closing tag of the XML root node.

        .. versionadded:: 0.0.3
        """
        return '</resource>'

    @classmethod
    def xml_dict(cls, data):
        """ Renders a dict as XML.

        :param data: the data stream to be rendered as xml.

        .. versionchanged:: 0.5
           Always return ordered items (#441).

        .. versionchanged:: 0.2
           Leaf values are now properly escaped.

        .. versionadded:: 0.0.3
        """
        xml = ''
        ordered_items = OrderedDict(sorted(data.items()))
        for k, v in ordered_items.items():
            if isinstance(v, datetime.datetime):
                v = date_to_str(v)
            elif isinstance(v, (datetime.time, datetime.date)):
                v = v.isoformat()
            if not isinstance(v, list):
                v = [v]
            for value in v:
                if isinstance(value, dict):
                    links = cls.xml_add_links(value)
                    xml += "<%s>" % k
                    xml += cls.xml_dict(value)
                    xml += links
                    xml += "</%s>" % k
                else:
                    xml += "<%s>%s</%s>" % (k, utils.escape(value), k)
        return xml
