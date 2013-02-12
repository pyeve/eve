from flask import request, Response, current_app as app
from functools import wraps


def requires_auth(f):
    """ Enables Authorization logic for decorated functions.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if app.auth and not app.auth.authorized():
            return app.auth.authenticate()
        return f(*args, **kwargs)
    return decorated


class BasicAuth(object):
    """ Implements Basic AUTH logic. Should be subclassed to implement custom
    authorization checking.

    .. versionadded:: 0.0.4
    """
    def check_auth(self, username, password):
        """ This function is called to check if a username / password
        combination is valid. Must be overridden with custom logic.

        :param username: user name.
        :param password: user password.
        """
        #raise NotImplementedError
        return username == 'admin' and password == 'secret'

    def authenticate(self):
        """ Returns a standard a 401 response that enables basic auth.
        Ovverride if you want to change the response and/or the realm.
        """
        return Response(
            'Please provide proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm:"%s"' % __package__})

    def authorized(self):
        auth = request.authorization
        return auth and self.check_auth(auth.username, auth.password)
