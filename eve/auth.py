from flask import request, Response, current_app as app
from functools import wraps


def requires_auth(endpoint_class):
    """ Enables Authorization logic for decorated functions.

    :param endpoint_class: the 'class' to which the decorated endpoint belongs
                           to.  Can be 'resource' (resource endpoint), 'item'
                           (item endpoint) and 'home' for the API entry point.

    .. versionadded:: 0.0.4
    """
    def fdec(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if args:
                resource = app.config['DOMAIN'][args[0]]
            if endpoint_class == 'resource':
                public = resource['public_methods']
                roles = resource['allowed_roles']
            elif endpoint_class == 'item':
                public = resource['public_item_methods']
                roles = resource['allowed_item_roles']
            elif endpoint_class == 'home':
                public = app.config['PUBLIC_METHODS']
                roles = app.config['ALLOWED_ROLES']
            if app.auth and request.method not in public:
                if not app.auth.authorized(roles):
                    return app.auth.authenticate()
            return f(*args, **kwargs)
        return decorated
    return fdec


class BasicAuth(object):
    """ Implements Basic AUTH logic. Should be subclassed to implement custom
    authorization checking.

    .. versionadded:: 0.0.4
    """
    def check_auth(self, username, password, allowed_roles):
        """ This function is called to check if a username / password
        combination is valid. Must be overridden with custom logic.

        :param username: decoded user name.
        :param password: decoded user password.
        :param allowed_roles: allowed user allowed_roles
        """
        raise NotImplementedError

    def authenticate(self):
        """ Returns a standard a 401 response that enables basic auth.
        Ovverride if you want to change the response and/or the realm.
        """
        return Response(
            'Please provide proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm:"%s"' % __package__})

    def authorized(self, allowed_roles):
        """ Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        """
        auth = request.authorization
        return auth and self.check_auth(auth.username, auth.password,
                                        allowed_roles)
