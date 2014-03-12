# -*- coding: utf-8 -*-
from bson import ObjectId

import eve
import json
from eve import Eve
from eve.tests import TestBase


class TestVersioning(TestBase):

    def setUp(self):
        super(TestVersioning, self).setUp()
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

    def assertShadowDocument(self):
        self.assertTrue(True)

    def test_insert_shadow_document_simple(self):
        """Make sure that Eve actually saves a copy of the document in the
        parallel versions collection when the entire document is version
        controlled.
        """
        # test single post
        #todo: be sure to test _version==2 here

        # test put

        # test patch

        # Todo: do I also need to test POST/array?
        self.assertTrue(True)

    def test_insert_shadow_document_complex(self):
        """Make sure that Eve actually saves a copy of the document in the
        parallel versions collection when the entire document is version
        controlled.
        """
        # test single post
        #todo: be sure to test _version==2 here

        # test put

        # test patch

        # Todo: do I also need to test POST/array?
        self.assertTrue(True)

    def test_get_unknown_version(self):
        """ Make sure that Eve return a nice error when requesting an unknown
        version.
        """
        self.assertTrue(True)

    def test_get_late_config_change(self):
        """ Make sure that Eve returns version = 0 for documents that haven't
        been modified since version control has been turned on.
        """
        # test get and getitem
        self.assertTrue(True)

    def test_get_latest_version_simple(self):
        """ Make sure that Eve is correctly synthesizing the latest version of a
        document when the entire document is version controlled.
        """
        # test get and getitem
        # put a change

        # get the latest version and make sure it matches
        self.assertTrue(True)

    def test_get_latest_version_complex(self):
        """ Make sure that Eve is correctly synthesizing the latest version of a
        document when only some fields of a document are version controlled.
        """
        # test get and getitem
        # put a change

        # get the latest version and make sure it matches
        self.assertTrue(True)

    def test_get_old_verion_simple(self):
        """ Make sure that Eve is correctly synthesizing the old version of a
        document when the entire document is version controlled.
        """
        # test get and getitem
        # put a change

        # get the previous version and make sure it matches
        self.assertTrue(True)

    def test_get_old_verion_complex(self):
        """ Make sure that Eve is correctly synthesizing the old version of a
        document when only some fields of a document are version controlled.
        """
        # test get and getitem
        # put a change

        # get the previous version and make sure it matches
        self.assertTrue(True)

    def test_getitem_all(self):
        # test with HATEOS on and off
        self.assertTrue(True)

    def test_getitem_list(self):
        # test with HATEOS on and off
        # note - i might not even add this feature, is essentially ?version=all with a projection
        self.assertTrue(True)

    def test_getitem_diffs(self):
        # test with HATEOS on and off
        self.assertTrue(True)

    def test_data_relation_with_version(self):
        """ Make sure that Eve correctly validates a data_relation with a
        version and returns the version with the data_relation in the response.
        """
        self.assertTrue(True)

    def test_data_relation_without_version(self):
        """ Make sure that Eve still correctly handles vanilla data_relations
        when versioning is turned on.
        """
        self.assertTrue(True)
        