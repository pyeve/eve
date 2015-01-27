# -*- coding: utf-8 -*-

from bson import ObjectId
import copy
from eve.tests import TestBase
from eve.tests.utils import DummyEvent
from eve import STATUS, STATUS_OK, ETAG
from eve.tests.test_settings import MONGO_DBNAME


class TestVersioningBase(TestBase):
    def setUp(self):
        self.versioned_field = 'ref'
        self.unversioned_field = 'prog'
        self.fields = [self.versioned_field, self.unversioned_field]

        super(TestVersioningBase, self).setUp()

        self.version_field = self.app.config['VERSION']
        self.latest_version_field = self.app.config['LATEST_VERSION']
        self.document_id_field = self.app.config['ID_FIELD'] + \
            self.app.config['VERSION_ID_SUFFIX']
        self.known_resource_shadow = self.known_resource + \
            self.app.config['VERSIONS']

        self._db = self.connection[MONGO_DBNAME]

    def tearDown(self):
        super(TestVersioningBase, self).tearDown()
        self.connection.close()

    def enableVersioning(self, partial=False):
        del(self.domain['contacts']['schema']['title']['default'])
        del(self.domain['contacts']['schema']['dependency_field1']['default'])
        del(self.domain['contacts']['schema']['read_only_field']['default'])
        del(self.domain['contacts']['schema']['dict_with_read_only']
                       ['schema']['read_only_in_dict']['default'])
        if partial is True:
            contact_schema = self.domain['contacts']['schema']
            contact_schema[self.unversioned_field]['versioned'] = False
        domain = copy.copy(self.domain)
        for resource, settings in domain.items():
            settings['versioning'] = True
            settings['datasource'].pop('projection', None)
            self.app.register_resource(resource, settings)

    def enableDataVersionRelation(self, embeddable=True):
        field = {
            'type': 'dict',
            'schema': {
                self.app.config['VERSION']: {'type': 'integer'}
            },
            'data_relation': {
                'version': True,
                'resource': 'contacts'
            }
        }
        if embeddable is True:
            field['schema'][self.app.config['ID_FIELD']] = {'type': 'objectid'}
            field['data_relation']['embeddable'] = True
        else:
            field['schema']['ref'] = {'type': 'string'}
            field['data_relation']['field'] = 'ref'
        self.domain['invoices']['schema']['person'] = field

    def assertEqualFields(self, obj1, obj2, fields):
        for field in fields:
            self.assertEqual(obj1[field], obj2[field])

    def assertVersion(self, response, version):
        self.assertTrue(self.version_field in response)
        self.assertEqual(response[self.version_field], version)

    def assertLatestVersion(self, response, latest_version):
        self.assertTrue(self.latest_version_field in response)
        self.assertEqual(response[self.latest_version_field], latest_version)

    def assertDocumentVersionFields(
            self, response, version, latest_version=None):
        self.assertVersion(response, version)
        if latest_version is None:
            latest_version = version
        self.assertLatestVersion(response, latest_version)

    def directGetDocument(self, _id):
        return self._db[self.known_resource].find_one(ObjectId(_id))

    def directGetShadowDocument(self, _id, version):
        return self._db[self.known_resource_shadow].find_one(
            {self.document_id_field: ObjectId(_id),
             self.app.config['VERSION']: version}
        )

    def countDocuments(self, _id=None):
        query = {}
        if _id is not None:
            query[self.app.config['ID_FIELD']] = ObjectId(_id)

        documents = self._db[self.known_resource].find(query)
        return documents.count()

    def countShadowDocuments(self, _id=None):
        query = {}
        if _id is not None:
            query[self.document_id_field] = ObjectId(_id)

        documents = self._db[self.known_resource_shadow].find(query)
        return documents.count()

    def assertGoodPutPatch(self, response, status):
        self.assert200(status)
        self.assertTrue(STATUS in response)
        self.assertTrue(STATUS_OK in response[STATUS])


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

    def assertPrimaryAndShadowDocuments(self, _id, version, partial=False):
        # verify primary document fields
        document = self.directGetDocument(_id)
        self.assertTrue(document is not None)
        self.assertTrue(document[self.version_field] == version)
        self.assertTrue(self.versioned_field in document)
        self.assertTrue(self.unversioned_field in document)

        # verify shadow documents fields
        shadow_document = self.directGetShadowDocument(_id, version)
        self.assertTrue(shadow_document is not None)
        self.assertTrue(self.versioned_field in shadow_document)
        self.assertEqual(
            document[self.versioned_field],
            shadow_document[self.versioned_field])
        if partial is True:
            self.assertFalse(self.unversioned_field in shadow_document)
        else:
            self.assertTrue(self.unversioned_field in shadow_document)
            self.assertEqual(
                document[self.unversioned_field],
                shadow_document[self.unversioned_field])

        # verify meta fields
        self.assertTrue(shadow_document[self.version_field] == version)
        self.assertTrue(self.document_id_field in shadow_document)
        self.assertEqual(
            document[self.app.config['ID_FIELD']],
            shadow_document[self.document_id_field])
        self.assertTrue(self.app.config['ID_FIELD'] in shadow_document)
        self.assertTrue(self.app.config['LAST_UPDATED'] in shadow_document)
        self.assertTrue(self.app.config['ETAG'] in shadow_document)

        # verify that no unexpected fields exist
        num_meta_fields = 5  # see previous block
        if partial is True:
            self.assertEqual(len(shadow_document.keys()), num_meta_fields + 1)
        else:
            self.assertEqual(len(shadow_document.keys()), num_meta_fields + 2)

    def assertHateoasLinks(self, links, version_param):
        """ Makes sure links for `self`, `collection`, and `parent` point to
        the right place.
        """
        self_url = links['self']['href']
        coll_url = links['collection']['href']
        prnt_url = links['parent']['href']
        self.assertTrue('?version=%s' % (str(version_param)) in self_url)
        if version_param in ('all', 'diffs'):
            self.assertEqual(self_url.split('?')[0], coll_url)
            self.assertEqual(coll_url.rsplit('/', 1)[0], prnt_url)
        else:
            self.assertEqual('%s?version=all' % self_url.split('?')[0],
                             coll_url)
            self.assertEqual(coll_url.split('?')[0], prnt_url)

    def do_test_get(self):
        query = '?where={"%s":"%s"}' % \
            (self.app.config['ID_FIELD'], self.item_id)
        response, status = self.get(self.known_resource, query=query)
        response = response[self.app.config['ITEMS']][0]

        # get always returns the latest version of a document
        self.assert200(status)
        self.assertDocumentVersionFields(response, 1)
        self.assertEqualFields(self.item, response, self.fields)

    def do_test_getitem(self, partial):
        # put a second version
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)

        if partial is True:
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
        self.assertDocumentVersionFields(response, 1, 2)
        self.assertEqualFields(version_1, response, self.fields)
        links = response['_links']
        self.assertHateoasLinks(links, 1)

        # check the get of the second version
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=2')
        self.assert200(status)
        self.assertDocumentVersionFields(response, 2)
        self.assertEqualFields(self.item_change, response, self.fields)
        links = response['_links']
        self.assertHateoasLinks(links, 2)

        # check the get without version specified and make sure it is version 2
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assert200(status)
        self.assertDocumentVersionFields(response, 2)
        self.assertEqualFields(self.item_change, response, self.fields)

    def do_test_post(self, partial):
        response, status = self.post(
            self.known_resource_url, data=self.item_change)
        self.assert201(status)
        _id = response[self.app.config['ID_FIELD']]
        self.assertPrimaryAndShadowDocuments(_id, 1, partial=partial)

        document = self.directGetDocument(_id)
        self.assertEqualFields(self.item_change, document, self.fields)

        self.assertTrue(self.countShadowDocuments(self.item_id) == 1)

    def do_test_multi_post(self):
        self.assertTrue(True)

    def do_test_put(self, partial):
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)
        self.assertPrimaryAndShadowDocuments(self.item_id, 2, partial=partial)

        document = self.directGetDocument(self.item_id)
        self.assertEqualFields(self.item_change, document, self.fields)

        self.assertTrue(self.countShadowDocuments(self.item_id) == 2)

    def do_test_patch(self, partial):
        response, status = self.patch(
            self.item_id_url, data=self.item_change,
            headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)
        self.assertPrimaryAndShadowDocuments(self.item_id, 2, partial=partial)

        document = self.directGetDocument(self.item_id)
        self.assertEqualFields(self.item_change, document, self.fields)

        self.assertTrue(self.countShadowDocuments(self.item_id) == 2)

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
        response, status = self.get(
            self.known_resource, item=self.item_id, query='?version=2')
        self.assert404(status)

    def test_getitem_version_bad_format(self):
        """ Make sure that Eve return a nice error when requesting an unknown
        version.
        """
        response, status = self.get(
            self.known_resource, item=self.item_id, query='?version=bad')
        self.assert400(status)

    def test_getitem_version_all(self):
        """ Verify that all documents are returned which each appearing exactly
        as it would if it were accessed explicitly.
        """
        meta_fields = self.fields + [
            self.app.config['ID_FIELD'],
            self.app.config['LAST_UPDATED'], self.app.config['ETAG'],
            self.app.config['DATE_CREATED'], self.app.config['LINKS'],
            self.version_field, self.latest_version_field]

        # put a second version
        response, status = self.put(
            self.item_id_url, data=self.item_change,
            headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)
        etag2 = response[self.app.config['ETAG']]

        # get query
        response, status = self.get(
            self.known_resource, item=self.item_id, query='?version=all')
        self.assert200(status)
        items = response[self.app.config['ITEMS']]
        self.assertEqual(len(items), 2)

        # check the get of the first version
        self.assertDocumentVersionFields(items[0], 1, 2)
        self.assertEqualFields(self.item, items[0], self.fields)
        self.assertTrue(field in items[0] for field in meta_fields)
        self.assertEqual(len(items[0].keys()), len(meta_fields))
        self.assertEqual(items[0][self.app.config['ETAG']], self.item_etag)

        # # check the get of the second version
        self.assertDocumentVersionFields(items[1], 2)
        self.assertEqualFields(self.item_change, items[1], self.fields)
        self.assertTrue(field in items[1] for field in meta_fields)
        self.assertEqual(len(items[1].keys()), len(meta_fields))
        self.assertEqual(items[1][self.app.config['ETAG']], etag2)

        # check the `self` links for both versions
        self_href = items[0]['_links']['self']['href']
        self.assertEqual(int(self_href.split('?version=')[1]),
                         items[0][self.version_field])
        self_href = items[1]['_links']['self']['href']
        self.assertEqual(int(self_href.split('?version=')[1]),
                         items[1][self.version_field])

    def test_getitem_version_pagination(self):
        """ Verify that `?version=all` and `?version=diffs` display pagination
        links when results exceed `PAGINATION_DEFAULT`.
        """
        # create many versions
        response, status = self.put(
            self.item_id_url, data=self.item_change,
            headers=[('If-Match', self.item_etag)])
        for n in range(100):
            response, status = self.put(
                self.item_id_url, data=self.item_change,
                headers=[('If-Match', response[self.app.config['ETAG']])])

        # get 2nd page of results
        page = 2
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=all&page=%d' % page)
        links = response['_links']
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 2, 102, 25)
        self.assertHateoasLinks(links, 'all')

    def test_on_fetched_item(self):
        """ Verify that on_fetched_item events are fired for versioned
        requests.
        """
        devent = DummyEvent(lambda: True)
        self.app.on_fetched_item += devent
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=1')
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(
            self.item_id,
            str(devent.called[1][self.app.config['ID_FIELD']]))
        self.assertEqual(2, len(devent.called))

        # check for ?version=all requests
        devent = DummyEvent(lambda: True)
        self.app.on_fetched_item += devent
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=all')
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(
            self.item_id,
            str(devent.called[1][self.app.config['ID_FIELD']]))
        self.assertEqual(2, len(devent.called))

        # check for ?version=diffs requests
        devent = DummyEvent(lambda: True)
        self.app.on_fetched_item += devent
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=diffs')
        self.assertEqual(None, devent.called)

    def test_on_fetched_item_contacts(self):
        """ Verify that on_fetched_item_contacts events are fired for versioned
        requests.
        """
        devent = DummyEvent(lambda: True)
        self.app.on_fetched_item_contacts += devent
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=1')
        self.assertEqual(
            self.item_id,
            str(devent.called[0][self.app.config['ID_FIELD']]))
        self.assertEqual(1, len(devent.called))

        # check for ?version=all requests
        devent = DummyEvent(lambda: True)
        self.app.on_fetched_item_contacts += devent
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=all')
        self.assertEqual(
            self.item_id,
            str(devent.called[0][self.app.config['ID_FIELD']]))
        self.assertEqual(1, len(devent.called))

        # check for ?version=diffs requests
        devent = DummyEvent(lambda: True)
        self.app.on_fetched_item_contacts += devent
        response, status = self.get(self.known_resource, item=self.item_id,
                                    query='?version=diffs')
        self.assertEqual(None, devent.called)

        # TODO: also test with HATEOS off

    def test_getitem_version_diffs(self):
        """ Verify that the first document is returned in its entirety and that
        subsequent documents are simply diff to the previous version.
        """
        meta_fields = self.fields + [
            self.app.config['ID_FIELD'],
            self.app.config['LAST_UPDATED'], self.app.config['ETAG'],
            self.app.config['DATE_CREATED'], self.app.config['LINKS'],
            self.version_field, self.latest_version_field]

        # put a second version
        response, status = self.put(
            self.item_id_url, data=self.item_change,
            headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)
        etag2 = response[self.app.config['ETAG']]

        # get query
        response, status = self.get(
            self.known_resource, item=self.item_id, query='?version=diffs')
        self.assert200(status)
        items = response[self.app.config['ITEMS']]
        self.assertEqual(len(items), 2)

        # check the get of the first version
        self.assertDocumentVersionFields(items[0], 1, 2)
        self.assertEqualFields(self.item, items[0], self.fields)
        self.assertTrue(field in items[0] for field in meta_fields)
        self.assertEqual(len(items[0].keys()), len(meta_fields))
        self.assertEqual(items[0][self.app.config['ETAG']], self.item_etag)

        # # check the get of the second version
        self.assertVersion(items[1], 2)
        self.assertEqualFields(self.item_change, items[1], self.fields)
        changed_fields = self.fields + [
            self.version_field,
            self.app.config['LAST_UPDATED'],
            self.app.config['ETAG']]
        self.assertTrue(field in items[1] for field in changed_fields)
        # since the test routine happens so fast, `LAST_UPDATED` is probably
        # not in the diff (the date output only has a one second resolution)
        self.assertTrue(
            len(items[1].keys()) == len(changed_fields) or
            len(items[1].keys()) == len(changed_fields) - 1)
        self.assertEqual(items[1][self.app.config['ETAG']], etag2)

        # TODO: could also verify that a 3rd iteration is a diff of the 2nd
        # iteration and not a diff of the 1st iteration by mistake...

        # TODO: also test with HATEOS off

    def test_getitem_projection(self):
        """ Verify that projections happen smoothly when versioning is on.
        """
        # test inclusive projection
        response, status = self.get(
            self.known_resource, item=self.item_id,
            query='?projection={"%s": 1}' % self.unversioned_field)
        self.assert200(status)
        self.assertTrue(self.unversioned_field in response)
        self.assertFalse(self.versioned_field in response)
        self.assertTrue(self.version_field in response)
        self.assertTrue(self.latest_version_field in response)

        # test exclusive projection
        response, status = self.get(
            self.known_resource, item=self.item_id,
            query='?projection={"%s": 0}' % self.unversioned_field)
        self.assert200(status)
        self.assertFalse(self.unversioned_field in response)
        self.assertTrue(self.versioned_field in response)
        self.assertTrue(self.version_field in response)
        self.assertTrue(self.latest_version_field in response)

    def test_getitem_version_all_projection(self):
        """ Verify that projections happen smoothly when versioning is on.
        """
        # put a second version
        response, status = self.put(
            self.item_id_url, data=self.item_change,
            headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)

        # test inclusive projection
        projection = '{"%s": 1}' % self.unversioned_field
        response, status = self.get(
            self.known_resource, item=self.item_id,
            query='?version=all&projection=%s' % projection)
        self.assert200(status)
        items = response[self.app.config['ITEMS']]
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertTrue(self.unversioned_field in item)
            self.assertFalse(self.versioned_field in item)
            self.assertTrue(self.version_field in item)
            self.assertTrue(self.latest_version_field in item)
            if item[self.version_field] == 1:
                self.assertEqual(
                    item[self.unversioned_field],
                    self.item[self.unversioned_field])
            else:
                self.assertEqual(
                    item[self.unversioned_field],
                    self.item_change[self.unversioned_field])

        # test exclusive projection
        projection = '{"%s": 0}' % self.unversioned_field
        response, status = self.get(
            self.known_resource, item=self.item_id,
            query='?version=all&projection=%s' % projection)
        self.assert200(status)
        items = response[self.app.config['ITEMS']]
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertFalse(self.unversioned_field in item)
            self.assertTrue(self.versioned_field in item)
            self.assertTrue(self.version_field in item)
            self.assertTrue(self.latest_version_field in item)

    def test_automatic_fields(self):
        """ Make sure that Eve throws an error if we try to set a versioning
        field manually.
        """
        # set _version
        self.item_change[self.version_field] = '1'
        r, status = self.post(
            self.known_resource_url, data=self.item_change)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {self.version_field: 'unknown field'})

        # set _latest_version
        self.item_change[self.latest_version_field] = '1'
        r, status = self.post(
            self.known_resource_url, data=self.item_change)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(
            r, {self.latest_version_field: 'unknown field'})

        # set _id_document
        self.item_change[self.document_id_field] = '1'
        r, status = self.post(
            self.known_resource_url, data=self.item_change)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(
            r, {self.document_id_field: 'unknown field'})

    def test_referential_integrity(self):
        """ Make sure that Eve still correctly handles vanilla data_relations
        when versioning is turned on. (Copied from tests/methods/post.py.)
        """
        data = {"person": self.unknown_item_id}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        expected = ("value '%s' must exist in resource '%s', field '%s'" %
                    (self.unknown_item_id, 'contacts',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, {'person': expected})

        data = {"person": self.item_id}
        r, status = self.post('/invoices/', data=data)
        self.assert201(status)

    def test_delete(self):
        """ Verify that we don't throw an error if we delete a resource that is
        supposed to be versioned but whose shadow collection does not exist.
        """
        # turn off filter setting
        self.domain['contacts']['datasource']['filter'] = None

        # verify the primary collection exists but the shadow does not
        self.assertTrue(self.countDocuments() > 0)
        self.assertTrue(self.countShadowDocuments() > 0)

        # delete resource and verify no errors
        response, status = self.delete(self.known_resource_url)
        self.assert204(status)

        # verify that there are 0 documents in both collections
        self.assertTrue(self.countDocuments() == 0)
        self.assertTrue(self.countShadowDocuments() == 0)

    def test_deleteitem(self):
        """ Verify that we don't throw an error if we delete an item that is
        supposed to be versioned but that doesn't have any shadow copies.
        """
        # verify the primary document exists but no shadow documents do
        self.assertTrue(self.countDocuments(self.item_id) > 0)
        self.assertTrue(self.countShadowDocuments(self.item_id) > 0)

        # delete resource and verify no errors
        response, status = self.delete(
            self.item_id_url, headers=[('If-Match', self.item_etag)])
        self.assert204(status)

        # verify that neither primary or shadow documents exist
        self.assertTrue(self.countDocuments(self.item_id) == 0)
        self.assertTrue(self.countShadowDocuments(self.item_id) == 0)


class TestDataRelationVersionNotVersioned(TestNormalVersioning):
    def setUp(self):
        super(TestDataRelationVersionNotVersioned, self).setUp()

        # enable versioning in the invoice data_relation definition
        self.enableDataVersionRelation(embeddable=True)

        # turn on version after data has been inserted into the db
        self.enableVersioning()

        # insert versioned test data
        self.insertTestData()

    def test_referential_integrity(self):
        """ Make sure that Eve correctly validates a data_relation with a
        version and returns the version with the data_relation in the response.
        """
        data_relation = \
            self.domain['invoices']['schema']['person']['data_relation']
        value_field = data_relation['field']
        version_field = self.app.config['VERSION']
        validation_error_format = (
            "versioned data_relation must be a dict"
            " with fields '%s' and '%s'" % (value_field, version_field))

        # must be a dict
        data = {"person": self.item_id}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {'person': 'must be of dict type'})

        # must have _id
        data = {"person": {value_field: self.item_id}}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {'person': validation_error_format})

        # must have _version
        data = {"person": {version_field: 1}}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {'person': validation_error_format})

        # bad id format
        data = {"person": {value_field: 'bad', version_field: 1}}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(
            r, {'person': {
                value_field: "value 'bad' cannot be converted to a ObjectId"}})

        # unknown id
        data = {"person": {
            value_field: self.unknown_item_id, version_field: 1}}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(
            r, {'person': "value '%s' must exist in "
                "resource '%s', field '%s' at version '%s'." %
                (self.unknown_item_id, 'contacts', value_field, 1)})

        # version doesn't exist
        data = {"person": {value_field: self.item_id, version_field: 2}}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(
            r, {'person': "value '%s' must exist in "
                "resource '%s', field '%s' at version '%s'." %
                (self.item_id, 'contacts', value_field, 2)})

        # put a second version
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)

        # reference first version... this should work
        data = {"person": {value_field: self.item_id, version_field: 1}}
        r, status = self.post('/invoices/', data=data)
        self.assert201(status)

        # reference second version... this should work
        data = {"person": {value_field: self.item_id, version_field: 2}}
        r, status = self.post('/invoices/', data=data)
        self.assert201(status)

    def test_embedded(self):
        """ Perform a quick check to make sure that Eve can embedded with a
        version in the data relation.
        """
        data_relation = \
            self.domain['invoices']['schema']['person']['data_relation']
        value_field = data_relation['field']

        # add embeddable data relation
        data = {"person": {value_field: self.item_id, self.version_field: 1}}
        response, status = self.post('/invoices/', data=data)
        self.assert201(status)
        invoice_id = response[value_field]

        # test that it works
        response, status = self.get(
            self.domain['invoices']['url'],
            item=invoice_id, query='?embedded={"person": 1}')
        self.assert200(status)
        self.assertTrue('ref' in response['person'])


