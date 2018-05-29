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

Eve provides a robust, feature rich, REST-centered API implementation,
and you just need to configure your API settings and behavior, plug in your
datasource, and you're good to go. See :doc:`features` for a list
of features available to Eve-powered APIs. You might want to check the
:doc:`rest_api_for_humans` slide deck too.

API settings are stored in a standard Python module (defaults to
``settings.py``), which makes customization quite a trivial task. It is also
possible to extend some key features, namely :ref:`auth`, :ref:`validation` and
Data Access, by providing the Eve engine with custom objects.

A little context
----------------
At `Gestionale Amica <http://gestionaleamica.com>`_ we had been working hard on
a full featured, Python powered, RESTful Web API. We learned quite a few things
on REST best patterns, and we had a chance to put Python's renowned web
capabilities to the test. Then, at EuroPython 2012, I had the opportunity to share
what we learned.  My talk sparked quite a bit of interest, and even after a few
months had passed, the slides were still receiving a lot of hits every day.
I kept receiving emails asking for source code examples and whatnot. After all,
a REST API lies in the future of every web-oriented developer, and who isn't
one these days?

So, I thought, perhaps I could take the proprietary, closed code (codenamed
'Adam') and refactor it "just a little bit", so that it could fit a much wider
number of use cases. I could then release it as an open source project. Well
it turned out to be slightly more complex than that but finally here it is, and
of course it's called Eve.

REST, Flask and MongoDB
-----------------------
The slides from my EuroPython talk, *Developing RESTful Web APIs with Flask and
MongoDB*, are `available online`_. You might want to check them out to understand
why and how certain design decisions were made, especially with regards to REST
implementation.

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
