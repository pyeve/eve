from eve.tests import TestBase
from redis import Redis
import time


class TestRateLimit(TestBase):
    def setUp(self):
        super(TestRateLimit, self).setUp()
        self.app.redis = Redis()
        self.app.config['RATE_LIMIT_GET'] = (1, 1)
        self.app.redis.flushdb()

    def test_ratelimit_home(self):
        """ PLEASE NOTE: this requires a running redis-server
        """
        self.get_ratelimit("/")

    def test_ratelimit_resource(self):
        """ PLEASE NOTE: this requires a running redis-server
        """
        self.get_ratelimit(self.known_resource_url)

    def test_ratelimit_item(self):
        """ PLEASE NOTE: this requires a running redis-server
        """
        self.get_ratelimit(self.item_id_url)

    def test_noratelimits(self):
        """ PLEASE NOTE: this requires a running redis-server
        """
        self.app.config['RATE_LIMIT_GET'] = None
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
