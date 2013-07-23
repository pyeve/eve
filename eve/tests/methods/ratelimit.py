from eve.tests import TestBase
import time
import unittest

# necessary evil
my_redis = None
try:
    from redis import Redis, ConnectionError
    my_redis = Redis()
    try:
        my_redis.flushdb()
    except ConnectionError:
        my_redis = None
except ImportError:
    pass

print my_redis


class TestRateLimit(TestBase):
    def setUp(self):
        super(TestRateLimit, self).setUp()
        if my_redis:
            self.app.redis = my_redis
            self.app.config['RATE_LIMIT_GET'] = (1, 1)

    @unittest.skipIf(my_redis is None, 'requires "pip install redis" and a '
                     'running redis-server')
    def test_ratelimit_home(self):
        self.get_ratelimit("/")

    @unittest.skipIf(my_redis is None, 'requires "pip install redis" and a '
                     'running redis-server')
    def test_ratelimit_resource(self):
        self.get_ratelimit(self.known_resource_url)

    @unittest.skipIf(my_redis is None, 'requires "pip install redis" and a '
                     'running redis-server')
    def test_ratelimit_item(self):
        self.get_ratelimit(self.item_id_url)

    @unittest.skipIf(my_redis is None, 'requires "pip install redis" and a '
                     'running redis-server')
    def test_noratelimits(self):
        self.app.config['RATE_LIMIT_GET'] = None
        if self.app.redis:
            self.app.redis.flushdb()
        r = self.test_client.get("/")
        self.assert200(r.status_code)
        self.assertTrue('X-RateLimit-Remaining' not in r.headers)
        self.assertTrue('X-RateLimit-Limit' not in r.headers)
        self.assertTrue('X-RateLimit-Reset' not in r.headers)

    def get_ratelimit(self, url):
        self.assertRateLimit(self.test_client.get(url))
        r = self.test_client.get(url)
        self.assertEqual(r.status_code, 429)
        self.assertTrue('Rate limit exceeded' in r.data)

        time.sleep(1)
        self.assertRateLimit(self.test_client.get(url))

    def assertRateLimit(self, r):
        self.assertTrue('X-RateLimit-Remaining' in r.headers)
        self.assertEqual(r.headers['X-RateLimit-Remaining'], '0')
        self.assertTrue('X-RateLimit-Limit' in r.headers)
        self.assertEqual(r.headers['X-RateLimit-Limit'], '1')
        # renouncing on testing the actual Reset value:
        self.assertTrue('X-RateLimit-Reset' in r.headers)
