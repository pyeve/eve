# -*- coding: utf-8 -*-

"""
    eve.methods
    ~~~~~~~~~~~

    This package implements the HTTP methods supported by Eve.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

# flake8: noqa
from eve.methods.get import get, getitem
from eve.methods.post import post
from eve.methods.patch import patch
from eve.methods.put import put
from eve.methods.delete import delete, deleteitem
