#!/usr/bin/env python

from setuptools import setup, find_packages
DESCRIPTION = ("REST API framework to effortlessly build and deploy highly "
               "customizable, fully featured RESTful Web Services. Powered "
               "by Flask, MongoDB and good intentions.")
LONG_DESCRIPTION = open('README.rst').read()
#VERSION = __import__('eve').__version__

setup(
    name='Eve',
    version='0.0.9',
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
        'cerberus==0.3.0',
        'events==0.1.0',
        'simplejson==3.3.0',
        'werkzeug==0.9.4',
        'markupsafe==0.18',
        'jinja2==2.7',
        'itsdangerous==0.22',
        'flask==0.10.1',
        'pymongo==2.6',
        'flask-pymongo==0.3.0',
    ],
    tests_require=['redis'],
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
