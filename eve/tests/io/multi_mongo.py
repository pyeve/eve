# -*- coding: utf-8 -*-
from datetime import datetime

import json
from bson import ObjectId
from flask_pymongo import MongoClient

import eve
from eve.auth import BasicAuth
from eve.tests import TestBase
from eve.tests.test_settings import MONGO1_PASSWORD, MONGO1_USERNAME, \
    MONGO1_DBNAME, MONGO_DBNAME


class TestMultiMongo(TestBase):
    def setUp(self):
        super(TestMultiMongo, self).setUp()

        self.setupDB2()

        schema = {
            'author': {'type': 'string'},
            'title': {'type': 'string'},
        }
        settings = {
            'schema': schema,
            'mongo_prefix': 'MONGO1'
        }

        self.app.register_resource('works', settings)

    def tearDown(self):
        super(TestMultiMongo, self).tearDown()
        self.dropDB2()

    def setupDB2(self):
        self.connection = MongoClient()
        self.connection.drop_database(MONGO1_DBNAME)
        self.connection[MONGO1_DBNAME].add_user(MONGO1_USERNAME,
                                                MONGO1_PASSWORD)
        self.bulk_insert2()

    def dropDB2(self):
        self.connection = MongoClient()
        self.connection.drop_database(MONGO1_DBNAME)
        self.connection.close()

    def bulk_insert2(self):
        _db = self.connection[MONGO1_DBNAME]
        works = self.random_works(self.known_resource_count)
        _db.works.insert(works)
        self.work = _db.works.find_one()
        self.connection.close()

    def random_works(self, num):
        works = []
        for i in range(num):
            dt = datetime.now()
            work = {
                'author': self.random_string(20),
                'title': self.random_string(30),
                eve.LAST_UPDATED: dt,
                eve.DATE_CREATED: dt,
            }
            works.append(work)
        return works