class TestDataRelationVersionVersioned(TestNormalVersioning):
    def setUp(self):
        super(TestDataRelationVersionVersioned, self).setUp()

        # enable versioning in the invoice data_relation definition
        self.enableDataVersionRelation(embeddable=False)

        # turn on version after data has been inserted into the db
        self.enableVersioning()

        # insert versioned test data
        self.insertTestData()

    def test_referential_integrity(self):
        """ Make sure that Eve correctly distinguishes between versions when
        referencing fields that aren't '_id'.
        """
        # put a second version
        response, status = self.put(self.item_id_url, data=self.item_change,
                                    headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)

        # try saving a field from the first version against version 2
        data = {"person": {'ref': self.item['ref'], self.version_field: 2}}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(
            r, {'person': "value '%s' must exist in "
                "resource '%s', field '%s' at version '%s'." %
                (self.item['ref'], 'contacts', 'ref', 2)})

        # try saving against the first version...this should work
        data = {"person": {'ref': self.item['ref'], self.version_field: 1}}
        r, status = self.post('/invoices/', data=data)
        self.assert201(status)


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

        # enable versioning in the invoice data_relation definition
        self.enableDataVersionRelation(embeddable=True)

        # turn on version after data has been inserted into the db
        self.enableVersioning()

    def test_get(self):
        """ Make sure that Eve returns version = 1 even for documents that
        haven't been modified since version control has been turned on.
        """
        response, status = self.get(self.known_resource)
        self.assert200(status)
        items = response[self.app.config['ITEMS']]
        self.assertEqual(len(items), self.app.config['PAGINATION_DEFAULT'])
        for item in items:
            self.assertDocumentVersionFields(item, 1)

    def test_getitem(self):
        """ Make sure that Eve returns version = 1 even for documents that
        haven't been modified since version control has been turned on.
        """
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assert200(status)
        self.assertDocumentVersionFields(response, 1)

    def test_put(self):
        """ Make sure that Eve jumps to version = 2 and saves two shadow copies
        (version 1 and version 2) for documents that where already in the
        database before version control was turned on.
        """
        # make sure there are no shadow documents
        self.assertTrue(self.countShadowDocuments() == 0)

        # put a change
        changes = {"ref": "this is a different value"}
        response, status = self.put(self.item_id_url, data=changes,
                                    headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)
        self.assertDocumentVersionFields(response, 2)

        # make sure that this saved to the db (if it didn't, version == 1)
        self.assertTrue(self.countShadowDocuments() == 2)
        response2, status = self.get(self.known_resource, item=self.item_id)
        self.assert200(status)
        self.assertDocumentVersionFields(response2, 2)
        self.assertEqual(response[ETAG], response2[ETAG])

    def test_patch(self):
        """ Make sure that Eve jumps to version = 2 and saves two shadow copies
        (version 1 and version 2) for documents that where already in the
        database before version control was turned on.
        """
        # make sure there are no shadow documents
        self.assertTrue(self.countShadowDocuments() == 0)

        # patch a change
        changes = {"ref": "this is a different value"}
        response, status = self.patch(
            self.item_id_url, data=changes,
            headers=[('If-Match', self.item_etag)])
        self.assertGoodPutPatch(response, status)
        self.assertDocumentVersionFields(response, 2)

        # make sure that this saved to the db (if it didn't, version == 1)
        self.assertTrue(self.countShadowDocuments() == 2)
        response2, status = self.get(self.known_resource, item=self.item_id)
        self.assert200(status)
        self.assertDocumentVersionFields(response2, 2)
        self.assertEqual(response[ETAG], response2[ETAG])

    def test_delete(self):
        """ Verify that we don't throw an error if we delete a resource that is
        supposed to be versioned but whose shadow collection does not exist.
        """
        # turn off filter setting
        self.domain['contacts']['datasource']['filter'] = None

        # verify the primary collection exists but the shadow does not
        self.assertTrue(self.countDocuments() > 0)
        self.assertTrue(self.countShadowDocuments() == 0)

        # delete resource and verify no errors
        response, status = self.delete(self.known_resource_url)
        self.assert204(status)

        # verify that there are 0 documents in both collections
        self.assertTrue(self.countDocuments() == 0)
        self.assertTrue(self.countShadowDocuments() == 0)

    def test_deleteitem(self):
        """ Verify that we don't throw an error if we delete an item that is
        supposed to be versioned but that doesn't have any shadow copies.
        """
        # verify the primary document exists but no shadow documents do
        self.assertTrue(self.countDocuments(self.item_id) > 0)
        self.assertTrue(self.countShadowDocuments(self.item_id) == 0)

        # delete resource and verify no errors
        response, status = self.delete(
            self.item_id_url, headers=[('If-Match', self.item_etag)])
        self.assert204(status)

        # verify that neither primary or shadow documents exist
        self.assertTrue(self.countDocuments(self.item_id) == 0)
        self.assertTrue(self.countShadowDocuments(self.item_id) == 0)

    def test_referential_integrity(self):
        """ Make sure that Eve doesn't mind doing a data relation even when the
        shadow copy doesn't exist.
        """
        data_relation = \
            self.domain['invoices']['schema']['person']['data_relation']
        value_field = data_relation['field']
        version_field = self.app.config['VERSION']

        # verify that Eve will take version = 1 if no shadow docs exist
        data = {"person": {value_field: self.item_id, version_field: 1}}
        response, status = self.post('/invoices/', data=data)
        self.assert201(status)

    def test_embedded(self):
        """ Perform a quick check to make sure that Eve can embedded with a
        version in the data relation.
        """
        data_relation = \
            self.domain['invoices']['schema']['person']['data_relation']
        value_field = data_relation['field']
        version_field = self.app.config['VERSION']

        # verify that Eve will take version = 1 if no shadow docs exist
        data = {"person": {value_field: self.item_id, version_field: 1}}
        response, status = self.post('/invoices/', data=data)
        self.assert201(status)
        invoice_id = response[value_field]

        # verify that we can embed across the data_relation w/o shadow copy
        response, status = self.get(
            self.domain['invoices']['url'],
            item=invoice_id, query='?embedded={"person": 1}')
        self.assert200(status)
        self.assertTrue('ref' in response['person'])
