#!/usr/bin/env python
from collections import Counter, OrderedDict  # noqa
import importlib


from setuptools import setup, find_packages
DESCRIPTION = ("Python REST API for Humans.")
with open('README.rst') as f:
    LONG_DESCRIPTION = f.read()

install_requires = [
    'cerberus>=1.1',
    'events>=0.3,<0.4',
    'simplejson>=3.3.0,<4.0',
    'werkzeug>=0.9.4,<=0.14',
    'markupsafe>=0.23,<1.0',
    'jinja2>=2.8,<3.0',
    'itsdangerous>=0.24,<1.0',
    'flask>=0.10.1,<1.0',
    'pymongo>=3.5',
]

setup(
    name='Eve',
    version='0.8-dev',
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
    install_requires=install_requires,
    tests_require=['redis', 'testfixtures'],
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
