# -*- coding: utf-8 -*-)

"""
    eve.render
    ~~~~~~~~~~

    Implements proper, automated rendering for Eve responses.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import datetime
import time
import simplejson as json
from flask import make_response, request
from bson.objectid import ObjectId
from eve.utils import date_to_str, config

# mapping between supported mime types and render functions.
_MIME_TYPES = [{'mime': ('application/json',), 'renderer': 'render_json'},
               {'mime': ('application/xml', 'text/xml', 'application/x-xml',),
                'renderer': 'render_xml'}]
_DEFAULT_MIME = 'application/json'


def send_response(resource, dct, last_modified=None, etag=None, status=200):
    """ Prepares the response object according to the client request and
    available renderers, making sure that all accessory directives (caching,
    etag, last-modified) are present.

    :param resource: the resource involved.
    :param dct: the dict that should be sent back as a response.
    :param last_modified: Last-Modified header value.
    :param etag: ETag header value.
    :param status: response status.
    """
    # obtain the best match between client's request and available mime types,
    # along with the corresponding render function.
    mime, renderer = _best_mime()

    # invoke the render function and obtain the corresponding rendered item
    rendered = globals()[renderer](**dct)

    # build the main wsgi rensponse object
    resp = make_response(rendered, status)
    resp.mimetype = mime

    # cache directives
    if request.method == 'GET':
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

    return resp


def _best_mime():
    """ Returns the best match between the requested mime type and the
    ones supported by Eve. Along with the mime, also the corresponding
    render function is returns.
    """
    supported = list()
    renders = dict()
    for mime in _MIME_TYPES:
        for mime_type in mime['mime']:
            supported.append(mime_type)
            renders[mime_type] = mime['renderer']
    best_match = request.accept_mimetypes.best_match(supported) or \
        _DEFAULT_MIME
    return best_match, renders[best_match]


class APIEncoder(json.JSONEncoder):
    """ Propretary JSONEconder subclass used by the json render function.
    This is needed to address the encoding of special values.
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            # convert any datetime to RFC 1123 format
            return date_to_str(obj)
        elif isinstance(obj, (datetime.time, datetime.date)):
            # should not happen since the only supported date-like format
            # supported at dmain schema level is 'datetime' .
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            # BSON/Mongo ObjectId is rendered as a string
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def render_json(**data):
    """ JSON render function
    """
    return json.dumps(data, cls=APIEncoder)


def render_xml(**data):
    """ XML render function.

    :param data: the data stream to be rendered as xml.

    .. versionchanged:: 0.0.3
       Support for HAL-like hyperlinks and resource descriptors.
    """
    if data:
        xml = xml_root_open(data)
        xml += xml_add_links(data)
        xml += xml_add_items(data)
        xml += xml_root_close()
    return '' or xml


def xml_root_open(data):
    """ Returns the opening tag for the XML root node. If the datastream
    includes informations about resource endpoints (href, title), they will
    be added as node attributes. The resource endpoint is then removed to allow
    for further processing of the datastream.

    :param data: the data stream to be rendered as xml.

    .. versionadded:: 0.0.3
    """
    links = data.get('_links')
    href = title = ''
    if links and 'self' in links:
        self_ = links.pop('self')
        href = ' href="%s" ' % self_['href']
        if 'title' in self_:
            title = ' title="%s" ' % self_['title']
    return '<resource%s%s>' % (href, title)


def xml_add_links(data):
    """ Returns as many <link> nodes as there are in the datastream. The links
    are then removed from the datastream to allow for further processing.

    :param data: the data stream to be rendered as xml.

    .. versionadded:: 0.0.3
    """
    chunk = '<link rel="%s" href="%s" title="%s" />'
    links = data.pop('_links', {})
    xml = ''
    for rel, link in links.items():
        if isinstance(link, list):
            xml += ''.join([chunk % (rel, d['href'], d['title']) for d in
                            link])
        else:
            xml += ''.join(chunk % (rel, link['href'], link['title']))
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
