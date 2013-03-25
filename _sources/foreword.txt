.. _foreword:

Introduction
============

Read this before you get started with Eve. This hopefully answers some
questions about the purpose and goals of the project, and when you should or
should not be using it.

Philosophy
----------
You have data stored somewhere and you want to expose it to your users
through a RESTful Web API. Eve is the tool that allows you to do so. 

The idea is that a robust API implementation is provided by Eve, and you just need
to configure API interface and behaviour, plug in your datasource, and you're
good to go. 

API settings are stored in a standard Python module (defaults to
``settings.py``), which makes customization quite a trivial task. It is also
possible to extend some key features, namely :ref:`auth`, Validation and Data
Access, by providing the Eve engine with custom objects.


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

Eve is released under terms of the :ref:`license`.


.. note::
    Work in progress.
