# -*- coding: utf-8 -*-

"""
    Auth-SHA1/HMAC-Roles
    ~~~~~~~~~~~~~~~~~~~~

    Securing an Eve-powered API with Basic Authentication (RFC2617) and user
    roles.

    This script assumes that user accounts are stored in an 'accounts' MongoDB
    collection, that passwords are stored as SHA1/HMAC hashes and that user
    roles are stored in a 'roles' array. All API resources/methods will be
    secured unless they are made explicitly public (by fiddling with some
    settings you can open one or more resources and/or methods to public access
    -see docs).

    Since we are using werkzeug we don't need any extra import (werkzeug being
    one of Flask/Eve prerequisites).

    Checkout Eve at https://github.com/nicolaiarocci/eve

    This snippet by Nicola Iarocci can be used freely for anything you like.
    Consider it public domain.
"""

from eve import Eve
from eve.auth import BasicAuth
from werkzeug.security import check_password_hash


class RolesAuth(BasicAuth):
    def check_auth(self, username, password, allowed_roles):
        # use Eve's own db driver; no additional connections/resources are used
        accounts = app.data.driver.db['accounts']
        lookup = {'username': username}
        if allowed_roles:
            # only retrieve a user if his roles match ``allowed_roles``
            lookup['roles'] = {'$in': allowed_roles}
        account = accounts.find_one(lookup)
        return account and check_password_hash(account['password'], password)


if __name__ == '__main__':
    app = Eve(auth=RolesAuth)
    app.run()
