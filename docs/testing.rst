Running the Tests 
=================
Eve runs under Python 2.6, Python 2.7, Python 3.3 and PyPy. Therefore tests
will be run in those four platforms in our `continuous integration server`_.

The easiest way to get started is to run the tests in your local environment
with:

.. code-block:: console

   $ python setup.py test 

If you want you can run a single module, say the ``methods`` suite:

.. code-block:: console

   $ python setup.py test -s eve.tests.methods

Or, to run only the ``get`` tests:

.. code-block:: console

   $ python setup.py test -s eve.tests.methods.get

You can also choose to just run a single class:

.. code-block:: console

   $ python setup.py test -s eve.tests.methods.get.TestGetItem

Or even a single class function:

.. code-block:: console

   $ python setup.py test -s eve.tests.methods.get.TestGetItem.test_expires


.. _test_prerequisites:

Prerequisites
-------------

Install the required dependencies for running tests and building documentation
by running ::

    $ pip install -r dev-requirements.txt

Testing with other python versions
----------------------------------
Before you submit a pull request, make sure your tests and changes run in
all supported python versions: 2.6, 2.7, 3.3, 3.4 and PyPy. Instead of creating all
those environments by hand, Eve uses tox_.

Make sure you have all required python versions installed and run:

.. code-block:: console

   $ pip install tox  # First time only
   $ tox

This might take some time the first run as the different virtual environments
are created and dependencies are installed. If everything is ok, you will see
the following:

.. code-block:: console

    _________ summary _________
    py26: commands succeeded
    py27: commands succeeded
    py33: commands succeeded
    py34: commands succeeded
    pypy: commands succeeded
    flake8: commands succeeded
    congratulations :)

If something goes **wrong** and one test fails, you might need to run that test
in the specific python version. You can use the created environments to run
some specific tests. For example, if a test suite fails in Python 3.4:

.. code-block:: console

    # From the project folder
    $ tox -e py34 -- -s eve.tests.methods.get.TestGetItem

Using Pytest
-------------
You also choose to run the whole test suite using pytest_:

.. code-block:: console
    
    # Run the whole test suite
    $ py.test                

    # Run all tests in the 'methods' folder
    $ py.test eve/tests/methods       

    # Run all the tests named 'TestEvents'
    $ py.test -k TestEvents   

    # Run the specific test class
    $ py.test eve/tests/methods/get.py::TestEvents 

    # Run the specific test
    $ py.test eve/tests/auth.py::TestBasicAuth::test_custom_auth


You can use pytest_ from tox_, but you will need to install it in the tox
environments before using it.

.. code-block:: console

    $ .tox/py26/bin/pip install pytest
    $ .tox/py26/bin/py.test

Please note that, just for my own convenience, the ``pytest.ini`` file is
currently set up in such a way that any test run will abort after two failures.
Also, if you are a Vim_ user (you should), you might want to check out the awesome
pytest.vim_ plugin.


RateLimiting and Redis
----------------------
While there are no test requirements for most of the suite, please be advised
that in order to execute the :ref:`ratelimiting` tests you need a running
Redis_ server, and redispy_ must be installed. The Rate-Limiting tests are
silently skipped if any of the two conditions are not met. 

Redispy will install automatically on the first test run, or you can install it
yourself with 

.. code-block:: console

    $ pip install redis
    
Continuous Integration
----------------------
Each time code is pushed to either the ``develop`` or the ``master``  branch
the whole test-suite is executed on Travis-CI. This is also the case for
pull-requests. When a pull request is submitted and the CI run fails two things
happen: a 'the build is broken' email is sent to the submitter; the request is
rejected.  The contributor can then fix the code, add one or more commits as
needed, and push again.

The CI will also run flake8 so make sure that your code complies to PEP8 before
submitting a pull request, or be prepared to be mail-spammed by CI.

Please note that in practice you're only supposed to submit pull requests
against the ``develop`` branch, see :ref:`contributing`.

Building documentation
----------------------
Eve uses Sphinx_ for its documentation. To build the documentation locally,
switch to the ``docs`` folder and run ::

    $ make html

This will generate html documentation in the folder ``~/code/eve.docs/html``,
which can be overridden with the ``BUILDDIR`` make variable ::

    $ make html BUILDDIR=/path/to/docs

Make sure Sphinx_ reports no errors or warnings when running the above.

To preview the documentation open ``index.html`` in the build directory ::

    $ open /path/to/docs/index.html

Alternatively switch to the build directory, start a local webserver ::

    $ python3 -m http.server

and then point your browser at ``localhost:8000``.

.. note::

    Eve uses a customised Sphinx_ theme based on alabaster_. The easiest way
    to get the right version is by installing the :ref:`test_prerequisites`.

.. _`continuous integration server`: https://travis-ci.org/nicolaiarocci/eve/
.. _tox: http://tox.readthedocs.org/en/latest/
.. _Redis:  http://redis.io/
.. _redispy: https://github.com/andymccurdy/redis-py
.. _simple: http://redis.io/topics/quickstart
.. _pytest: http://pytest.org
.. _pytest.vim: https://github.com/alfredodeza/pytest.vim
.. _Vim: http://en.wikipedia.org/wiki/Vim_(text_editor)
.. _Sphinx: http://sphinx-doc.org
.. _alabaster: https://pypi.python.org/pypi/alabaster
