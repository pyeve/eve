from flask import request, Response, current_app as app
from functools import wraps


def requires_auth(endpoint_class):
    """ Enables Authorization logic for decorated functions.

    :param endpoint_class: the 'class' to which the decorated endpoint belongs
                           to.  Can be 'resource' (resource endpoint), 'item'
                           (item endpoint) and 'home' for the API entry point.

    .. versionchanged:: 0.0.7
       Passing the 'resource' argument when inoking auth.authenticate()

    .. versionchanged:: 0.0.5
       Support for Cross-Origin Resource Sharing (CORS): 'OPTIONS' request
       method is now public by default. The actual method ('GET', etc.) will
       still be protected if so configured.

    .. versionadded:: 0.0.4
    """
    def fdec(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if args:
                resource_name = args[0]
                resource = app.config['DOMAIN'][args[0]]
            else:
                resource_name = resource = None
            if endpoint_class == 'resource':
                public = resource['public_methods']
                roles = resource['allowed_roles']
            elif endpoint_class == 'item':
                public = resource['public_item_methods']
                roles = resource['allowed_item_roles']
            elif endpoint_class == 'home':
                public = app.config['PUBLIC_METHODS'] + ['OPTIONS']
                roles = app.config['ALLOWED_ROLES']
            if app.auth and request.method not in public:
                if not app.auth.authorized(roles, resource_name):
                    return app.auth.authenticate()
            return f(*args, **kwargs)
        return decorated
    return fdec


class BasicAuth(object):
    """ Implements Basic AUTH logic. Should be subclassed to implement custom
    authorization checking.

    .. versionchanged:: 0.0.7
       Support for 'resource' argument.

    .. versionadded:: 0.0.4
    """
    def check_auth(self, username, password, allowed_roles, resource):
        """ This function is called to check if a username / password
        combination is valid. Must be overridden with custom logic.

        :param resource: resource being requested.
        """
        raise NotImplementedError

    def authenticate(self):
        """ Returns a standard a 401 response that enables basic auth.
        Ovverride if you want to change the response and/or the realm.
        """
        return Response(
            'Please provide proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm:"%s"' % __package__})

    def authorized(self, allowed_roles, resource):
        """ Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        :param resource: resource being requested.
        """
        auth = request.authorization
        return auth and self.check_auth(auth.username, auth.password,
                                        allowed_roles, resource)


class HMACAuth(BasicAuth):
    """ Hash Message Authentication Code (HMAC) authentication logic. Must be
    subclassed to implement custom authorization checking.

    .. versionchanged:: 0.0.7
       Support for 'resource' argument.

    .. versionadded:: 0.0.5
    """
    def check_auth(self, userid, hmac_hash, headers, data, allowed_roles,
                   resource):
        """ This function is called to check if a token is valid. Must be
        overridden with custom logic.

        :param userid: user id included with the request.
        :param hmac: hash included with the request.
        :param headers: request headers. Suitable for hash computing.
        :param data: request data. Suitable for hash computing.
        :param allowed_roles: allowed user roles.
        :param resource: resource being requested.
        """
        raise NotImplementedError

    def authenticate(self):
        """ Returns a standard a 401. Ovverride if you want to change the
        response.
        """
        return Response('Please provide proper credentials', 401)

    def authorized(self, allowed_roles, resource):
        """ Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        :param resource: resource being requested.
        """
        auth = request.headers.get('Authorization')
        try:
            userid, hmac_hash = auth.split(':')
        except:
            auth = None
        return auth and self.check_auth(userid, hmac_hash, request.headers,
                                        request.data, allowed_roles, resource)


class TokenAuth(BasicAuth):
    """ Implements Token AUTH logic. Should be subclassed to implement custom
    authorization checking.

    .. versionchanged:: 0.0.7
       Support for 'resource' argument.

    .. versionadded:: 0.0.5
    """
    def check_auth(self, token, allowed_roles, resource):
        """ This function is called to check if a token is valid. Must be
        overridden with custom logic.

        :param token: decoded user name.
        :param allowed_roles: allowed user roles
        :param resource: resource being requested.
        """
        raise NotImplementedError

    def authenticate(self):
        """ Returns a standard a 401 response that enables basic auth.
        Ovverride if you want to change the response and/or the realm.
        """
        return Response(
            'Please provide proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm:"%s"' % __package__})

    def authorized(self, allowed_roles, resource):
        """ Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        :param resource: resource being requested.
        """
        auth = request.authorization
        return auth and self.check_auth(auth.username, allowed_roles, resource)
