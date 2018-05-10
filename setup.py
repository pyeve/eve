#!/usr/bin/env python
from collections import Counter, OrderedDict  # noqa
import importlib


from setuptools import setup, find_packages
DESCRIPTION = ("Python REST API for Humans.")
with open('README.rst') as f:
    LONG_DESCRIPTION = f.read()

INSTALL_REQUIRES = [
    'cerberus>=1.1',
    'events>=0.3,<0.4',
    'flask>=1.0',
    'pymongo>=3.5',
    'simplejson>=3.3.0,<4.0',
]

EXTRAS_REQUIRE = {
    "docs": [
        "sphinx",
        "alabaster",
        "sphinxcontrib-embedly"
    ],
    "tests": [
        "redis",
        "testfixtures",
        "pytest",
        "tox",
    ],
}
EXTRAS_REQUIRE["dev"] = EXTRAS_REQUIRE["tests"] + EXTRAS_REQUIRE["docs"]

setup(
    name='Eve',
    version='0.8',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Nicola Iarocci',
    author_email='eve@nicolaiarocci.com',
    url='http://python-eve.org',
    project_urls={
        'Documentation': 'http://python-eve.org',
        'Code': 'https://github.com/pyeve/eve',
        'Issue tracker': 'https://github.com/pyeve/eve/issues',
    },
    license='BSD',
    platforms=["any"],
    packages=find_packages(),
    test_suite="eve.tests",
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
