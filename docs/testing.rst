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

RateLimting and Redis
---------------------
While there are no test requirements for most of the suite, please be advised
that in order to execute the :ref:`ratelimiting` tests you need a running
Redis_ server, and that redispy_ must be installed. The Rate-Limiting tests are
silently skipped if any of the two conditions are not met. 

Redispy will install automatically on the first test run, or you can install it
yourself with 

.. code-block:: console

    $ pip install redis
    
but again, if you want Rate-Limit tests to execute, you will have to make sure
that Redis is installed (that's simple_) and that an instance of
``redis-server`` is running. 

.. _Redis:  http://redis.io/
.. _redispy: https://github.com/andymccurdy/redis-py
.. _simple: http://redis.io/topics/quickstart
