from eve.tests import TestBase
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from eve.tests.test_settings import MONGO1_DBNAME, MONGO1_USERNAME, \
    MONGO1_PASSWORD, MONGO_HOST, MONGO_PORT
from eve.io.mongo.flask_pymongo import PyMongo


class TestPyMongo(TestBase):
    def setUp(self, url_converters=None):
        super(TestPyMongo, self).setUp(url_converters)
        self._setupdb()
        schema = {
            'title': {'type': 'string'},
        }
        settings = {
            'schema': schema,
            'mongo_prefix': 'MONGO1',
        }

        self.app.register_resource('works', settings)

    def test_auth_params_provided_in_mongo_url(self):
        self.app.config['MONGO1_URL'] = \
            'mongodb://%s:%s@%s:%s' % (MONGO1_USERNAME, MONGO1_PASSWORD,
                                       MONGO_HOST, MONGO_PORT)
        with self.app.app_context():
            db = PyMongo(self.app, 'MONGO1').db
        self.assertEqual(0, db.works.count())

    def test_auth_params_provided_in_config(self):
        self.app.config['MONGO1_USERNAME'] = MONGO1_USERNAME
        self.app.config['MONGO1_PASSWORD'] = MONGO1_PASSWORD
        with self.app.app_context():
            db = PyMongo(self.app, 'MONGO1').db
        self.assertEqual(0, db.works.count())

    def test_invalid_auth_params_provided(self):
        # if bad username and/or password is provided in MONGO_URL and mongo
        # run w\o --auth pymongo won't raise exception
        self.app.config['MONGO1_USERNAME'] = 'bad_username'
        self.app.config['MONGO1_PASSWORD'] = 'bad_password'
        self.assertRaises(OperationFailure, self._pymongo_instance)

    def test_invalid_port(self):
        self.app.config['MONGO1_PORT'] = 'bad_value'
        self.assertRaises(TypeError, self._pymongo_instance)

    def test_invalid_options(self):
        self.app.config['MONGO1_OPTIONS'] = {
            'connectTimeoutMS': 'bad_value'
        }
        self.assertRaises(ValueError, self._pymongo_instance)

    def test_valid_port(self):
        self.app.config['MONGO1_PORT'] = 27017
        with self.app.app_context():
            db = PyMongo(self.app, 'MONGO1').db
        self.assertEqual(0, db.works.count())

    def _setupdb(self):
        self.connection = MongoClient()
        self.connection.drop_database(MONGO1_DBNAME)
        db = self.connection[MONGO1_DBNAME]
        try:
            db.command('dropUser', MONGO1_USERNAME)
        except OperationFailure:
            pass
        db.command('createUser', MONGO1_USERNAME, pwd=MONGO1_PASSWORD,
                   roles=['dbAdmin'])

    def _pymongo_instance(self):
        with self.app.app_context():
            PyMongo(self.app, 'MONGO1')
