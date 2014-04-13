from flask import request, Response, current_app as app, g
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
                # resource or item endpoint
                resource_name = args[0]
                resource = app.config['DOMAIN'][args[0]]
                if endpoint_class == 'resource':
                    public = resource['public_methods']
                    roles = resource['allowed_roles']
                elif endpoint_class == 'item':
                    public = resource['public_item_methods']
                    roles = resource['allowed_item_roles']
                auth = resource['authentication']
            else:
                # home
                resource_name = resource = None
                public = app.config['PUBLIC_METHODS'] + ['OPTIONS']
                roles = app.config['ALLOWED_ROLES']
                auth = app.auth
            if auth and request.method not in public:
                if not auth.authorized(roles, resource_name, request.method):
                    return auth.authenticate()
            return f(*args, **kwargs)
        return decorated
    return fdec


class BasicAuth(object):
    """ Implements Basic AUTH logic. Should be subclassed to implement custom
    authentication checking.

    .. versionchanged:: 0.4
       auth.request_auth_value replaced with getter and setter methods which
       rely on flask's 'g' object, for enhanced thread-safity.

    .. versionchanged:: 0.1.1
        auth.request_auth_value is now used to store the auth_field value.

    .. versionchanged:: 0.0.9
       Support for user_id property.

    .. versionchanged:: 0.0.7
       Support for 'resource' argument.

    .. versionadded:: 0.0.4
    """
    def set_request_auth_value(self, value):
        g.auth_value = value

    def get_request_auth_value(self):
        return g.get("auth_value")

    def check_auth(self, username, password, allowed_roles, resource, method):
        """ This function is called to check if a username / password
        combination is valid. Must be overridden with custom logic.

        :param username: username provided with current request.
        :param password: password provided with current request
        :param allowed_roles: allowed user roles.
        :param resource: resource being requested.
        :param method: HTTP method being executed (POST, GET, etc.)
        """
        raise NotImplementedError

    def authenticate(self):
        """ Returns a standard a 401 response that enables basic auth.
        Override if you want to change the response and/or the realm.
        """
        return Response(
            'Please provide proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm:"%s"' % __package__})

    def authorized(self, allowed_roles, resource, method):
        """ Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        :param resource: resource being requested.
        """
        auth = request.authorization
        return auth and self.check_auth(auth.username, auth.password,
                                        allowed_roles, resource, method)


class HMACAuth(BasicAuth):
    """ Hash Message Authentication Code (HMAC) authentication logic. Must be
    subclassed to implement custom authorization checking.

    .. versionchanged:: 0.0.9
       Replaced the now deprecated request.data with request.get_data().

    .. versionchanged:: 0.0.7
       Support for 'resource' argument.

    .. versionadded:: 0.0.5
    """
    def check_auth(self, userid, hmac_hash, headers, data, allowed_roles,
                   resource, method):
        """ This function is called to check if a token is valid. Must be
        overridden with custom logic.

        :param userid: user id included with the request.
        :param hmac_hash: hash included with the request.
        :param headers: request headers. Suitable for hash computing.
        :param data: request data. Suitable for hash computing.
        :param allowed_roles: allowed user roles.
        :param resource: resource being requested.
        :param method: HTTP method being executed (POST, GET, etc.)
        """
        raise NotImplementedError

    def authenticate(self):
        """ Returns a standard a 401. Override if you want to change the
        response.
        """
        return Response('Please provide proper credentials', 401)

    def authorized(self, allowed_roles, resource, method):
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
                                        request.get_data(), allowed_roles,
                                        resource, method)


class TokenAuth(BasicAuth):
    """ Implements Token AUTH logic. Should be subclassed to implement custom
    authentication checking.

    .. versionchanged:: 0.0.7
       Support for 'resource' argument.

    .. versionadded:: 0.0.5
    """
    def check_auth(self, token, allowed_roles, resource, method):
        """ This function is called to check if a token is valid. Must be
        overridden with custom logic.

        :param token: decoded user name.
        :param allowed_roles: allowed user roles
        :param resource: resource being requested.
        :param method: HTTP method being executed (POST, GET, etc.)
        """
        raise NotImplementedError

    def authenticate(self):
        """ Returns a standard a 401 response that enables basic auth.
        Override if you want to change the response and/or the realm.
        """
        return Response(
            'Please provide proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm:"%s"' % __package__})

    def authorized(self, allowed_roles, resource, method):
        """ Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        :param resource: resource being requested.
        """
        auth = request.authorization
        return auth and self.check_auth(auth.username, allowed_roles, resource,
                                        method)


def auth_field_and_value(resource):
    """ If auth is active and the resource requires it, return both the
    current request 'request_auth_value' and the 'auth_field' for the resource

    .. versionchanged:: 0.4
       Use new auth.request_auth_value() method.

    .. versionadded:: 0.3
    """
    if '|resource' in request.endpoint:
        # We are on a resource endpoint and need to check against
        # `public_methods`
        public_method_list_to_check = 'public_methods'
    else:
        # We are on an item endpoint and need to check against
        # `public_item_methods`
        public_method_list_to_check = 'public_item_methods'

    resource_dict = app.config['DOMAIN'][resource]
    auth = resource_dict['authentication']

    request_auth_value = auth.get_request_auth_value() if auth else None
    auth_field = resource_dict.get('auth_field', None) if request.method not \
        in resource_dict[public_method_list_to_check] else None

    return auth_field, request_auth_value
