# -*- coding: utf-8 -*-

"""
    Default values in schemas
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Default values for schemas work in two steps.
    1. The schema is searched for defaults and a list of default is built.
    2. In each POST/PUT request, for each default (if any) the document is
    checked for a missing value, and if a value is missing the default is
    added.

    :copyright: (c) 2016 by Nicola Iarocci.
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
    circular_dependency_checker = CircularDependencyChecker()
    while len(todo) > 0:
        circular_dependency_checker.register_todo_list(todo)
        defaults, document_part = todo.pop(0)
        if isinstance(defaults, list) and len(defaults):
            todo.extend((defaults[0], item) for item in document_part)
            continue
        for name, value in defaults.items():
            if callable(value):
                try:
                    value = value(document)
                except KeyError:
                    todo.append(({name: value}, document_part))
                    continue
            if isinstance(value, dict):
                # default dicts overwrite simple values
                existing = document_part.setdefault(name, {})
                if not isinstance(existing, dict):
                    document_part[name] = {}
                todo.append((value, document_part[name]))
            elif isinstance(value, list) and len(value):
                existing = document_part.get(name)
                if not existing:
                    document_part.setdefault(name, value)
                    continue
                if all(isinstance(item, (dict, list)) for item in existing):
                    todo.extend((value[0], item) for item in existing)
                else:
                    document_part.setdefault(name, existing)
            else:
                document_part.setdefault(name, value)


class CircularDependencyChecker(object):
    """Raises an error if the same todo list appears twice."""

    def __init__(self):
        self.known_states = set()

    def register_todo_list(self, todo):
        # Pickling or similar serializing techniques won't work as there are
        # lambda functions in `todo`. As we don't need persistance we can just
        # use a `repr` to detect equal todo lists.
        state = repr(todo)
        if state in self.known_states:
            raise RuntimeError('circular dependency for default values')
        else:
            self.known_states.add(state)
