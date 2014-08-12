#!/usr/bin/env python

from setuptools import setup, find_packages
DESCRIPTION = ("REST API framework powered by Flask, MongoDB and good "
               "intentions.")
LONG_DESCRIPTION = open('README.rst').read()

setup(
    name='Eve',
    version='0.4',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Nicola Iarocci',
    author_email='eve@nicolaiarocci.com',
    url='http://python-eve.org',
    license=open('LICENSE').read(),
    platforms=["any"],
    packages=find_packages(),
    test_suite="eve.tests",
    install_requires=[
        'cerberus==0.7.2',
        'events==0.2.1',
        'simplejson==3.5.2',
        'werkzeug==0.9.6',
        'markupsafe==0.23',
        'jinja2==2.7.3',
        'itsdangerous==0.24',
        'flask==0.10.1',
        'pymongo==2.7.1',
        'flask-pymongo==0.3.0',
    ],
    tests_require=['redis'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
