How to contribute
=================

Contributions are welcome! Not familiar with the codebase yet? No problem!
There are many ways to contribute to open source projects: reporting bugs,
helping with the documentation, spreading the word and of course, adding
new features and patches.

Support questions
-----------------

Please, don't use the issue tracker for this. Use one of the following
resources for questions about your own code:

* Ask on `Stack Overflow`_. Search with Google first using: ``site:stackoverflow.com eve {search term, exception message, etc.}``
* The `mailing list`_ is intended to be a low traffic resource for both developers/contributors and API maintainers looking for help or requesting feedback.
* The IRC channel ``#python-eve`` on FreeNode.

.. _Stack Overflow: https://stackoverflow.com/questions/tagged/eve?sort=linked
.. _`mailing list`: https://groups.google.com/forum/#!forum/python-eve

Reporting issues
----------------

- Describe what you expected to happen.
- If possible, include a `minimal, complete, and verifiable example`_ to help
  us identify the issue. This also helps check that the issue is not with your
  own code.
- Describe what actually happened. Include the full traceback if there was an
  exception.
- List your Python and Eve versions. If possible, check if this issue is
  already fixed in the repository.

.. _minimal, complete, and verifiable example: https://stackoverflow.com/help/mcve

Submitting patches
------------------

- Include tests if your patch is supposed to solve a bug, and explain
  clearly under which circumstances the bug happens. Make sure the test fails
  without your patch.
- Enable and install pre-commit_ to ensure styleguides and codechecks are
  followed. CI will reject a change that does not conform to the guidelines.

.. _pre-commit: https://pre-commit.com/

First time setup
~~~~~~~~~~~~~~~~

- Download and install the `latest version of git`_.
- Configure git with your `username`_ and `email`_::

        git config --global user.name 'your name'
        git config --global user.email 'your email'

- Make sure you have a `GitHub account`_.
- Fork Eve to your GitHub account by clicking the `Fork`_ button.
- `Clone`_ your GitHub fork locally::

        git clone https://github.com/{username}/eve
        cd eve

- Add the main repository as a remote to update later::

        git remote add pyeve https://github.com/pyeve/eve
        git fetch pyeve

- Create a virtualenv::

        python3 -m venv env
        . env/bin/activate
        # or "env\Scripts\activate" on Windows

- Install Eve in editable mode with development dependencies::

        pip install -e ".[dev]"

- Install pre-commit_ and then activate its hooks. pre-commit is a framework for managing and maintaining multi-language pre-commit hooks. Eve uses pre-commit to ensure code-style and code formatting is the same::

    $ pip install --user pre-commit
    $ pre-commit install

  Afterwards, pre-commit will run whenever you commit.


.. _GitHub account: https://github.com/join
.. _latest version of git: https://git-scm.com/downloads
.. _username: https://help.github.com/articles/setting-your-username-in-git/
.. _email: https://help.github.com/articles/setting-your-email-in-git/
.. _Fork: https://github.com/pallets/flask/fork
.. _Clone: https://help.github.com/articles/fork-a-repo/#step-2-create-a-local-clone-of-your-fork

Start coding
~~~~~~~~~~~~

- Create a branch to identify the issue you would like to work on (e.g.
  ``fix_for_#1280``)
- Using your favorite editor, make your changes, `committing as you go`_.
- Follow `PEP8`_.
- Include tests that cover any code changes you make. Make sure the test fails
  without your patch. `Run the tests. <contributing-testsuite_>`_.
- Push your commits to GitHub and `create a pull request`_.
- Celebrate 🎉

.. _committing as you go: http://dont-be-afraid-to-commit.readthedocs.io/en/latest/git/commandlinegit.html#commit-your-changes
.. _PEP8: https://pep8.org/
.. _create a pull request: https://help.github.com/articles/creating-a-pull-request/

.. _contributing-testsuite:

Running the tests
~~~~~~~~~~~~~~~~~

You should have both Python 2.7 and 3.6 available in your system. Now
running tests is as simple as issuing this command::

    $ tox -e linting,py27,py36

This command will run tests via the "tox" tool against Python 2.7 and 3.6 and
also perform "lint" coding-style checks.

You can pass different options to ``tox``. For example, to run tests on Python
2.7 and pass options to pytest (e.g. enter pdb on failure) to pytest you can
do::

    $ tox -e py27 -- --pdb

Or to only run tests in a particular test module on Python 3.6::

    $ tox -e py36 -- -k TestGet

Travis-CI will run the full suite when you submit your pull request. The full
test suite takes a long time to run because it tests multiple combinations of
Python and dependencies. You need to have Python 2.7, 3.4, 3.5, 3.6, and PyPy
installed to run all of the environments. Then run::

    tox

Please note that you need an active MongoDB instance running on localhost in
order for the tests run. Also, be advived that in order to execute the
:ref:`ratelimiting` tests you need a running Redis_ server. The Rate-Limiting
tests are silently skipped if any of the two conditions are not met.

Building the docs
~~~~~~~~~~~~~~~~~
Build the docs in the ``docs`` directory using Sphinx::

    cd docs
    make html

Open ``_build/html/index.html`` in your browser to view the docs.

Read more about `Sphinx <http://www.sphinx-doc.org>`_.

make targets
~~~~~~~~~~~~
Eve provides a ``Makefile`` with various shortcuts. They will ensure that
all dependencies are installed.

- ``make test`` runs the basic test suite with ``pytest``
- ``make test-all`` runs the full test suite with ``tox``
- ``make docs`` builds the HTML documentation
- ``make check`` performs some checks on the package
- ``make install-dev`` install Eve in editable mode with all development dependencies.

First time contributor?
-----------------------
It's alright. We've all been there. See next chapter.

Don't know where to start?
--------------------------
There are usually several TODO comments scattered around the codebase, maybe
check them out and see if you have ideas, or can help with them. Also, check
the `open issues`_ in case there's something that sparks your interest. And
what about documentation? I suck at English, so if you're fluent with it (or
notice any typo and/or mistake), why not help with that? In any case, other
than GitHub help_ pages, you might want to check this excellent `Effective
Guide to Pull Requests`_

.. _`the repository`: http://github.com/pyeve/eve
.. _AUTHORS: https://github.com/pyeve/eve/blob/master/AUTHORS
.. _`open issues`: https://github.com/pyeve/eve/issues
.. _`new issue`: https://github.com/pyeve/eve/issues/new
.. _GitHub: https://github.com/
.. _`proper format`: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
.. _flake8: http://flake8.readthedocs.org/en/latest/
.. _tox: http://tox.readthedocs.org/en/latest/
.. _help: https://help.github.com/
.. _`Effective Guide to Pull Requests`: http://codeinthehole.com/writing/pull-requests-and-other-good-practices-for-teams-using-github/
.. _`fork and edit`: https://github.com/blog/844-forking-with-the-edit-button
.. _`Pull Request`: https://help.github.com/articles/creating-a-pull-request
.. _`running the tests`: http://python-eve.org/testing#running-the-tests
.. _Redis: https://redis.io
