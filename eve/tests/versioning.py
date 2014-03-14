# -*- coding: utf-8 -*-
from bson import ObjectId

import eve
import json
import copy
from eve import Eve
from eve.tests import TestBase
from eve import STATUS, STATUS_OK, ETAG
from eve.tests.test_settings import MONGO_DBNAME
from bson.objectid import ObjectId


class TestVersioningBase(TestBase):
    def setUp(self):
        self.versioned_field = 'ref'
        self.unversioned_field = 'prog'

        super(TestVersioningBase, self).setUp()

        self.version_field = self.app.config['VERSION']
        self.latest_version_field = self.app.config['LATEST_VERSION']

        self._db = self.connection[MONGO_DBNAME]

    def enableVersioning(self, partial=False):
        if partial == True:
            contact_schema = self.app.config['DOMAIN']['contacts']['schema']
            contact_schema[self.unversioned_field]['versioned'] = False
        for resource, settings in self.app.config['DOMAIN'].items():
            settings['versioning'] = True
            settings['datasource'].pop('projection', None)
            self.app.register_resource(resource, settings)

    def assertEqualFields(self, obj1, obj2, fields):
        for field in fields:
            self.assertEqual(obj1[field], obj2[field])

    def assertVersion(self, response, version):
        self.assertTrue(self.version_field in response)
        self.assertEqual(response[self.version_field], version)

    def assertLatestVersion(self, response, latest_version):
        self.assertTrue(self.latest_version_field in response)
        self.assertEqual(response[self.latest_version_field], latest_version)

    def compareToGetItem(self, item, fields, compare_to):
        response, status = self.get(self.known_resource, item=item)
        self.assert200(status)
        self.assertEqualFields(response, compare_to, fields)

    def assertResponseVersion(self, response, status, version,
        latest_version = None):
        self.assert200(status)
        self.assertVersion(response, version)
        if latest_version == None:
            latest_version = version
        self.assertLatestVersion(response, latest_version)

    def directGetDocument(self, _id):
        return self._db[self.known_resource].find_one(ObjectId(_id))

    def directGetShadowDocument(self, _id, version):
        id_field = self.app.config['ID_FIELD'] + \
            self.app.config['VERSION_ID_SUFFIX']
        return self._db[self.known_resource + \
            self.app.config['VERSIONS']].find_one({
                id_field: ObjectId(_id),
                self.app.config['VERSION']: version
            })


class TestNormalVersioning(TestVersioningBase):
    def setUp(self):
        super(TestNormalVersioning, self).setUp()

        # create some dummy contacts to use for versioning tests
        self.item = {
            self.versioned_field: 'ref value 1..............',
            self.unversioned_field: 123
        }
        self.item_change = {
            self.versioned_field: 'ref value 2..............',
            self.unversioned_field: 456
        }

    def insertTestData(self):
        contact, status = self.post(self.known_resource_url, data=self.item)
        self.assert201(status)
        self.item_id = contact[self.app.config['ID_FIELD']]
        self.item_etag = contact[ETAG]
        self.item_id_url = ('/%s/%s' %
                            (self.domain[self.known_resource]['url'],
                             self.item_id))


class TestCompleteVersioning(TestNormalVersioning):
    def setUp(self):
        super(TestCompleteVersioning, self).setUp()

        # turn on version after data has been inserted into the db
        self.enableVersioning()

        # insert versioned test data
        self.insertTestData()

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
        item = {'ref': 'this is a post test!!!!!!'}
        response, status = self.post(self.known_resource_url, data=item)
        self.assert201(status)
        _id = response[self.app.config['ID_FIELD']]

        document = self.directGetDocument(_id)
        self.assertTrue(document != None)
        shadow_document = self.directGetShadowDocument(_id, 1)
        self.assertTrue(shadow_document != None)

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
        response, status = self.get(self.known_resource, item=self.item_id,
            query='?version=bad')
        # self.assert404(status)

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

    def test_version_control_the_unkown(self):
        """
        """
        # this probably doesn't work yet...


