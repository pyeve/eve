# -*- coding: utf-8 -*-

"""
    eve.auth
    ~~~~~~~~

    Allow API endpoints to be secured via BasicAuth and derivates.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
from flask import request, Response, current_app as app, g, abort
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
            if endpoint_class == 'resource' or endpoint_class == 'item':
                if args:
                    resource_name = args[0]
                elif kwargs.get('resource'):
                    resource_name = kwargs.get('resource')
                else:
                    raise ValueError("'requires_auth(%s)' decorated functions "
                                     "must include resource in args or kwargs"
                                     % endpoint_class)

                # fetch resource or item auth configuration
                resource = app.config['DOMAIN'].get(resource_name)
                if resource is None:
                    abort(404)
                if endpoint_class == 'resource':
                    public = resource['public_methods']
                    roles = list(resource['allowed_roles'])
                    if request.method in ['GET', 'HEAD', 'OPTIONS']:
                        roles += resource['allowed_read_roles']
                    else:
                        roles += resource['allowed_write_roles']
                elif endpoint_class == 'item':
                    public = resource['public_item_methods']
                    roles = list(resource['allowed_item_roles'])
                    if request.method in ['GET', 'HEAD', 'OPTIONS']:
                        roles += resource['allowed_item_read_roles']
                    else:
                        roles += resource['allowed_item_write_roles']
                auth = resource_auth(resource_name)
            else:
                # home or media endpoints
                resource_name = resource = None
                public = app.config['PUBLIC_METHODS'] + ['OPTIONS']
                roles = list(app.config['ALLOWED_ROLES'])
                if request.method in ['GET', 'OPTIONS']:
                    roles += app.config['ALLOWED_READ_ROLES']
                else:
                    roles += app.config['ALLOWED_WRITE_ROLES']
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

    .. versionchanged:: 0.7
       Add support for get_user_or_token()/set_user_or_token(). This allows for
       easy retrieval of active user information. See #846.

    .. versionchanged:: 0.6
       Add mongo_prefix getter and setter methods.

    .. versionchanged:: 0.4
       ensure all errors returns a parseable body #366.
       auth.request_auth_value replaced with getter and setter methods which
       rely on flask's 'g' object, for enhanced thread-safety.

    .. versionchanged:: 0.1.1
        auth.request_auth_value is now used to store the auth_field value.

    .. versionchanged:: 0.0.9
       Support for user_id property.

    .. versionchanged:: 0.0.7
       Support for 'resource' argument.

    .. versionadded:: 0.0.4
    """
    def set_mongo_prefix(self, value):
        g.mongo_prefix = value

    def get_mongo_prefix(self):
        return g.get('mongo_prefix')

    def set_request_auth_value(self, value):
        g.auth_value = value

    def get_request_auth_value(self):
        return g.get('auth_value')

    def get_user_or_token(self):
        return g.get('user')

    def set_user_or_token(self, user):
        g.user = user

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
        resp = Response(None, 401, {'WWW-Authenticate': 'Basic realm="%s"' %
                                    __package__})
        abort(401, description='Please provide proper credentials',
              response=resp)

    def authorized(self, allowed_roles, resource, method):
        """ Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        :param resource: resource being requested.
        """
        auth = request.authorization
        if auth:
            self.set_user_or_token(auth.username)
        return auth and self.check_auth(auth.username, auth.password,
                                        allowed_roles, resource, method)


class HMACAuth(BasicAuth):
    """ Hash Message Authentication Code (HMAC) authentication logic. Must be
    subclassed to implement custom authorization checking.

    .. versionchanged:: 0.7
       Add support for get_user_or_token()/set_user_or_token(). This allows for
       easy retrieval of active user information. See #846.

    .. versionchanged:: 0.4
       Ensure all errors returns a parseable body #366.

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
        abort(401, description='Please provide proper credentials')

    def authorized(self, allowed_roles, resource, method):
        """ Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        :param resource: resource being requested.
        """
        auth = request.headers.get('Authorization')
        try:
            userid, hmac_hash = auth.split(':')
            self.set_user_or_token(userid)
        except:
            auth = None
        return auth and self.check_auth(userid, hmac_hash, request.headers,
                                        request.get_data(), allowed_roles,
                                        resource, method)


class TokenAuth(BasicAuth):
    """ Implements Token AUTH logic. Should be subclassed to implement custom
    authentication checking.

    .. versionchanged:: 0.7
       Add support for get_user_or_token()/set_user_or_token(). This allows for
       easy retrieval of active user information. See #846.

    .. versionchanged:: 0.4
       Ensure all errors returns a parseable body #366.

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
        """ Returns a standard a 401. Override if you want to change the
        response.
        """
        resp = Response(None, 401, {'WWW-Authenticate': 'Basic realm="%s"' %
                                    __package__})
        abort(401, description='Please provide proper credentials',
              response=resp)

    def authorized(self, allowed_roles, resource, method):
        """ Validates the the current request is allowed to pass through.

        :param allowed_roles: allowed roles for the current request, can be a
                              string or a list of roles.
        :param resource: resource being requested.
        """
        auth = None
        if hasattr(request.authorization, 'username'):
            auth = request.authorization.username

        # Werkzeug parse_authorization does not handle
        # "Authorization: <token>" or
        # "Authorization: Token <token>" or
        # "Authorization: Bearer <token>"
        # headers, therefore they should be explicitly handled
        if not auth and request.headers.get('Authorization'):
            auth = request.headers.get('Authorization').strip()
            if auth.lower().startswith(('token', 'bearer')):
                auth = auth.split(' ')[1]

        if auth:
            self.set_user_or_token(auth)
        return auth and self.check_auth(auth, allowed_roles, resource,
                                        method)


def auth_field_and_value(resource):
    """ If auth is active and the resource requires it, return both the
    current request 'request_auth_value' and the 'auth_field' for the resource

    .. versionchanged:: 0.4
       Use new auth.request_auth_value() method.

    .. versionadded:: 0.3
    """
    if request.endpoint and '|resource' in request.endpoint:
        # We are on a resource endpoint and need to check against
        # `public_methods`
        public_method_list_to_check = 'public_methods'
    else:
        # We are on an item endpoint and need to check against
        # `public_item_methods`
        public_method_list_to_check = 'public_item_methods'

    resource_dict = app.config['DOMAIN'][resource]
    auth = resource_auth(resource)

    request_auth_value = auth.get_request_auth_value() if auth else None
    auth_field = resource_dict.get('auth_field', None) if request.method not \
        in resource_dict[public_method_list_to_check] else None

    return auth_field, request_auth_value


def resource_auth(resource):
    """ Ensure resource auth is an instance and its state is preserved between
    calls.

    .. versionchanged:: 0.6
       Change name so it can be clearly imported from other modules.

    .. versionadded:: 0.5.2
    """
    resource_def = app.config['DOMAIN'][resource]
    if callable(resource_def['authentication']):
        resource_def['authentication'] = resource_def['authentication']()
    return resource_def['authentication']
