# -*- coding: utf-8 -*-
from __future__ import print_function

"""
    Custom event notifications
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Flask supports callback functions via decorators such as
    `before_request` and `after_request`. Being a subclass of Flask, Eve
    supports this mechanism too, and it's pretty darn powerful. The catch is
    that you need to be quite familiar with Flask internals, so for example if
    you want to inspect the `request` object you have to explicitly import it
    from flask.

    Checkout Eve at https://github.com/pyeve/eve

    This snippet by Nicola Iarocci can be used freely for anything you like.
    Consider it public domain.
"""
from flask import request
from eve import Eve
from notifications_settings import SETTINGS

app = Eve(auth=None, settings=SETTINGS)


@app.before_request
def before():
    print("the request object ready to be processed:", request)


@app.after_request
def after(response):
    """
    Your function must take one parameter, a `response_class` object and return
    a new response object or the same (see Flask documentation).
    """
    print("and here we have the response object instead:", response)
    return response


if __name__ == "__main__":
    app.run()
