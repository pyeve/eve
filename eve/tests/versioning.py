# -*- coding: utf-8 -*-
from bson import ObjectId

import eve
import json
from eve import Eve
from eve.tests import TestBase


class TestNormalVersioning(TestBase):

    def setUp(self):
        super(TestNormalVersioning, self).setUp()
        # self.app = Eve(settings=self.settings_file, auth=ValidBasicAuth)
        # self.test_client = self.app.test_client()
        # self.content_type = ('Content-Type', 'application/json')
        # self.valid_auth = [('Authorization', 'Basic YWRtaW46c2VjcmV0'),
        #                    self.content_type]
        # self.invalid_auth = [('Authorization', 'Basic IDontThinkSo'),
        #                      self.content_type]
        # for _, schema in self.app.config['DOMAIN'].items():
        #     schema['allowed_roles'] = ['admin']
        #     schema['allowed_item_roles'] = ['admin']
        # self.app.set_defaults()

    def test_my_first_test(self):
        self.assertTrue(True)
        