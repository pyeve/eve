import datetime
import time
import simplejson as json
from flask import make_response, request
from bson.objectid import ObjectId
from eve.utils import date_to_str, config

_MIME_TYPES = [{'mime': ('application/json',), 'renderer': 'render_json'},
               {'mime': ('application/xml', 'text/xml', 'application/x-xml',),
                'renderer': 'render_xml'}]
_DEFAULT_MIME = 'application/json'


def send_response(resource, dct, last_modified=None, etag=None, status=200):
    mime, renderer = best_mime()
    response = {'response': dct}
    rendered = globals()[renderer](**response)
    resp = make_response(rendered, status)
    resp.mimetype = mime

    if request.method == 'GET':
        if resource:
            cache_control = config.DOMAIN[resource]['cache_control']
            expires = config.DOMAIN[resource]['cache_expires']
        else:
            cache_control = config.CACHE_CONTROL
            expires = config.CACHE_EXPIRES
        resp.headers.add('Cache-Control', cache_control)
        resp.expires = time.time() + expires

    if etag:
        resp.headers.add('ETag', etag)
    if last_modified:
        resp.headers.add('Last-Modified', date_to_str(last_modified))

    return resp


def best_mime():
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
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            # convert any datetime to RFC 1123 format
            return date_to_str(obj)
        elif isinstance(obj, (datetime.time, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def render_json(**data):
    return json.dumps(data, cls=APIEncoder)


def render_xml(**d):
    """Converts a dict to XML
    """

    xml = ''
    for k, v in d.items():
        if isinstance(v, datetime.datetime):
            v = date_to_str(v)
        elif isinstance(v, (datetime.time, datetime.date)):
            v = v.isoformat()
        if type(v) is dict:
            xml += "<%s>" % (k.rstrip('s'))
            xml += render_xml(**v)
            xml += "</%s>" % (k.rstrip('s'))
        else:
            original_list = False
            if type(v) is not list:
                v = [v]
            else:
                original_list = True
                xml += "<%s>" % k
            for value in v:
                if type(value) is dict:
                    xml += "<%s>" % (k.rstrip('s'))
                    xml += render_xml(**value)
                    xml += "</%s>" % (k.rstrip('s'))
                else:
                    xml += "<%s>%s</%s>" % (str(k.rstrip('s')), value,
                                            str(k.rstrip('s')))
            if original_list:
                xml += "</%s>" % k
    return xml
