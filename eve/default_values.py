# -*- coding: utf-8 -*-

"""
    Default values in schemas
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Default values for schemas work in two steps.
    1. The schema is searched for defaults and a list of default is built.
    2. In each POST/PUT request, for each default (if any) the document is
    checked for a missing value, and if a value is missing the default is
    added.

    :copyright: (c) 2014 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""


def build_defaults(schema):
    """Build a tree of default values

    It walks the tree down looking for entries with a `default` key. In order
    to avoid empty dicts the tree will be walked up and the empty dicts will be
    removed.

    :param schema: Resource schema
    :type schema: dict
    :rtype: dict with defaults

    .. versionadded:: 0.4
    """
    # Pending schema nodes to process: loop and add defaults
    pending = set()
    # Stack of nodes to work on and clean up
    stack = [(schema, None, None, {})]
    level_schema, level_name, level_parent, current = stack[-1]
    while len(stack) > 0:
        leave = True
        for name, value in level_schema.items():
            if 'default' in value:
                current[name] = value['default']
            elif value.get('type') == 'dict':
                leave = False
                stack.append((
                    value['schema'], name, current,
                    current.setdefault(name, {})))
                pending.add(id(current[name]))
            elif value.get('type') == 'list' and 'schema' in value and \
                    'schema' in value['schema']:
                leave = False
                def_dict = {}
                current[name] = [def_dict]
                stack.append((
                    value['schema']['schema'], name, current, def_dict))
                pending.add(id(def_dict))
        pending.discard(id(current))
        if leave:
            # Leaves trigger the `walk up` till the next not processed node
            while id(current) not in pending:
                if not current and level_parent is not None:
                    del level_parent[level_name]
                stack.pop()
                if len(stack) == 0:
                    break
                level_schema, level_name, level_parent, current = stack[-1]
        else:
            level_schema, level_name, level_parent, current = stack[-1]

    return current


def resolve_default_values(document, defaults):
    """ Add any defined default value for missing document fields.

    :param document: the document being posted or replaced
    :param defaults: tree with the default values
    :type defaults: dict

    .. versionadded:: 0.2
    """
    todo = [(defaults, document)]
    while len(todo) > 0:
        defaults, document = todo.pop()
        for name, value in defaults.items():
            if isinstance(value, dict):
                # default dicts overwrite simple values
                existing = document.setdefault(name, {})
                if not isinstance(existing, dict):
                    document[name] = {}
                todo.append((value, document[name]))
            if isinstance(value, list):
                existing = document.get(name)
                if not existing:
                    continue
                todo.extend((value[0], item) for item in existing)
            else:
                document.setdefault(name, value)
