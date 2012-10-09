from eva.flaskapp import RegexConverter
from eva.tests import TestBase
from eva.exceptions import ConfigException


class TestConfig(TestBase):

    def test_regexconverter(self):
        regex_converter = self.app.url_map.converters.get('regex')
        self.assertIs(regex_converter, RegexConverter)

    def test_validate_config(self):
        del self.app.config['DOMAIN']
        try:
            self.app.validate_config()
        except ConfigException, e:
            self.assertTrue("missing" in str(e))
        else:
            self.fail("ConfigException expected but not raised.")

        self.app.config['DOMAIN'] = []
        try:
            self.app.validate_config()
        except ConfigException, e:
            self.assertTrue('must be a dict' in str(e))
        else:
            self.fail("ConfigException expected but not raised.")

        self.app.config['DOMAIN'] = {}
        try:
            self.app.validate_config()
        except ConfigException, e:
            self.assertTrue('must contain at least one' in str(e))
        else:
            self.fail("ConfigException expected but not raised.")

    def test_set_defaults(self):
        self.domain.clear()
        self.domain['resource_test'] = {}
        self.domain['resource_test']['url'] = 'an_alternative_url'
        self.app.set_defaults()

        for resource, settings in self.domain.items():
            self.assertEqual(settings['url'], 'an_alternative_url')
            self.assertEqual(settings['methods'],
                             self.app.config['RESOURCE_METHODS'])
            self.assertEqual(settings['cache_control'],
                             self.app.config['CACHE_CONTROL'])
            self.assertEqual(settings['item_methods'],
                             self.app.config['ITEM_METHODS'])
            self.assertEqual(settings['item_lookup'],
                             self.app.config['ITEM_LOOKUP'])
            self.assertEqual(settings['item_lookup_field'],
                             self.app.config['ITEM_LOOKUP_FIELD'])
            self.assertEqual(settings['item_url'],
                             self.app.config['ITEM_URL'])
            self.assertEqual(settings['item_cache_control'],
                             self.app.config['ITEM_CACHE_CONTROL'])

    def test_url_helpers(self):
        self.assertIs(type(self.app.config['RESOURCES']), dict)
        self.assertIs(type(self.app.config['URLS']), dict)

        for resource, settings in self.domain.items():
            self.assertEqual(settings['url'],
                             self.app.config['URLS'][resource])
            self.assertEqual(resource,
                             self.app.config['RESOURCES'][settings['url']])

    def test_url_rules(self):
        map_adapter = self.app.url_map.bind(self.app.config['BASE_URI'])

        for resource, settings in self.domain.items():
            for method in settings['methods']:
                self.assertTrue(map_adapter.test('/%s/' % settings['url'],
                                                 method))

            # TODO test item endpoints as well. gonna be tricky since
            # we have regexes here
