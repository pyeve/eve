#!/usr/bin/env python

from setuptools import setup, find_packages

DESCRIPTION = ('An out-of-the-box RESTful Web API. Effortlessly build and '
               'deploy your fully featured, proprietary API.')
LONG_DESCRIPTION = open('README.rst').read()
VERSION = __import__('eve').__version__

setup(
    name='Eve',
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Nicola Iarocci',
    author_email='nicola@nicolaiarocci.com',
    url='http://github.com/nicolaiarocci/eve',
    license=open('LICENSE').read(),
    platforms=["any"],
    packages=find_packages(),
    test_suite="eve.tests",
    #\requires=['simplejson'],
    install_requires=['flask-pymongo', 'json-datetime', 'cerberus'],
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
