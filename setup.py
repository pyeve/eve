#!/usr/bin/env python

from setuptools import setup, find_packages

DESCRIPTION = ("A RESTful Web API powered by Python and MongoDB")
LONG_DESCRIPTION = open('README.md').read()

setup(
    name='eve',
    version='0.0.1',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Nicola Iarocci',
    author_email='nicola@nicolaiarocci.com',
    url='http://github.com/nicolaiarocci/json-datetime',
    license=open('LICENSE').read(),
    platforms=["any"],
    packages=find_packages(),
    test_suite="eve.tests",
    #\requires=['simplejson'],
    install_requires=['flask-pymongo', 'json-datetime'],
    classifiers=[
        'Development Status :: 5 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
