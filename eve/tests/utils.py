from datetime import datetime
from eva.tests import TestBase
from eva.utils import parse_request, str_to_date, config


class TestUtils(TestBase):

    def setUp(self):
        super(TestUtils, self).setUp()
        self.dt_fmt = config.DATE_FORMAT
        self.datestr = 'Tue, 18 Sep 2012 10:12:30 UTC'
        self.valid = datetime.strptime(self.datestr, self.dt_fmt)

    def test_parse_request(self):
        # where
        self.assertEqual(parse_request().where, None)
        self.assertEqual(parse_request({'where': 'hello'}).where, 'hello')

        # sort
        self.assertEqual(parse_request().sort, None)
        self.assertEqual(parse_request({'sort': 'hello'}).sort, 'hello')

        # page
        self.assertEqual(parse_request().page, 1)
        self.assertEqual(parse_request({'page': 2}).page, 2)
        self.assertEqual(parse_request({'page': -1}).page, 1)
        self.assertEqual(parse_request({'page': 0}).page, 1)
        self.assertEqual(parse_request({'page': 1.1}).page, 1)
        self.assertEqual(parse_request({'page': 'string'}).page, 1)

        # max_restults
        default = config.PAGING_DEFAULT
        limit = config.PAGING_LIMIT
        self.assertEqual(parse_request().max_results, default)
        self.assertEqual(
            parse_request({'max_results': limit + 1}).max_results, limit)
        self.assertEqual(
            parse_request({'max_results': 2}).max_results, 2)
        self.assertEqual(
            parse_request({'max_restults': -1}).max_results, default)
        self.assertEqual(
            parse_request({'max_restults': 0}).max_results, default)
        self.assertEqual(
            parse_request({'max_restults': 1.1}).max_results, default)
        self.assertEqual(
            parse_request({'max_restults': 'string'}).max_results, default)

        # if-modified-since
        ims = 'If-Modified-Since'
        self.assertEqual(parse_request().if_modified_since, None)
        self.assertEqual(parse_request(headers=None).if_modified_since, None)
        self.assertEqual(parse_request(
            headers={ims: self.datestr}).if_modified_since, self.valid)
        self.assertRaises(ValueError,
                          parse_request,
                          headers={ims: 'not-a-date'})
        self.assertRaises(ValueError,
                          parse_request,
                          headers={ims: self.datestr.replace('UTC', 'GMT')})

    def test_str_to_date(self):
        self.assertEqual(str_to_date(self.datestr), self.valid)
        self.assertRaises(ValueError, str_to_date, 'not-a-date')
        self.assertRaises(ValueError, str_to_date,
                          self.datestr.replace('UTC', 'GMT'))
