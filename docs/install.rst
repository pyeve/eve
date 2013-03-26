.. _install:

Installation
============
This part of the documentation covers the installation of Eve. The first step
to using any software package is getting it properly installed.

Distribute & Pip
----------------
Installing Eve is simple with `pip <http://www.pip-installer.org/>`_:

.. code-block:: console

    $ pip install eve

or, with `easy_install <http://pypi.python.org/pypi/setuptools>`_:

.. code-block:: console

    $ easy_install eve

But, you really `shouldn't do that <http://www.pip-installer.org/en/latest/other-tools.html#pip-compared-to-easy-install>`_.

Cheeseshop Mirror
-----------------
If the Cheeseshop is down, you can also install Eve from one of the mirrors.
`Crate.io <http://crate.io>`_ is one of them:

.. code-block:: console

    $ pip install -i http://simple.crate.io/ eve

Get the Code
------------
Eve is actively developed on GitHub, where the code is
`always available <https://github.com/nicolaiarocci/eve>`_. You can either
clone the public repository:

.. code-block:: console

    $ git clone git://github.com/nicolaiarocci/eve.git

Once you have a copy of the source, you can embed it in your Python package,
or install it into your site-packages easily:

.. code-block:: console

    $ python setup.py install
