#!/usr/bin/env python
import io
import re

from setuptools import setup, find_packages
from collections import OrderedDict

DESCRIPTION = "Python REST API for Humans."
with open("README.rst") as f:
    LONG_DESCRIPTION = f.read()

with io.open("eve/__init__.py", "rt", encoding="utf8") as f:
    VERSION = re.search(r"__version__ = \"(.*?)\"", f.read()).group(1)

INSTALL_REQUIRES = [
    "cerberus>=1.1,<2.0",
    "events>=0.3,<0.4",
    "flask",
    "pymongo>=3.7",
    "simplejson>=3.3.0,<4.0",
]

EXTRAS_REQUIRE = {
    "docs": ["sphinx", "alabaster", "doc8"],
    "tests": ["redis", "testfixtures", "pytest", "tox"],
}
EXTRAS_REQUIRE["dev"] = EXTRAS_REQUIRE["tests"] + EXTRAS_REQUIRE["docs"]

setup(
    name="Eve",
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/x-rst",
    author="Nicola Iarocci",
    author_email="eve@nicolaiarocci.com",
    url="http://python-eve.org",
    project_urls=OrderedDict(
        (
            ("Documentation", "http://python-eve.org"),
            ("Code", "https://github.com/pyeve/eve"),
            ("Issue tracker", "https://github.com/pyeve/eve/issues"),
        )
    ),
    license="BSD",
    platforms=["any"],
    packages=find_packages(),
    test_suite="eve.tests",
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    python_requires=">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*, !=3.4.*",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
