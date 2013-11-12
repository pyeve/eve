Running the Tests 
=================
The test suite runs under Python 2.6, Python 2.7 and Python 3.3. To execute it
locally just run:

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

   $ python setup.py test -s eve.tests.methods.get.TestGetItem.test_get_max_results

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

.. _Redis:  http://redis.io/
.. _redispy: https://github.com/andymccurdy/redis-py
.. _simple: http://redis.io/topics/quickstart
