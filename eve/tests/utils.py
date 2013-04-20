# -*- coding: utf-8 -*-

import hashlib
from bson.json_util import dumps
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
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).where, None)
        with self.app.test_request_context('/?where=hello'):
            self.assertEqual(parse_request(self.known_resource).where, 'hello')

    def test_parse_request_sort(self):
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).sort, None)
        with self.app.test_request_context('/?sort=hello'):
            self.assertEqual(parse_request(self.known_resource).sort, 'hello')

    def test_parse_request_page(self):
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).page, 1)
        with self.app.test_request_context('/?page=2'):
            self.assertEqual(parse_request(self.known_resource).page, 2)
        with self.app.test_request_context('/?page=-1'):
            self.assertEqual(parse_request(self.known_resource).page, 1)
        with self.app.test_request_context('/?page=0'):
            self.assertEqual(parse_request(self.known_resource).page, 1)
        with self.app.test_request_context('/?page=1.1'):
            self.assertEqual(parse_request(self.known_resource).page, 1)
        with self.app.test_request_context('/?page=string'):
            self.assertEqual(parse_request(self.known_resource).page, 1)

    def test_parse_request_max_results(self):
        default = config.PAGINATION_DEFAULT
        limit = config.PAGINATION_LIMIT
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).max_results, default)
        with self.app.test_request_context('/?max_results=%d' % (limit+1)):
            self.assertEqual(parse_request(self.known_resource).max_results, limit)
        with self.app.test_request_context('/?max_results=2'):
            self.assertEqual(parse_request(self.known_resource).max_results, 2)
        with self.app.test_request_context('/?max_results=-1'):
            self.assertEqual(parse_request(self.known_resource).max_results, default)
        with self.app.test_request_context('/?max_results=0'):
            self.assertEqual(parse_request(self.known_resource).max_results, default)
        with self.app.test_request_context('/?max_results=1.1'):
            self.assertEqual(parse_request(self.known_resource).max_results, 1)
        with self.app.test_request_context('/?max_results=string'):
            self.assertEqual(parse_request(self.known_resource).max_results, default)

    def test_parse_request_max_results_disabled_pagination(self):
        self.app.config['DOMAIN'][self.known_resource]['pagination'] = False
        default = 0
        limit = config.PAGINATION_LIMIT
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).max_results, default)
        with self.app.test_request_context('/?max_results=%d' % (limit+1)):
            self.assertEqual(parse_request(self.known_resource).max_results, limit+1)
        with self.app.test_request_context('/?max_results=2'):
            self.assertEqual(parse_request(self.known_resource).max_results, 2)
        with self.app.test_request_context('/?max_results=-1'):
            self.assertEqual(parse_request(self.known_resource).max_results, default)
        with self.app.test_request_context('/?max_results=0'):
            self.assertEqual(parse_request(self.known_resource).max_results, default)
        with self.app.test_request_context('/?max_results=1.1'):
            self.assertEqual(parse_request(self.known_resource).max_results, 1)
        with self.app.test_request_context('/?max_results=string'):
            self.assertEqual(parse_request(self.known_resource).max_results, default)

    def test_parse_request_if_modified_since(self):
        ims = 'If-Modified-Since'
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).if_modified_since, None)
        with self.app.test_request_context(headers=None):
            self.assertEqual(parse_request(self.known_resource).if_modified_since, None)
        with self.app.test_request_context(headers={ims: self.datestr}):
            self.assertEqual(parse_request(self.known_resource).if_modified_since, self.valid +
                timedelta(seconds=1))
        with self.app.test_request_context(headers={ims: 'not-a-date'}):
            self.assertRaises(ValueError,
                          parse_request,
                          self.known_resource)
        with self.app.test_request_context(headers={ims: self.datestr.replace('UTC', 'GMT')}):
            self.assertRaises(ValueError,
                              parse_request,
                              self.known_resource)

    def test_parse_request_if_none_match(self):
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).if_none_match, None)
        with self.app.test_request_context(headers=None):
            self.assertEqual(parse_request(self.known_resource).if_none_match, None)
        with self.app.test_request_context(headers={'If-None-Match': self.etag}):
            self.assertEqual(parse_request(self.known_resource).if_none_match, self.etag)

    def test_parse_request_if_match(self):
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).if_match, None)
        with self.app.test_request_context(headers=None):
            self.assertEqual(parse_request(self.known_resource).if_match, None)
        with self.app.test_request_context(headers={'If-Match': self.etag}):
            self.assertEqual(parse_request(self.known_resource).if_match, self.etag)

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
        test = {'key1': 'value1', 'another': 'value2'}
        challenge = dumps(test, sort_keys=True)
        self.assertEqual(hashlib.sha1(challenge).hexdigest(),
                         document_etag(test))
