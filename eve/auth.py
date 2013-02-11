from flask import request, Response


class BasicAuth(object):
    def check_auth(self, username, password):
        """ This function is called to check if a username / password
        combination is valid. Must be overridden with custom logic.
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