class TestPartialVersioning(TestNormalVersioning):
    def setUp(self):
        super(TestPartialVersioning, self).setUp()

        # turn on version after data has been inserted into the db
        self.enableVersioning(partial=True)

        # insert versioned test data
        self.insertTestData()

    def assertPrimaryAndShadowDocuments(self, _id, version, partial = False):
        # verify primary document fields
        document = self.directGetDocument(_id)
        self.assertTrue(document != None)
        self.assertTrue(document[self.version_field] == version)
        self.assertTrue(self.versioned_field in document)
        self.assertTrue(self.unversioned_field in document)

        # verify shadow documents fields
        shadow_document = self.directGetShadowDocument(_id, version)
        self.assertTrue(shadow_document != None)
        self.assertTrue(self.versioned_field in shadow_document)
        if partial == True:
            self.assertTrue(self.unversioned_field not in shadow_document)
        else:
            self.assertTrue(self.unversioned_field in shadow_document)

    def test_get(self):
        """ Test that get response successfully synthesize old document versions
        with new field values.
        """
        fields = [self.versioned_field, self.unversioned_field]
        query='?where={"%s":"%s"}' % (self.app.config['ID_FIELD'], self.item_id)
        response, status = self.get(self.known_resource, query=query)
        response = response['_items'][0]

        # get always returns the latest version of a document
        self.assertResponseVersion(response, status, 1)
        self.assertEqualFields(self.item, response, fields)

    def test_getitem(self):
        """ Test that get response successfully synthesize both old and new
        document versions when partial versioning is in place.
        """
        fields = [self.versioned_field, self.unversioned_field]
        # put a second version
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])

        # build expected response since the state of version 1 will change
        new_version_1 = copy.copy(self.item)
        new_version_1[self.unversioned_field] = \
            self.item_change[self.unversioned_field]

        # check the get of the first version
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=1')
        self.assertResponseVersion(response, status, 1, 2)
        self.assertEqualFields(new_version_1, response, fields)

        # check the get of the second version
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=2')
        self.assertResponseVersion(response, status, 2)
        self.assertEqualFields(self.item_change, response, fields)

        # check the get without version specified and make sure it is version 2
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assertResponseVersion(response, status, 2)
        self.assertEqualFields(self.item_change, response, fields)

    def test_post(self):
        """ Verify that partial version control can happen on POST.
        """
        response, status = self.post(self.known_resource_url,
            data=self.item_change)
        self.assert201(status)
        _id = response[self.app.config['ID_FIELD']]
        self.assertPrimaryAndShadowDocuments(_id, 1, partial=True)

    def test_multi_post(self):
        """ Eve literally throws single documents into an array before
        processing them in a POST, so I don't feel the need to specially test
        the versioning features here. Making a stub nontheless.
        """
        self.assertTrue(True)

    def test_put(self):
        """ Verify that partial version control can happen on PUT.
        """
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertTrue(STATUS in response)
        self.assertTrue(STATUS_OK in response[STATUS])
        self.assertPrimaryAndShadowDocuments(self.item_id, 2, partial=True)

    def test_patch(self):
        """ Verify that partial version control can happen on PATCH.
        """
        response, status = self.patch(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertTrue(STATUS in response)
        self.assertTrue(STATUS_OK in response[STATUS])
        self.assertPrimaryAndShadowDocuments(self.item_id, 2, partial=True)

    def test_version_control_the_unkown(self):
        """ Currently, the versioning scheme assumes true unless a field is
        explicetely marked to not be version controlled. That means, if
        'allow_unknown' is enabled, those fields are always version controlled.
        This scenario is already tested under TestCompleteVersioning. If this
        behavior changes in the future, this stub should be filled out.
        """
        self.assertTrue(True)


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
        """ Make sure that Eve doesn't mind doing a data relation explicetely to
        version 0 of a document. This should only be allowed if the shadow
        collection it empty.
        """
        pass # todo
        