.. _foreword:

Foreword
========

Read this before you get started with Eve. This hopefully answers some
questions about the purpose and goals of the project, and when you should or
should not be using it.

Philosophy
----------
You have data stored somewhere and you want to expose it to your users
through a RESTful Web API. Eve is the tool that allows you to do so. 

The idea is that a robust, feature rich, REST-centered API implementation is
provided by Eve, and you just need to configure API interface and behaviour,
plug in your datasource, and you're good to go. See :doc:`features` for a list
of features available to Eve-powered APIs.

API settings are stored in a standard Python module (defaults to
``settings.py``), which makes customization quite a trivial task. It is also
possible to extend some key features, namely :ref:`auth`, :ref:`validation` and
Data Access, by providing the Eve engine with custom objects.

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

So, I thought, perhaps I could take the proprietary, closed code (codenamed
'Adam') and refactor it "just a little bit", so that it could fit a much wider
number of use cases. I could then release it as an open source project. Well
it turned out to be slightly more complex than that but finally here it is, and
of course it's called Eve.

It still got a long way to go before it becomes the fully featured open source,
out-of-the-box API solution I came to envision (see the Roadmap below), but
I feel that at this point the codebase is ready enough for a public preview.
This will hopefully allow for some constructive feedback and maybe, for some
contributors to join the ranks.

REST, Flask and MongoDB
-----------------------
The slides of my EuroPython talk, *Developing RESTful Web APIs with Flask and
MongoDB*, are `available online`_. You might want to check them to understand
why and how certain design decisions were made, especially with regards to REST
implementation.

Roadmap
-------
In no particular order, here's a partial list of the features that I plan/would
like to add to Eve, provided that there is enough interest in the project.

- Documentation (working on it!)
- Granular exception handling
- Journaling/logging
- Server side caching
- Alternative sort syntax (``?sort=name``)
- More authentication schemes
- Support for MySQL and/or other SQL/NoSQL databases

BSD License 
-----------
A large number of open source projects you find today are GPL Licensed. While
the GPL has its time and place, it should most certainly not be your go-to
license for your next open source project.

A project that is released as GPL cannot be used in any commercial product
without the product itself also being offered as open source.

The MIT, BSD, ISC, and Apache2 licenses are great alternatives to the GPL that
allow your open-source software to be used freely in proprietary, closed-source
software.

Eve is released under terms of the BSD License. See :ref:`license`.

.. _available online: https://speakerdeck.com/u/nicola/p/developing-restful-web-apis-with-python-flask-and-mongodb
