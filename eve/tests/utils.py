# -*- coding: utf-8 -*-

import copy
import hashlib
from bson.json_util import dumps
from datetime import datetime, timedelta
from eve.tests import TestBase
from eve.utils import parse_request, str_to_date, config, weak_date, \
    date_to_str, querydef, document_etag, extract_key_values, \
    debug_error_message, validate_filters, import_from_string


class TestUtils(TestBase):
    """ collection, document and home_link methods (and resource_uri, which is
    used by all of them) are tested in 'tests.methods' since we need an active
    flaskapp context
    """

    def setUp(self):
        super(TestUtils, self).setUp()
        self.dt_fmt = config.DATE_FORMAT
        self.datestr = 'Tue, 18 Sep 2012 10:12:30 GMT'
        self.valid = datetime.strptime(self.datestr, self.dt_fmt)
        self.etag = '56eaadbbd9fa287e7270cf13a41083c94f52ab9b'

    def test_parse_request_where(self):
        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = \
            ['ref']
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
            self.assertEqual(parse_request(self.known_resource).max_results,
                             default)
        with self.app.test_request_context('/?max_results=%d' % (limit + 1)):
            self.assertEqual(parse_request(self.known_resource).max_results,
                             limit)
        with self.app.test_request_context('/?max_results=2'):
            self.assertEqual(parse_request(self.known_resource).max_results, 2)
        with self.app.test_request_context('/?max_results=-1'):
            self.assertEqual(parse_request(self.known_resource).max_results,
                             default)
        with self.app.test_request_context('/?max_results=0'):
            self.assertEqual(parse_request(self.known_resource).max_results,
                             default)
        with self.app.test_request_context('/?max_results=1.1'):
            self.assertEqual(parse_request(self.known_resource).max_results, 1)
        with self.app.test_request_context('/?max_results=string'):
            self.assertEqual(parse_request(self.known_resource).max_results,
                             default)

    def test_parse_request_max_results_disabled_pagination(self):
        self.app.config['DOMAIN'][self.known_resource]['pagination'] = False
        default = 0
        limit = config.PAGINATION_LIMIT
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).max_results,
                             default)
        with self.app.test_request_context('/?max_results=%d' % (limit + 1)):
            self.assertEqual(parse_request(self.known_resource).max_results,
                             limit + 1)
        with self.app.test_request_context('/?max_results=2'):
            self.assertEqual(parse_request(self.known_resource).max_results, 2)
        with self.app.test_request_context('/?max_results=-1'):
            self.assertEqual(parse_request(self.known_resource).max_results,
                             default)
        with self.app.test_request_context('/?max_results=0'):
            self.assertEqual(parse_request(self.known_resource).max_results,
                             default)
        with self.app.test_request_context('/?max_results=1.1'):
            self.assertEqual(parse_request(self.known_resource).max_results, 1)
        with self.app.test_request_context('/?max_results=string'):
            self.assertEqual(parse_request(self.known_resource).max_results,
                             default)

    def test_parse_request_if_modified_since(self):
        ims = 'If-Modified-Since'
        with self.app.test_request_context():
            self.assertEqual(parse_request(
                self.known_resource).if_modified_since, None)
        with self.app.test_request_context(headers=None):
            self.assertEqual(
                parse_request(self.known_resource).if_modified_since, None)
        with self.app.test_request_context(headers={ims: self.datestr}):
            self.assertEqual(
                parse_request(self.known_resource).if_modified_since,
                self.valid + timedelta(seconds=1))
        with self.app.test_request_context(headers={ims: 'not-a-date'}):
            self.assertRaises(ValueError, parse_request, self.known_resource)
        with self.app.test_request_context(
            headers={ims:
                     self.datestr.replace('GMT', 'UTC')}):
            self.assertRaises(ValueError, parse_request, self.known_resource)
            self.assertRaises(ValueError, parse_request, self.known_resource)

    def test_parse_request_if_none_match(self):
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).if_none_match,
                             None)
        with self.app.test_request_context(headers=None):
            self.assertEqual(parse_request(self.known_resource).if_none_match,
                             None)
        with self.app.test_request_context(headers={'If-None-Match':
                                                    self.etag}):
            self.assertEqual(parse_request(self.known_resource).if_none_match,
                             self.etag)

    def test_parse_request_if_match(self):
        with self.app.test_request_context():
            self.assertEqual(parse_request(self.known_resource).if_match, None)
        with self.app.test_request_context(headers=None):
            self.assertEqual(parse_request(self.known_resource).if_match, None)
        with self.app.test_request_context(headers={'If-Match': self.etag}):
            self.assertEqual(parse_request(self.known_resource).if_match,
                             self.etag)

    def test_weak_date(self):
        with self.app.test_request_context():
            self.app.config['DATE_FORMAT'] = '%Y-%m-%d'
            self.assertEqual(weak_date(self.datestr), self.valid +
                             timedelta(seconds=1))

    def test_str_to_date(self):
        self.assertEqual(str_to_date(self.datestr), self.valid)
        self.assertRaises(ValueError, str_to_date, 'not-a-date')
        self.assertRaises(ValueError, str_to_date,
                          self.datestr.replace('GMT', 'UTC'))

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
        challenge = dumps(test, sort_keys=True).encode('utf-8')
        with self.app.test_request_context():
            self.assertEqual(hashlib.sha1(challenge).hexdigest(),
                             document_etag(test))

    def test_document_etag_ignore_fields(self):
        test = {'key1': 'value1', 'key2': 'value2'}
        ignore_fields = ["key2"]
        test_without_ignore = {'key1': 'value1'}
        challenge = dumps(test_without_ignore, sort_keys=True).encode('utf-8')
        with self.app.test_request_context():
            self.assertEqual(hashlib.sha1(challenge).hexdigest(),
                             document_etag(test, ignore_fields))

        # not required fields can not be present
        test = {'key1': 'value1', 'key2': 'value2'}
        ignore_fields = ["key3"]
        test_without_ignore = {'key1': 'value1', 'key2': 'value2'}
        challenge = dumps(test_without_ignore, sort_keys=True).encode('utf-8')
        with self.app.test_request_context():
            self.assertEqual(hashlib.sha1(challenge).hexdigest(),
                             document_etag(test, ignore_fields))

        # ignore fiels nested using doting notation
        test = {'key1': 'value1', 'dict': {'key2': 'value2', 'key3': 'value3'}}
        ignore_fields = ['dict.key2']
        test_without_ignore = {'key1': 'value1', 'dict': {'key3': 'value3'}}
        challenge = dumps(test_without_ignore, sort_keys=True).encode('utf-8')
        with self.app.test_request_context():
            self.assertEqual(hashlib.sha1(challenge).hexdigest(),
                             document_etag(test, ignore_fields))

    def test_extract_key_values(self):
        test = {
            'key1': 'value1',
            'key2': {
                'key1': 'value2',
                'nested': {
                    'key1': 'value3'
                }
            }
        }
        self.assertEqual(list(extract_key_values('key1', test)),
                         ['value1', 'value2', 'value3'])

    def test_debug_error_message(self):
        with self.app.test_request_context():
            self.app.config['DEBUG'] = False
            self.assertEqual(debug_error_message('An error message'), None)
            self.app.config['DEBUG'] = True
            self.assertEqual(debug_error_message('An error message'),
                             'An error message')

    def test_validate_filters(self):
        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = []
        with self.app.test_request_context():
            self.assertTrue('key' in validate_filters(
                {'key': 'val'},
                self.known_resource))
            self.assertTrue('key' in validate_filters(
                {'key': ['val1', 'val2']},
                self.known_resource))
            self.assertTrue('key' in validate_filters(
                {'key': {'$in': ['val1', 'val2']}},
                self.known_resource))
            self.assertTrue('key' in validate_filters(
                {'$or': [{'key': 'val1'}, {'key': 'val2'}]},
                self.known_resource))
            self.assertTrue('$or' in validate_filters(
                {'$or': 'val'},
                self.known_resource))
            self.assertTrue('$or' in validate_filters(
                {'$or': {'key': 'val1'}},
                self.known_resource))
            self.assertTrue('$or' in validate_filters(
                {'$or': ['val']},
                self.known_resource))

        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = \
            ['key']
        with self.app.test_request_context():
            self.assertTrue(validate_filters(
                {'key': 'val'},
                self.known_resource) is None)
            self.assertTrue(validate_filters(
                {'key': ['val1', 'val2']},
                self.known_resource) is None)
            self.assertTrue(validate_filters(
                {'key': {'$in': ['val1', 'val2']}},
                self.known_resource) is None)
            self.assertTrue(validate_filters(
                {'$or': [{'key': 'val1'}, {'key': 'val2'}]},
                self.known_resource) is None)

    def test_import_from_string(self):
        dt = import_from_string('datetime.datetime')
        self.assertEqual(dt, datetime)


class DummyEvent(object):
    """
    Even handler that records the call parameters and asserts a check

    Usage::

        app = Eve()
        app.on_my_event = DummyEvent(element_not_deleted)

    In the test::

        assert app.on_my_event.called[0] == expected_param_0
    """
    def __init__(self, check, deepcopy=False):
        """
        :param check: method checking the state of something during the event.
        :type: check: callable returning bool
        :param deepcopy: Do we need to store a copy of the argument calls? In
            some events arguments are changed after the event, so keeping a
            reference to the original object doesn't allow a test to check what
            was passed. The default is False.
        :type deepcopy: bool
        """
        self.__called = None
        self.__check = check
        self.__deepcopy = deepcopy

    def __call__(self, *args):
        assert self.__check()
        # In some method the arguments are changed after the events
        if self.__deepcopy:
            args = copy.deepcopy(args)
        self.__called = args

    @property
    def called(self):
        """
        The results of the call to the event.

        :rtype: It returns None if the event hasn't been called or a tuple with
            the positional arguments of the last call if called.
        """
        return self.__called
