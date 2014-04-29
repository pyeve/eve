import unittest

from eve.default_values import (
    build_defaults,
    resolve_default_values)


class TestBuildDefaults(unittest.TestCase):
    def test_simple(self):
        schema = {
            "name": {'type': 'string'},
            "email": {'type': 'string', 'default': "no@example.com"}
        }
        res = build_defaults(schema)
        self.assertEqual({'email': 'no@example.com'}, res)

    def test_nested_one_level(self):
        schema = {
            "address": {
                'type': 'dict',
                'schema': {
                    'street': {'type': 'string'},
                    'country': {'type': 'string', 'default': 'wonderland'}
                }
            }
        }
        res = build_defaults(schema)
        self.assertEqual({'address': {'country': 'wonderland'}}, res)

    def test_empty_defaults_multiple_level(self):
        schema = {
            'subscription': {
                'type': 'dict',
                'schema': {
                    'type': {'type': 'string'},
                    'when': {
                        'type': 'dict',
                        'schema': {
                            'timestamp': {'type': 'int'},
                            'repr': {'type': 'string'}
                        }
                    }
                }
            }
        }
        res = build_defaults(schema)
        self.assertEqual({}, res)

    def test_nested_multilevel(self):
        schema = {
            "subscription": {
                'type': 'dict',
                'schema': {
                    'type': {'type': 'string'},
                    'when': {
                        'type': 'dict',
                        'schema': {
                            'timestamp': {'type': 'int', 'default': 0},
                            'repr': {'type': 'string', 'default': '0'}
                        }
                    }
                }
            }
        }
        res = build_defaults(schema)
        self.assertEqual(
            {'subscription': {'when': {'timestamp': 0, 'repr': '0'}}},
            res)

    def test_default_in_list_schema(self):
        schema = {
            "one": {
                'type': 'list',
                'schema': {
                    'type': 'dict',
                    'schema': {
                        'title': {
                            'type': 'string',
                            'default': 'M.'
                        }
                    }
                }
            },
            "two": {
                'type': 'list',
                'schema': {
                    'type': 'dict',
                    'schema': {
                        'name': {'type': 'string'}
                    }
                }
            }
        }
        res = build_defaults(schema)
        self.assertEqual({"one": [{'title': 'M.'}]}, res)


class TestResolveDefaultValues(unittest.TestCase):
    def test_one_level(self):
        document = {'name': 'john'}
        defaults = {'email': 'noemail'}
        resolve_default_values(document, defaults)
        self.assertEqual({'name': 'john', 'email': 'noemail'}, document)

    def test_multilevel(self):
        document = {'name': 'myname', 'one': {'hey': 'jude'}}
        defaults = {'one': {'two': {'three': 'banana'}}}
        resolve_default_values(document, defaults)
        expected = {
            'name': 'myname',
            'one': {
                'hey': 'jude',
                'two': {'three': 'banana'}
            }
        }
        self.assertEqual(expected, document)

    def test_value_instead_of_dict(self):
        document = {'name': 'john'}
        defaults = {'name': {'first': 'john'}}
        resolve_default_values(document, defaults)
        self.assertEqual(document, defaults)

    def test_lists(self):
        document = {"one": [{"name": "john"}, {}]}
        defaults = {"one": [{"title": "M."}]}
        resolve_default_values(document, defaults)
        expected = {"one": [
            {"name": "john", "title": "M."},
            {"title": "M."}]}
        self.assertEqual(expected, document)
