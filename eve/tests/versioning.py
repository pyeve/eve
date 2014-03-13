# -*- coding: utf-8 -*-
from bson import ObjectId

import eve
import json
from eve import Eve
from eve.tests import TestBase
from eve import ETAG


class TestVersioningBase(TestBase):
    def setUp(self):
        super(TestVersioningBase, self).setUp()

        self.version_field = self.app.config['VERSION']
        self.latest_version_field = self.app.config['LATEST_VERSION']

    def enableVersioning(self, partial=False):
        if partial == True:
            # self.app.config
            pass
        for resource, settings in self.app.config['DOMAIN'].items():
            settings['versioning'] = True
            settings['datasource'].pop('projection', None)
            self.app.register_resource(resource, settings)

    def assertVersion(self, response, version):
        self.assertTrue(self.version_field in response)
        self.assertEqual(response[self.version_field], version)

    def assertLatestVersion(self, response, latest_version):
        self.assertTrue(self.latest_version_field in response)
        self.assertEqual(response[self.latest_version_field], latest_version)

    def compareToGetItem(self, item, fields, compare_to):
        response, status = self.get(self.known_resource, item=item)
        self.assert200(status)
        for field in fields:
            self.assertEqual(response[field], compare_to[field])

    def assertResponseVersion(self, response, status, version,
        latest_version = None):
        self.assert200(status)
        self.assertVersion(response, version)
        if latest_version == None:
            latest_version = version
        self.assertLatestVersion(response, latest_version)


class TestCompleteVersioning(TestVersioningBase):
    def setUp(self):
        super(TestCompleteVersioning, self).setUp()

    def modSettingsBeforeData(self):
        # turn on version before we insert bulk data
        self.enableVersioning()

    def random_contacts(self, num):
        """ Set the version field on bulk data. Eve test data doesn't go through
        the front door (it's inserted directly into the open MongoDB connection)
        so we have to override the function that is generating the bulk data.
        """
        return super(TestCompleteVersioning, self).random_contacts(num, \
            versioning=True)

    def test_get(self):
        """
        """

    def test_getitem(self):
        """ This test class tests getitem in every other test case. This is
        meant to be an empty stub so we don't forget that.
        """
        self.assertTrue(True)

    def test_post(self):
        """
        """
        # post a new document

        # # show that we only save some fields
        # shadow = self.getShadowDocument(self.item_id, version = 1)
        # self.assertTrue(f not in shadow for f in self.unversioned_fields)
        # self.assertTrue(f in shadow for f in self.versioned_fields)

        # # show that we can still synthesize the entire document
        # self.compareToGetItem(self.item_id, compare_to = self.version_test_fields, contact)

    def test_multi_post(self):
        """
        """

    def test_put(self):
        """ Make sure that Eve still sets version = 1 for documents that where
        already in the database before version control was turned on.
        """
        changes = {"ref": "this is a different value"}
        response, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assertResponseVersion(response, status, 2)

        # make sure that this saved to the db too (if it didn't, version == 0)
        response2, status = self.get(self.known_resource, item=self.item_id)
        self.assertResponseVersion(response, status, 2)
        self.assertEqual(response[ETAG], response2[ETAG])

    def test_patch(self):
        """
        """

    def test_getitem_version_unknown(self):
        """ Make sure that Eve return a nice error when requesting an unknown
        version.
        """


    def test_getitem_version_badformat(self):
        """ Make sure that Eve return a nice error when requesting an unknown
        version.
        """
        response, status = self.get(self.known_resource, item=self.item_id, \
            query='?version=bad')
        self.assert404(status)

    def test_getitem_version_all(self):
        """
        """
        # test with HATEOS on and off

    def test_getitem_version_list(self):
        """
        """
        # test with HATEOS on and off
        # note - i might not even add this feature, is essentially ?version=all with a projection

    def test_getitem_version_diffs(self):
        """
        """
        # test with HATEOS on and off

    def test_data_relation_with_version(self):
        """ Make sure that Eve correctly validates a data_relation with a
        version and returns the version with the data_relation in the response.
        """
        # test good id and good version

        # test good id and bad version

        # test bad id

    def test_data_relation_without_version(self):
        """ Make sure that Eve still correctly handles vanilla data_relations
        when versioning is turned on.
        """


class TestPartialVersioning(TestVersioningBase):
    def setUp(self):
        super(TestPartialVersioning, self).setUp()

    def modSettingsBeforeData(self):
        # turn on version before we insert bulk data
        self.enableVersioning()

    def random_contacts(self, num):
        """ Set the version field on bulk data. Eve test data doesn't go through
        the front door (it's inserted directly into the open MongoDB connection)
        so we have to override the function that is generating the bulk data.
        """
        return super(TestPartialVersioning, self).random_contacts(num, \
            versioning=True)

    def test_get(self):
        """
        """

    def test_getitem(self):
        """ This test class tests getitem in every other test case. This is
        meant to be an empty stub so we don't forget that.
        """
        self.assertTrue(True)

    def test_post(self):
        """
        """
        # post a new document

        # # show that we only save some fields
        # shadow = self.getShadowDocument(self.item_id, version = 1)
        # self.assertTrue(f not in shadow for f in self.unversioned_fields)
        # self.assertTrue(f in shadow for f in self.versioned_fields)

        # # show that we can still synthesize the entire document
        # self.compareToGetItem(self.item_id, compare_to = self.version_test_fields, contact)

    def test_multi_post(self):
        """
        """

    def test_put(self):
        """
        """

    def test_patch(self):
        """
        """


class TestLateVersioning(TestVersioningBase):
    def setUp(self):
        super(TestLateVersioning, self).setUp()

        # turn on version after data has been inserted into the db
        self.enableVersioning()

    def test_get(self):
        """ Make sure that Eve returns version = 0 for documents that haven't
        been modified since version control has been turned on.
        """
        response, status = self.get(self.known_resource)
        self.assert200(status)
        items = response['_items']
        self.assertEqual(len(items), self.app.config['PAGINATION_DEFAULT'])
        for item in items:
            self.assertVersion(item, 0)
            self.assertLatestVersion(item, 0)

    def test_getitem(self):
        """ Make sure that Eve returns version = 0 for documents that haven't
        been modified since version control has been turned on.
        """
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assertResponseVersion(response, status, 0)

    def test_put(self):
        """ Make sure that Eve still sets version = 1 for documents that where
        already in the database before version control was turned on.
        """
        changes = {"ref": "this is a different value"}
        response, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assertResponseVersion(response, status, 1)

        # make sure that this saved to the db too (if it didn't, version == 0)
        response2, status = self.get(self.known_resource, item=self.item_id)
        self.assertResponseVersion(response2, status, 1)
        self.assertEqual(response[ETAG], response2[ETAG])

    def test_patch(self):
        """ Make sure that Eve still sets version = 1 for documents that where
        already in the database before version control was turned on.
        """
        changes = {"ref": "this is a different value"}
        response, status = self.patch(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assertResponseVersion(response, status, 1)

        # make sure that this saved to the db too (if it didn't, version == 0)
        response2, status = self.get(self.known_resource, item=self.item_id)
        self.assertResponseVersion(response2, status, 1)
        self.assertEqual(response[ETAG], response2[ETAG])

    def test_data_relation_with_version(self):
        """
        """
        #todo: any special considerations for a data relation version to a recently version collection?!
        