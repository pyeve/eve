from __future__ import absolute_import

import logging
from flask import request


# TODO right now we are only logging exceptions. We should probably
# add support for some INFO and maybe DEBUG level logging (like, log each time
# a endpoint is hit, etc.)

class RequestFilter(logging.Filter):
    """ Adds Flask's request metadata to the log record so handlers can log
    this information too.

    import logging

    handler = logging.FileHandler('app.log')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(filename)s:%(lineno)d] -- ip: %(clientip)s url: %(url)s'))
    app.logger.addHandler(handler)

    The above example adds 'clientip' and request 'url' to every log record.

    Note that the app.logger can also be used by callback functions.

    def log_a_get(resoure, request, payload):
        app.logger.info('we just responded to a GET request!')

    app = Eve()
    app.on_post_GET += log_a_get

    .. versionadded:: 0.6

    """
    def filter(self, record):
        if request:
            record.clientip = request.remote_addr
            record.url = request.url
            record.method = request.method
        else:
            record.clientip = None
            record.url = None
            record.method = None

        return True
