# -*- coding: utf-8 -*-

"""
    Default values in schemas
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Default values for schemas work in two steps.
    1. The schema is searched for defaults and a list of default is built.
    2. In each POST/PUT request, for each default (if any) the document is
    checked for a missing value, and if a value is missing the default is
    added.

    :copyright: (c) 2015 by Nicola Iarocci.
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
        if isinstance(current, list):
            level_schema = {'schema': level_schema.copy()}
        for name, value in level_schema.items():
            default_next_level = None
            if 'default' in value:
                try:
                    current[name] = value['default']
                except TypeError:
                    current.append(value['default'])
            elif value.get('type') == 'dict' and 'schema' in value:
                default_next_level = {}
            elif value.get('type') == 'list' and 'schema' in value:
                default_next_level = []

            if default_next_level is not None:
                leave = False
                next_level = add_next_level(name, current, default_next_level)
                stack.append((value['schema'], name, current, next_level))
                pending.add(id(next_level))
        pending.discard(id(current))
        if leave:
            # Leaves trigger the `walk up` till the next not processed node
            while id(current) not in pending:
                if not current and level_parent is not None:
                    try:
                        del level_parent[level_name]
                    except TypeError:
                        level_parent.remove(current)
                stack.pop()
                if len(stack) == 0:
                    break
                level_schema, level_name, level_parent, current = stack[-1]
        else:
            level_schema, level_name, level_parent, current = stack[-1]

    return current


def add_next_level(name, current, default):
    if isinstance(current, list):
        current.append(default)
    else:
        default = current.setdefault(name, default)
    return default


def resolve_default_values(document, defaults):
    """ Add any defined default value for missing document fields.

    :param document: the document being posted or replaced
    :param defaults: tree with the default values
    :type defaults: dict

    .. versionchanged:: 0.5
       Fix #417. A default value of [] for a list causes an IndexError.

    .. versionadded:: 0.2
    """
    todo = [(defaults, document)]
    while len(todo) > 0:
        defaults, document = todo.pop()
        if isinstance(defaults, list) and len(defaults):
            todo.extend((defaults[0], item) for item in document)
            continue
        for name, value in defaults.items():
            if isinstance(value, dict):
                # default dicts overwrite simple values
                existing = document.setdefault(name, {})
                if not isinstance(existing, dict):
                    document[name] = {}
                todo.append((value, document[name]))
            if isinstance(value, list) and len(value):
                existing = document.get(name)
                if not existing:
                    document.setdefault(name, value)
                    continue
                if all(isinstance(item, (dict, list)) for item in existing):
                    todo.extend((value[0], item) for item in existing)
                else:
                    document.setdefault(name, existing)
            else:
                document.setdefault(name, value)
