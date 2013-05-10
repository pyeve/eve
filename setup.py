#!/usr/bin/env python

from setuptools import setup, find_packages

DESCRIPTION = ("RESTful Web API Made Simple")
LONG_DESCRIPTION = open('README.rst').read()
#VERSION = __import__('eve').__version__

setup(
    name='Eve',
    version='0.0.6-dev',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Nicola Iarocci',
    author_email='nicola@nicolaiarocci.com',
    url='http://python-eve.org',
    license=open('LICENSE').read(),
    platforms=["any"],
    packages=find_packages(),
    test_suite="eve.tests",
    install_requires=[
        'flask-pymongo>=0.2.0',
        'cerberus>=0.2.0',
        'simplejson',
        'events'
    ],
    extras_require={
        'sqlalchemy': ['sqlalchemy']
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
