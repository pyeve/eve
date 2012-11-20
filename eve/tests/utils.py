# -*- coding: utf-8 -*-

import hashlib
from datetime import datetime, timedelta
from eve.tests import TestBase
from eve.utils import parse_request, str_to_date, config, weak_date, \
    date_to_str, querydef, document_etag


class TestUtils(TestBase):
    """ collection, document and home_link methods (and resource_uri, which is
    used by all of them) are tested in 'tests.methods' since we need an active
    flaskapp context
    """

    def setUp(self):
        super(TestUtils, self).setUp()
        self.dt_fmt = config.DATE_FORMAT
        self.datestr = 'Tue, 18 Sep 2012 10:12:30 UTC'
        self.valid = datetime.strptime(self.datestr, self.dt_fmt)
        self.etag = '56eaadbbd9fa287e7270cf13a41083c94f52ab9b'

    def test_parse_request_where(self):
        self.assertEqual(parse_request().where, None)
        self.assertEqual(parse_request({'where': 'hello'}).where, 'hello')

    def test_parse_request_sort(self):
        self.assertEqual(parse_request().sort, None)
        self.assertEqual(parse_request({'sort': 'hello'}).sort, 'hello')

    def test_parse_request_page(self):
        self.assertEqual(parse_request().page, 1)
        self.assertEqual(parse_request({'page': 2}).page, 2)
        self.assertEqual(parse_request({'page': -1}).page, 1)
        self.assertEqual(parse_request({'page': 0}).page, 1)
        self.assertEqual(parse_request({'page': 1.1}).page, 1)
        self.assertEqual(parse_request({'page': 'string'}).page, 1)

    def test_parse_request_max_results(self):
        default = config.PAGING_DEFAULT
        limit = config.PAGING_LIMIT
        self.assertEqual(parse_request().max_results, default)
        self.assertEqual(
            parse_request({'max_results': limit + 1}).max_results, limit)
        self.assertEqual(
            parse_request({'max_results': 2}).max_results, 2)
        self.assertEqual(
            parse_request({'max_results': -1}).max_results, default)
        self.assertEqual(
            parse_request({'max_results': 0}).max_results, default)
        self.assertEqual(
            parse_request({'max_results': 1.1}).max_results, 1)
        self.assertEqual(
            parse_request({'max_results': 'string'}).max_results, default)

    def test_parse_request_if_modified_since(self):
        ims = 'If-Modified-Since'
        self.assertEqual(parse_request().if_modified_since, None)
        self.assertEqual(parse_request(headers=None).if_modified_since, None)
        self.assertEqual(parse_request(
            headers={ims: self.datestr}).if_modified_since, self.valid +
            timedelta(seconds=1))
        self.assertRaises(ValueError,
                          parse_request,
                          headers={ims: 'not-a-date'})
        self.assertRaises(ValueError,
                          parse_request,
                          headers={ims: self.datestr.replace('UTC', 'GMT')})

    def test_parse_request_if_none_match(self):
        self.assertEqual(parse_request().if_none_match, None)
        self.assertEqual(parse_request(headers=None).if_none_match, None)
        self.assertEqual(parse_request(
            headers={'If-None-Match': self.etag}).if_none_match, self.etag)

    def test_parse_request_if_match(self):
        self.assertEqual(parse_request().if_match, None)
        self.assertEqual(parse_request(headers=None).if_match, None)
        self.assertEqual(parse_request(
            headers={'If-Match': self.etag}).if_match, self.etag)

    def test_weak_date(self):
        self.assertEqual(weak_date(self.datestr), self.valid +
                         timedelta(seconds=1))

    def test_str_to_date(self):
        self.assertEqual(str_to_date(self.datestr), self.valid)
        self.assertRaises(ValueError, str_to_date, 'not-a-date')
        self.assertRaises(ValueError, str_to_date,
                          self.datestr.replace('UTC', 'GMT'))

    def test_date_to_str(self):
        self.assertEqual(date_to_str(self.valid), self.datestr)

    def test_querydef(self):
        self.assertEqual(querydef(max_results=10), '?max_results=10')
        self.assertEqual(querydef(page=10), '?page=10')
        self.assertEqual(querydef(where='wherepart'), '?where=wherepart')
        self.assertEqual(querydef(sort='sortpart'), '?sort=sortpart')

        self.assertEqual(querydef(where='wherepart', sort='sortpart'),
                         '?where=wherepart&sort=sortpart')
        self.assertEqual(querydef(max_results=10, sort='sortpart'),
                         '?max_results=10&sort=sortpart')

    def test_document_etag(self):
        test = 'test this if you dare!'
        self.assertEqual(hashlib.sha1(test).hexdigest(), document_etag(test))
