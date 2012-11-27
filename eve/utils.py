# -*- coding: utf-8 -*-

"""
    eve.utils
    ~~~~~~~~~

    Utility functions and classes.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import eve
import flask
import hashlib
from flask import request
from flask import current_app as app
from datetime import datetime, timedelta


class Config(object):
    """ Helper class used trorough the code to access configuration settings.
    If the main flaskapp object is not instantiated yet, returns the default
    setting in the eve __init__.py module, otherwise returns the flaskapp
    config value (which value might override the static defaults).
    """
    def __getattr__(self, name):
        try:
            return app.config.get(name)
        except:
            return getattr(eve, name)


# makes an instance of the Config helper class available to all the modules
# importing eve.utils.
config = Config()


class ParsedRequest(object):
    """ This class, by means of its attributes, describes a client request.
    """
    # `where` value of the query string (?where). Defaults to None.
    where = None

    # `sort` value of the query string (?sort). Defaults to None.
    sort = None

    # `page` value of the query string (?page). Defaults to 1.
    page = 1

    # `max_result` value of the query string (?max_results). Defaults to
    # `PAGING_DEFAULT`.
    max_results = config.PAGING_DEFAULT

    # `If-Modified-Since` request header value. Defaults to None.
    if_modified_since = None

    # `If-None_match` request header value. Defaults to None.
    if_none_match = None

    # `If-Match` request header value. Default to None.
    if_match = None


def parse_request(args=None, headers=None):
    """ Parses a client request, returning instance of :class:`ParsedRequest`
    containing relevant request data.

    :param args: request arguments. This is only used by the test suite as we
                 usually process flask request object.
    :param headers: request headers. Only used by the test suite as we usually
                    process flask request object.
    """
    if flask.has_request_context():
            args = request.args
            headers = request.headers

    r = ParsedRequest()

    if args:
        r.where = args.get('where')
        r.sort = args.get('sort')

        # TODO should probably return a 400 if 'page' is < 1 or non-numeric
        if 'page' in args:
            try:
                r.page = abs(int(args.get('page'))) or 1
            except ValueError:
                pass

        # TODO should probably return a 400 if 'max_results' < 1 or
        # non-numeric
        if 'max_results' in args:
            try:
                r.max_results = int(args.get('max_results'))
                if r.max_results > config.PAGING_LIMIT:
                    r.max_results = config.PAGING_LIMIT
                elif r.max_results <= 0:
                    r.max_results = config.PAGING_DEFAULT
            except ValueError:
                pass

    if headers:
        r.if_modified_since = weak_date(headers.get('If-Modified-Since'))
        # TODO if_none_match and if_match should probably be validated as
        # valid etags, returning 400 on fail. Not sure however since
        # we're just going to use these for string-type comparision
        r.if_none_match = headers.get('If-None-Match')
        r.if_match = headers.get('If-Match')

    return r


def weak_date(date):
    """ Returns a RFC-1123 string corresponding to a datetime value plus
    a 1 second timedelta. This is needed because when saved, documents
    LAST_UPDATED values have higher resolution than If-Modified-Since's, which
    is limited to seconds.

    :param date: the date to be adjusted.
    """
    return str_to_date(date) + timedelta(seconds=1) if date else None


def str_to_date(string):
    """ Converts a RFC-1123 string to the corresponding datetime value.

    :param string: the RFC-1123 string to convert to datetime value.
    """
    return datetime.strptime(string, config.DATE_FORMAT) if string else None


def date_to_str(date):
    """ Converts a datetime value to the corresponding RFC-1123 string.

    :param date: the datetime value to convert.
    """
    return datetime.strftime(date, config.DATE_FORMAT) if date else None


def collection_link(resource):
    """ Returns a link to a resource endpoint.

    :param resource: the resource name.
    """
    return ("<link rel='collection' title='%s' href='%s' />" %
            (config.URLS[resource], resource_uri(resource)))


def document_link(resource, document_id):
    """ Returns a link to a document endpoint.

    :param resource: the resource name.
    :param document_id: the document unique identifier.
    """
    title = config.DOMAIN[resource].get('item_title',
                                        resource.rstrip('s').capitalize())
    return ("<link rel='self' title='%s' href='%s%s/' />" %
            (title, resource_uri(resource), document_id))


def home_link():
    """ Returns a link to the API entry point/home page.
    """
    return "<link rel='parent' title='home' href='%s' />" % config.SERVER_NAME


def resource_uri(resource):
    """ Returns the absolute URI to a resource.

    :param resource: the resource name.
    """
    return '%s/%s/' % (config.SERVER_NAME, config.URLS[resource])


def querydef(max_results=config.PAGING_DEFAULT, where=None, sort=None,
             page=None):
    """ Returns a valid query string.

    :param max_results: `max_result` part of the query string. Defaults to
                        `PAGING_DEFAULT`
    :param where: `where` part of the query string. Defaults to None.
    :param sort: `sort` part of the query string. Defaults to None.
    :param page: `page` parte of the query string. Defaults to None.
    """
    where_part = '&where=%s' % where if where else ''
    sort_part = '&sort=%s' % sort if sort else ''
    page_part = '&page=%s' % page if page > 1 else ''
    max_results_part = 'max_results=%s' % max_results \
        if max_results != config.PAGING_DEFAULT else ''

    return ('?' + ''.join([max_results_part, where_part, sort_part,
                           page_part]).lstrip('&')).rstrip('?')


def document_etag(value):
    """ Computes and returns a valid ETag for the input value.

    :param value: the value to compute the ETag with.
    """
    h = hashlib.sha1()
    h.update(str(value))
    return h.hexdigest()
