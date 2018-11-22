# -*- coding: utf-8 -*-

"""
    Auth-Token
    ~~~~~~~~~~

    Securing an Eve-powered API with Token based Authentication.

    Token based authentication can be considered a specialized version of Basic
    Authentication. The Authorization header tag will contain the auth token.

    This script assumes that user accounts are stored in a MongoDB collection
    ('accounts'). All API resources/methods will be secured unless they are
    made explicitly public (by fiddling with some settings you can open one or
    more resources and/or methods to public access -see docs).

    Checkout Eve at https://github.com/pyeve/eve

    This snippet by Nicola Iarocci can be used freely for anything you like.
    Consider it public domain.
"""

from eve import Eve
from eve.auth import TokenAuth

from settings_security import SETTINGS


class TokenAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        """For the purpose of this example the implementation is as simple as
        possible. A 'real' token should probably contain a hash of the
        username/password combo, which should be then validated against the
        account data stored on the DB.
        """
        # use Eve's own db driver; no additional connections/resources are used
        accounts = app.data.driver.db["accounts"]
        return accounts.find_one({"token": token})


if __name__ == "__main__":
    app = Eve(auth=TokenAuth, settings=SETTINGS)
    app.run()
