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
        self.get_ratelimit("/")

    def test_ratelimit_resource(self):
        self.get_ratelimit(self.known_resource_url)

    def test_ratelimit_item(self):
        self.get_ratelimit(self.item_id_url)

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
