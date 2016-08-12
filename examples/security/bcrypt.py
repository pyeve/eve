# -*- coding: utf-8 -*-

"""
    Auth-BCrypt
    ~~~~~~~~~~~

    Securing an Eve-powered API with Basic Authentication (RFC2617).

    This script assumes that user accounts are stored in a MongoDB collection
    ('accounts'), and that passwords are stored as BCrypt hashes. All API
    resources/methods will be secured unless they are made explicitly public
    (by fiddling with some settings you can open one or more resources and/or
    methods to public access -see docs).

    You will need to install py-bcrypt: ``pip install py-bcrypt``

    Eve @ https://github.com/nicolaiarocci/eve

    This snippet by Nicola Iarocci can be used freely for anything you like.
    Consider it public domain.
"""

import bcrypt
from eve import Eve
from eve.auth import BasicAuth
from settings_security import SETTINGS


class BCryptAuth(BasicAuth):
    def check_auth(self, username, password, allowed_roles, resource, method):
        # use Eve's own db driver; no additional connections/resources are used
        accounts = app.data.driver.db['accounts']
        account = accounts.find_one({'username': username})
        return account and \
            bcrypt.hashpw(password, account['password']) == account['password']


if __name__ == '__main__':
    app = Eve(auth=BCryptAuth, settings=SETTINGS)
    app.run()
