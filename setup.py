#!/usr/bin/env python
import io
import re
from collections import OrderedDict

from setuptools import find_packages, setup

DESCRIPTION = "Python REST API for Humans."
with open("README.rst") as f:
    LONG_DESCRIPTION = f.read()

with io.open("eve/__init__.py", "rt", encoding="utf8") as f:
    VERSION = re.search(r"__version__ = \"(.*?)\"", f.read()).group(1)

INSTALL_REQUIRES = [
    "cerberus>=1.1,<2.0",
    "events>=0.3,<0.4",
    "flask",
    "pymongo",
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
    packages=find_packages(exclude=["tests*"]),
    test_suite="tests",
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
