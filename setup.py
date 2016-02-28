#!/usr/bin/env python

from setuptools import setup, find_packages
DESCRIPTION = ("Python REST API for Humans.")
with open('README.rst') as f:
    LONG_DESCRIPTION = f.read()

install_requires = [
    'cerberus>=0.9.2,<0.10',
    'events>=0.2.1,<0.3',
    'simplejson>=3.3.0,<4.0',
    'werkzeug>=0.9.4,<0.11',
    'markupsafe>=0.23,<1.0',
    'jinja2>=2.7.2,<3.0',
    'itsdangerous>=0.22,<1.0',
    'flask>=0.10.1,<0.11',
    'pymongo>=3.1',
    'flask-pymongo>=0.4',
]

try:
    from collections import OrderedDict  # noqa
except ImportError:
    # Python 2.6 needs this back-port
    install_requires.append('ordereddict')


setup(
    name='Eve',
    version='0.6.2.dev0',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Nicola Iarocci',
    author_email='eve@nicolaiarocci.com',
    url='http://python-eve.org',
    license='BSD',
    platforms=["any"],
    packages=find_packages(),
    test_suite="eve.tests",
    install_requires=install_requires,
    tests_require=['redis', 'testfixtures'],
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