class TestMethodsAcrossMultiMongo(TestMultiMongo):
    def test_get_multidb(self):
        # test that a GET on 'works' reads from MONGO1
        id_field = self.domain['works']['id_field']
        r, s = self.get('works/%s' % self.work[id_field])
        self.assert200(s)
        self.assertEqual(r['author'], self.work['author'])

        # while 'contacts' endpoint reads from MONGO
        id_field = self.domain['contacts']['id_field']
        r, s = self.get(self.known_resource, item=self.item_id)
        self.assert200(s)
        self.assertEqual(r[id_field], self.item_id)

    def test_post_multidb(self):
        # test that a POST on 'works' stores data to MONGO1
        work = self._save_work()
        db = self.connection[MONGO1_DBNAME]
        id_field = self.domain['works']['id_field']
        new = db.works.find_one({id_field: ObjectId(work[id_field])})
        self.assertTrue(new is not None)
        self.connection.close()

        # while 'contacts' endpoint stores data to MONGO
        contact = {'ref': '1234567890123456789054321'}
        r, s = self.post(self.known_resource_url, data=contact)
        self.assert201(s)
        db = self.connection[MONGO_DBNAME]
        id_field = self.domain['contacts']['id_field']
        new = db.contacts.find_one({id_field: ObjectId(r[id_field])})
        self.assertTrue(new is not None)
        self.connection.close()

    def test_patch_multidb(self):
        # test that a PATCH on 'works' udpates data on MONGO1
        work = self._save_work()
        id_field = self.domain['works']['id_field']
        id, etag = work[id_field], work[eve.ETAG]
        changes = {'author': 'mike'}

        headers = [('Content-Type', 'application/json'), ('If-Match', etag)]
        r = self.test_client.patch('works/%s' % id, data=json.dumps(changes),
                                   headers=headers)
        self.assert200(r.status_code)

        db = self.connection[MONGO1_DBNAME]
        updated = db.works.find_one({id_field: ObjectId(id)})
        self.assertEqual(updated['author'], 'mike')
        self.connection.close()

        # while 'contacts' endpoint updates data on MONGO
        field, value = "ref", "1234567890123456789012345"
        changes = {field: value}
        headers = [('Content-Type', 'application/json'), ('If-Match',
                                                          self.item_etag)]
        id_field = self.domain['contacts']['id_field']
        r = self.test_client.patch(self.item_id_url, data=json.dumps(changes),
                                   headers=headers)
        self.assert200(r.status_code)

        db = self.connection[MONGO_DBNAME]
        updated = db.contacts.find_one({id_field: ObjectId(self.item_id)})
        self.assertEqual(updated[field], value)
        self.connection.close()

    def test_put_multidb(self):
        # test that a PUT on 'works' udpates data on MONGO1
        work = self._save_work()
        id_field = self.domain['works']['id_field']
        id, etag = work[id_field], work[eve.ETAG]
        changes = {'author': 'mike', 'title': 'Eve for dummies'}

        headers = [('Content-Type', 'application/json'), ('If-Match', etag)]
        r = self.test_client.put('works/%s' % id, data=json.dumps(changes),
                                 headers=headers)
        self.assert200(r.status_code)

        db = self.connection[MONGO1_DBNAME]
        updated = db.works.find_one({id_field: ObjectId(id)})
        self.assertEqual(updated['author'], 'mike')
        self.connection.close()

        # while 'contacts' endpoint updates data on MONGO
        field, value = "ref", "1234567890123456789012345"
        changes = {field: value}
        headers = [('Content-Type', 'application/json'), ('If-Match',
                                                          self.item_etag)]
        id_field = self.domain['contacts']['id_field']
        r = self.test_client.put(self.item_id_url, data=json.dumps(changes),
                                 headers=headers)
        self.assert200(r.status_code)

        db = self.connection[MONGO_DBNAME]
        updated = db.contacts.find_one({id_field: ObjectId(self.item_id)})
        self.assertEqual(updated[field], value)
        self.connection.close()

    def test_delete_multidb(self):
        # test that DELETE on 'works' deletes data on MONGO1
        work = self._save_work()
        id_field = self.domain['works']['id_field']
        id, etag = work[id_field], work[eve.ETAG]
        r = self.test_client.delete('works/%s' % id, headers=[('If-Match',
                                                               etag)])
        self.assert204(r.status_code)
        db = self.connection[MONGO1_DBNAME]
        lost = db.works.find_one({id_field: ObjectId(id)})
        self.assertEqual(lost, None)
        self.connection.close()

        # while 'contacts' still deletes on MONGO
        r = self.test_client.delete(self.item_id_url,
                                    headers=[('If-Match', self.item_etag)])
        self.assert204(r.status_code)
        db = self.connection[MONGO_DBNAME]
        id_field = self.domain['contacts']['id_field']
        lost = db.contacts.find_one({id_field: ObjectId(self.item_id)})
        self.assertEqual(lost, None)
        self.connection.close()

    def _save_work(self):
        work = {'author': 'john doe', 'title': 'Eve for Dummies'}
        r, s = self.post('works', data=work)
        self.assert201(s)
        return r


class MyBasicAuth(BasicAuth):
    def check_auth(self, username, password, allowed_roles, resource, method):
        self.set_mongo_prefix('MONGO1')
        return True


class TestMultiMongoAuth(TestMultiMongo):
    def test_get_multidb(self):
        self.domain['works']['mongo_prefix'] = 'MONGO'
        self.domain['works']['public_item_methods'] = []

        headers = [('Authorization', 'Basic YWRtaW46c2VjcmV0')]

        # this will 404 since there's no 'works' collection on MONGO,
        id_field = self.domain['works']['id_field']
        r = self.test_client.get('works/%s' % self.work[id_field],
                                 headers=headers)
        self.assert404(r.status_code)

        # now set a custom auth class which sets mongo_prefix at MONGO1
        self.domain['works']['authentication'] = MyBasicAuth

        # this will 200 just fine as the custom auth class has precedence over
        # endpoint configuration.
        r = self.test_client.get('works/%s' % self.work[id_field],
                                 headers=headers)
        self.assert200(r.status_code)
        # test that we are indeed reading from the correct database instance.
        payl = json.loads(r.get_data().decode('utf-8'))
        self.assertEqual(payl['author'], self.work['author'])

        # 'contacts' still reads from MONGO
        r = self.test_client.get('%s/%s' % (self.known_resource_url,
                                            self.item_id), headers=headers)
        self.assert200(r.status_code)
