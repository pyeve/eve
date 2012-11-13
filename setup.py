#!/usr/bin/env python

from setuptools import setup, find_packages

DESCRIPTION = ("An out-of-the-box REST Web API that's as dangerous as you "
               "want it to be.")
LONG_DESCRIPTION = open('README.md').read()

setup(
    name='Eve',
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
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
