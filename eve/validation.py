# -*- coding: utf-8 -*-

"""
    eve.validation
    ~~~~~~~~~~~~~~

    Helper module. Allows eve submodules (methods.patch/post) to be fully
    datalayer-agnostic. Specialized Validator classes are implemented in the
    datalayer submodules.

    :copyright: (c) 2015 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

# flake8: noqa
from cerberus import ValidationError, SchemaError
