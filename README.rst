Eve
===
.. image:: https://secure.travis-ci.org/nicolaiarocci/eve.png?branch=master 
        :target: https://secure.travis-ci.org/nicolaiarocci/eve

*Eve is an out-of-the-box, highly customizable and fully featured RESTful Web
API framework that you can use to effortlessly build and deploy your own APIs*

Documentation
-------------
Please see the Eve website at http://python-eve.org

Live demo and examples
----------------------
Check out the live demo of a Eve-powered API at
https://github.com/nicolaiarocci/eve-demo. It comes with source code and usage
examples for all common use cases (GET, POST, PATCH, DELETE and more). There is
also a sample client app available. Check it out at
https://github.com/nicolaiarocci/eve-demo-client.

Installation
------------
Eve is on PyPI so all you need to do is

::

    pip install eve


Testing
-------
Just run

::
    
    python setup.py test

Eve has been tested successfully under Python 2.7 and Python 2.6.

License
-------
Eve is BSD licensed. See the `LICENSE
<https://github.com/nicolaiarocci/eve/blob/master/LICENSE>`_ for details.

Contributing
------------
Please see the `Contribution Guidelines`_.

Join us on IRC
--------------
If you're interested in contributing to the Eve project or have questions
about it come join us in our little #evehq channel on irc.freenode.net. It's
comfy and cozy over there.

Current state
-------------
Consider this a public preview (Alpha). Best way to be notified about its
availability is by starring/following the project repo at GitHub
https://github.com/nicolaiarocci/eve. You can follow me on Twitter at
http://twitter.com/nicolaiarocci.

A little context
----------------
At `Gestionale Amica <http://gestionaleamica.com>`_ we had been working hard on
a full featured, Python powered, RESTful Web API. We learned quite a few things
on REST best patterns, and we got a chance to put Python's renowned web
capabilities under review. Then, at EuroPython 2012, I got a chance to share
what we learned and my talk sparked quite a bit of interest there. A few months
have passed and still the slides are receiving a lot of hits each day, and
I keep receiving emails about source code samples and whatnot. After all,
a REST API lies in the future of every web-oriented developer, and who isn't
these days?

So I thought that perhaps I could take the proprietary, closed code (codenamed
'Adam') and refactor it "just a little bit", so that it could fit a much wider
number of use cases. I could then release it as an open source project. Well
it turned out to be slightly more complex than that but finally here it is, and
of course it's called Eve.

It still got a long way to go before it becomes the fully featured open source,
out-of-the-box API solution I came to envision (see the Roadmap below), but
I feel that at this point the codebase is ready enough for a public preview.
This will hopefully allow for some constructive feedback and maybe, for some
contributors to join the ranks.

PS: the slides of my EuroPython REST API talk are `available online`_. You
might want to check them to understand why and how certain design decisions
were made, especially with regards to REST implementation.

Roadmap
-------
In no particular order, here's a partial list of the features that I plan/would
like to add to Eve, provided that there is enough interest in the project.

- Documentation (coming soon!)
- Granular exception handling
- Journaling/error logging
- Server side caching
- Alternative sort syntax (``?sort=name``)
- Authentication (Digest, Oauth?)
- Support for MySQL and/or other SQL/NoSQL databases

.. _available online: https://speakerdeck.com/u/nicola/p/developing-restful-web-apis-with-python-flask-and-mongodb
.. _`Contribution Guidelines`: https://github.com/nicolaiarocci/eve/blob/develop/CONTRIBUTING.rst
