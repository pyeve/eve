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
        self.fields = [self.versioned_field, self.unversioned_field]

        super(TestVersioningBase, self).setUp()

        self.version_field = self.app.config['VERSION']
        self.latest_version_field = self.app.config['LATEST_VERSION']

        self._db = self.connection[MONGO_DBNAME]

    def enableVersioning(self, partial=False):
        del(self.domain['contacts']['schema']['title']['default'])
        if partial == True:
            contact_schema = self.domain['contacts']['schema']
            contact_schema[self.unversioned_field]['versioned'] = False
        for resource, settings in self.domain.items():
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

    def assertDocumentVersions(self, response, version,
        latest_version = None):
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

    def assertNumShadowDocuments(self, _id, num):
        id_field = self.app.config['ID_FIELD'] + \
            self.app.config['VERSION_ID_SUFFIX']
        documents = self._db[self.known_resource + \
            self.app.config['VERSIONS']].find({id_field: ObjectId(_id)})
        self.assertEqual(documents.count(), num)


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
        self.assertEqual(document[self.versioned_field],
            shadow_document[self.versioned_field])
        if partial == True:
            self.assertTrue(self.unversioned_field not in shadow_document)
        else:
            self.assertTrue(self.unversioned_field in shadow_document)
            self.assertEqual(document[self.unversioned_field],
                shadow_document[self.unversioned_field])

        # verify meta fields
        self.assertTrue(shadow_document[self.version_field] == version)
        document_id_field = self.app.config['ID_FIELD'] + \
            self.app.config['VERSION_ID_SUFFIX']
        self.assertTrue(document_id_field in shadow_document)
        self.assertEqual(document[self.app.config['ID_FIELD']],
            shadow_document[document_id_field])
        self.assertTrue(self.app.config['ID_FIELD'] in shadow_document)
        self.assertTrue(self.app.config['LAST_UPDATED'] in shadow_document)

        # verify that no unexpected fields exist
        num_meta_fields = 4 # see previous block
        if partial == True:
            self.assertEqual(len(shadow_document.keys()), num_meta_fields+1)
        else:
            self.assertEqual(len(shadow_document.keys()), num_meta_fields+2)

    def do_test_get(self):
        query='?where={"%s":"%s"}' % (self.app.config['ID_FIELD'], self.item_id)
        response, status = self.get(self.known_resource, query=query)
        response = response[self.app.config['ITEMS']][0]

        # get always returns the latest version of a document
        self.assert200(status)
        self.assertDocumentVersions(response, 1)
        self.assertEqualFields(self.item, response, self.fields)

    def do_test_getitem(self, partial):
        # put a second version
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])

        if partial == True:
            # build expected response since the state of version 1 will change
            version_1 = copy.copy(self.item)
            version_1[self.unversioned_field] = \
                self.item_change[self.unversioned_field]
        else:
            version_1 = self.item

        # check the get of the first version
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=1')
        self.assert200(status)
        self.assertDocumentVersions(response, 1, 2)
        self.assertEqualFields(version_1, response, self.fields)

        # check the get of the second version
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=2')
        self.assert200(status)
        self.assertDocumentVersions(response, 2)
        self.assertEqualFields(self.item_change, response, self.fields)

        # check the get without version specified and make sure it is version 2
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assert200(status)
        self.assertDocumentVersions(response, 2)
        self.assertEqualFields(self.item_change, response, self.fields)

    def do_test_post(self, partial):
        """ Verify that partial version control can happen on POST.
        """
        response, status = self.post(self.known_resource_url,
            data=self.item_change)
        self.assert201(status)
        _id = response[self.app.config['ID_FIELD']]
        self.assertPrimaryAndShadowDocuments(_id, 1, partial=partial)

        document = self.directGetDocument(_id)
        self.assertEqualFields(self.item_change, document, self.fields)

        self.assertNumShadowDocuments(self.item_id, 1)

    def do_test_multi_post(self):
        self.assertTrue(True)

    def do_test_put(self, partial):
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertTrue(STATUS in response)
        self.assertTrue(STATUS_OK in response[STATUS])
        self.assertPrimaryAndShadowDocuments(self.item_id, 2, partial=partial)

        document = self.directGetDocument(self.item_id)
        self.assertEqualFields(self.item_change, document, self.fields)

        self.assertNumShadowDocuments(self.item_id, 2)

    def do_test_patch(self, partial):
        response, status = self.patch(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertTrue(STATUS in response)
        self.assertTrue(STATUS_OK in response[STATUS])
        self.assertPrimaryAndShadowDocuments(self.item_id, 2, partial=partial)

        document = self.directGetDocument(self.item_id)
        self.assertEqualFields(self.item_change, document, self.fields)

        self.assertNumShadowDocuments(self.item_id, 2)

    def do_test_version_control_the_unkown(self):
        self.assertTrue(True)


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
        self.do_test_get()

    def test_getitem(self):
        """
        """
        self.do_test_getitem(partial=False)

    def test_post(self):
        """ Verify that a shadow document is created on post with all of the
        appropriate fields.
        """
        self.do_test_post(partial=False)

    def test_multi_post(self):
        """ Eve literally throws single documents into an array before
        processing them in a POST, so I don't feel the need to specially test
        the versioning features here. Making a stub nontheless.
        """
        self.do_test_multi_post()

    def test_put(self):
        """ Verify that an additional shadow document is created on post with
        all of the appropriate fields.
        """
        self.do_test_put(partial=False)

    def test_patch(self):
        """
        """
        self.do_test_patch(partial=False)

    def test_version_control_the_unkown(self):
        """
        """
        self.do_test_version_control_the_unkown()

    def test_getitem_version_unknown(self):
        """ Make sure that Eve return a nice error when requesting an unknown
        version.
        """
        response, status = self.get(self.known_resource, item=self.item_id,
            query='?version=2')
        self.assert404(status)

    def test_getitem_version_bad_format(self):
        """ Make sure that Eve return a nice error when requesting an unknown
        version.
        """
        response, status = self.get(self.known_resource, item=self.item_id,
            query='?version=bad')
        self.assert400(status)

    def test_getitem_version_all(self):
        """ Verify that all documents are returned which each appearing exactly
        as it would if it were accessed explicitly.
        """
        meta_fields = self.fields + [self.app.config['ID_FIELD'],
            self.app.config['LAST_UPDATED'], self.app.config['ETAG'],
            self.app.config['DATE_CREATED'], self.app.config['LINKS'],
            self.version_field, self.latest_version_field]

        # put a second version
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        etag2 = response[self.app.config['ETAG']]

        # get query
        response, status = self.get(self.known_resource, item=self.item_id,
            query='?version=all')
        self.assert200(status)
        items = response[self.app.config['ITEMS']]
        self.assertEqual(len(items), 2)

        # check the get of the first version
        self.assertDocumentVersions(items[0], 1, 2)
        self.assertEqualFields(self.item, items[0], self.fields)
        self.assertTrue(field in items[0] for field in meta_fields)
        self.assertEqual(len(items[0].keys()), len(meta_fields))
        self.assertEqual(items[0][self.app.config['ETAG']], self.item_etag)

        # # check the get of the second version
        self.assertDocumentVersions(items[1], 2)
        self.assertEqualFields(self.item_change, items[1], self.fields)
        self.assertTrue(field in items[1] for field in meta_fields)
        self.assertEqual(len(items[1].keys()), len(meta_fields))
        self.assertEqual(items[1][self.app.config['ETAG']], etag2)

        # TODO: also test with HATEOS off

    def test_getitem_version_diffs(self):
        """ Verify that the first document is returned in its entirety and that
        subsequent documents are simply diff to the previous version.
        """
        meta_fields = self.fields + [self.app.config['ID_FIELD'],
            self.app.config['LAST_UPDATED'], self.app.config['ETAG'],
            self.app.config['DATE_CREATED'], self.app.config['LINKS'],
            self.version_field, self.latest_version_field]

        # put a second version
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        etag2 = response[self.app.config['ETAG']]

        # get query
        response, status = self.get(self.known_resource, item=self.item_id,
            query='?version=diffs')
        self.assert200(status)
        items = response[self.app.config['ITEMS']]
        self.assertEqual(len(items), 2)

        # check the get of the first version
        self.assertDocumentVersions(items[0], 1, 2)
        self.assertEqualFields(self.item, items[0], self.fields)
        self.assertTrue(field in items[0] for field in meta_fields)
        self.assertEqual(len(items[0].keys()), len(meta_fields))
        self.assertEqual(items[0][self.app.config['ETAG']], self.item_etag)

        # # check the get of the second version
        self.assertVersion(items[1], 2)
        self.assertEqualFields(self.item_change, items[1], self.fields)
        changed_fields = self.fields + [self.version_field,
            self.app.config['LAST_UPDATED'], self.app.config['ETAG']]
        self.assertTrue(field in items[1] for field in changed_fields)
        # since the test routine happens so fast, `LAST_UPDATED` is probably not
        # in the diff (the date output only has a one second resolution)
        self.assertTrue(len(items[1].keys()) == len(changed_fields) or \
            len(items[1].keys()) == len(changed_fields) - 1)
        self.assertEqual(items[1][self.app.config['ETAG']], etag2)

        # TODO: could also verify that a 3rd iteration is a diff of the 2nd
        # iteration and not a diff of the 1st iteration...

        # TODO: also test with HATEOS off

    def test_data_relation_with_version(self):
        """ Make sure that Eve correctly validates a data_relation with a
        version and returns the version with the data_relation in the response.
        """
        pass # TODO
        # test good id and good version

        # test good id and bad version

        # test bad id

    def test_data_relation_without_version(self):
        """ Make sure that Eve still correctly handles vanilla data_relations
        when versioning is turned on.
        """
        pass # TODO


class TestPartialVersioning(TestNormalVersioning):
    def setUp(self):
        super(TestPartialVersioning, self).setUp()

        # turn on version after data has been inserted into the db
        self.enableVersioning(partial=True)

        # insert versioned test data
        self.insertTestData()

    def test_get(self):
        """ Test that get response successfully synthesize the full document
        even with unversioned fields.
        """
        self.do_test_get()

    def test_getitem(self):
        """ Test that get response can successfully synthesize both old and new
        document versions when partial versioning is in place.
        """
        self.do_test_getitem(partial=True)

    def test_post(self):
        """ Verify that partial version control can happen on POST.
        """
        self.do_test_post(partial=True)

    def test_multi_post(self):
        """ Eve literally throws single documents into an array before
        processing them in a POST, so I don't feel the need to specially test
        the versioning features here. Making a stub nontheless.
        """
        self.do_test_multi_post()

    def test_put(self):
        """ Verify that partial version control can happen on PUT.
        """
        self.do_test_put(partial=True)

    def test_patch(self):
        """ Verify that partial version control can happen on PATCH.
        """
        self.do_test_patch(partial=True)

    def test_version_control_the_unkown(self):
        """ Currently, the versioning scheme assumes true unless a field is
        explicitly marked to not be version controlled. That means, if
        'allow_unknown' is enabled, those fields are always version controlled.
        This is the same behavior as under TestCompleteVersioning.
        """
        self.do_test_version_control_the_unkown()


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
        items = response[self.app.config['ITEMS']]
        self.assertEqual(len(items), self.app.config['PAGINATION_DEFAULT'])
        for item in items:
            self.assertVersion(item, 0)
            self.assertLatestVersion(item, 0)

    def test_getitem(self):
        """ Make sure that Eve returns version = 0 for documents that haven't
        been modified since version control has been turned on.
        """
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assert200(status)
        self.assertDocumentVersions(response, 0)

    def test_put(self):
        """ Make sure that Eve still sets version = 1 for documents that where
        already in the database before version control was turned on.
        """
        changes = {"ref": "this is a different value"}
        response, status = self.put(self.item_id_url, data=changes,
                                    headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertDocumentVersions(response, 1)

        # make sure that this saved to the db too (if it didn't, version == 0)
        response2, status = self.get(self.known_resource, item=self.item_id)
        self.assert200(status)
        self.assertDocumentVersions(response2, 1)
        self.assertEqual(response[ETAG], response2[ETAG])

    def test_patch(self):
        """ Make sure that Eve still sets version = 1 for documents that where
        already in the database before version control was turned on.
        """
        changes = {"ref": "this is a different value"}
        response, status = self.patch(self.item_id_url, data=changes,
                                    headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertDocumentVersions(response, 1)

        # make sure that this saved to the db too (if it didn't, version == 0)
        response2, status = self.get(self.known_resource, item=self.item_id)
        self.assert200(status)
        self.assertDocumentVersions(response2, 1)
        self.assertEqual(response[ETAG], response2[ETAG])

    def test_data_relation_with_version(self):
        """ Make sure that Eve doesn't mind doing a data relation explicitly to
        version 0 of a document. This should only be allowed if the shadow
        collection it empty.
        """
        pass # TODO
        