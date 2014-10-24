How to Contribute
#################

Contributions are welcome! Not familiar with the codebase yet? No problem!
There are many ways to contribute to open source projects: reporting bugs,
helping with the documentation, spreading the word and of course, adding
new features and patches. 

Getting Started
---------------
#. Make sure you have a GitHub_ account.
#. Open a `new issue`_, assuming one does not already exist.
#. Clearly describe the issue including steps to reproduce when it is a bug.

Making Changes
--------------
* Fork_ the repository on GitHub.
* Create a topic branch from where you want to base your work.
* This is usually the ``develop`` branch. 
* Please avoid working directly on the ``develop`` branch.
* Make commits of logical units (if needed rebase your feature branch before
  submitting it).
* Check for unnecessary whitespace with ``git diff --check`` before committing.
* Make sure your commit messages are in the `proper format`_.
* If your commit fixes an open issue, reference it in the commit message (#15).
* Make sure your code conforms to PEP8_ (we're using flake8_ for PEP8 and extra checks).
* Make sure you have added the necessary tests for your changes.
* Run all the tests to assure nothing else was accidentally broken.
* Run again the entire suite via tox_ to check your changes against multiple
  python versions. ``pip install tox; tox``
* Don't forget to add yourself to AUTHORS_.

These guidelines also apply when helping with documentation (actually,
for typos and minor additions you might choose to `fork and
edit`_). See also the `running the tests`_ section in the official
documentation.

Submitting Changes
------------------
* Push your changes to a topic branch in your fork of the repository.
* Submit a `Pull Request`_.
* Wait for maintainer feedback.

Join us on IRC
--------------
If you're interested in contributing to the Eve project or have questions
about it come join us in our little #python-eve channel on irc.freenode.net.
It's comfy and cozy over there.

First time contributor?
-----------------------
It's alright. We've all been there. See next chapter.

Don't know where to start? 
--------------------------
There are usually several TODO comments scattered around the codebase, maybe
check them out and see if you have ideas, or can help with them. Also, check
the `open issues`_ in case there's something that sparks your interest (there's
also a special ``contributor friendly`` label flagging some interesting feature
requests). And what about documentation?  I suck at English so if you're fluent
with it (or notice any typo and/or mistake), why not help with that? In any
case, other than GitHub help_ pages, you might want to check this excellent
`Effective Guide to Pull Requests`_

.. _`the repository`: http://github.com/nicolaiarocci/eve
.. _AUTHORS: https://github.com/nicolaiarocci/eve/blob/develop/AUTHORS
.. _`open issues`: https://github.com/nicolaiarocci/eve/issues
.. _`new issue`: https://github.com/nicolaiarocci/eve/issues/new
.. _GitHub: https://github.com/
.. _Fork: https://help.github.com/articles/fork-a-repo
.. _`proper format`: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
.. _PEP8: http://www.python.org/dev/peps/pep-0008/
.. _flake8: http://flake8.readthedocs.org/en/latest/
.. _tox: http://tox.readthedocs.org/en/latest/
.. _help: https://help.github.com/
.. _`Effective Guide to Pull Requests`: http://codeinthehole.com/writing/pull-requests-and-other-good-practices-for-teams-using-github/
.. _`fork and edit`: https://github.com/blog/844-forking-with-the-edit-button
.. _`Pull Request`: https://help.github.com/articles/creating-a-pull-request
.. _`running the tests`: http://python-eve.org/testing#running-the-tests


