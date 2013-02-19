# -*- coding: utf-8 -*-

"""
    Auth-SHA1/HMAC
    ~~~~~~~~~~~~~~

    Securing an Eve-powered API with Basic Authentication (RFC2617).

    This script assumes that user accounts are stored in a MongoDB collection
    ('accounts'), and that passwords are stored as SHA1/HMAC hashes. All API
    resources/methods will be secured unless they are made explicitly public
    (you can open to public access one or more resources and/or methods by
    toggling some API settings - see docs).

    Since we are using werkzeug we don't need any extra import (werkzeug being
    one of Flask/Eve prerequisites).

    Checkout Eve at https://github.com/nicolaiarocci/eve

    This snippet by Nicola Iarocci can be used freely for anything you like.
    Consider it public domain.
"""

from eve import Eve
from eve.auth import BasicAuth
from werkzeug.security import check_password_hash


class Sha1Auth(BasicAuth):
    def check_auth(self, username, password):
        # use Eve's own db driver; no additional connections/resources are used
        accounts = app.data.driver.db['accounts']
        account = accounts.find_one({'username': username})
        return account and \
            check_password_hash(account['password'], password)


if __name__ == '__main__':
    app = Eve(auth=Sha1Auth)
    app.run()
