Running the Tests 
=================
Just run:

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
In order to run successfully the :ref:`ratelimiting` suite needs both
a running Redis_ server and redispy_ to be installed. If any of these
conditions is not satisfied the suite will just be silently skipped.

While you have to install Redis by yourself (it is really easy_), redispy will
install automatically on the first test run. Of course you can still install it
yourself, if so you wish:

.. code-block:: console

   $ pip install redis

.. _Redis:  http://redis.io/
.. _redispy: https://github.com/andymccurdy/redis-py
.. _easy: http://redis.io/topics/quickstart
