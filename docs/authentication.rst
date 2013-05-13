.. _auth:

Authentication
==============
You can restrict access to all API endpoints, or only some of them. You can
protect some HTTP verbs while leaving others open. For example, you could allow
public read-only access while leaving item creation and edition restricted to
authorized users only. There is also support for role-based access control

Authentication is one of those areas where customization is very important.
This is why you are provided with a handful of base authorization classes. They
should be subclassed in order to implement custom logic. As you will see in the
code snippets below, no matter which authentication scheme you pick, the only
thing that you need to do is override the ``check_auth()`` method. When you
instantiate the Eve app, you pass your custom class, like this:

::

    from eve.auth import BasicAuth

    class MyBasicAuth(BasicAuth):
        def check_auth(self, username, password, allowed_roles):
            return username == 'admin' and password == 'secret'

    app = Eve(auth=MyBasicAuth)
    app.run()

All your API endpoints are now secured which means that a client will need
to provide the correct credentials in order to consume the API:

.. code-block:: console

    $ curl -i http://example.com/
    HTTP/1.0 401 UNAUTHORIZED
    WWW-Authenticate: Basic realm:"eve"
    Content-Type: text/html; charset=utf-8
    Content-Length: 33
    Server: Eve/0.0.4 Werkzeug/0.8.3 Python/2.7.3
    Date: Thu, 14 Feb 2013 14:21:11 GMT

    Please provide proper credentials.

    $ curl -H "Authorization: Basic YWRtaW46c2VjcmV0" -i http://example.com/
    HTTP/1.0 200 OK
    Content-Type: application/json
    Content-Length: 194
    Server: Eve/0.0.4 Werkzeug/0.8.3 Python/2.7.3
    Date: Thu, 14 Feb 2013 14:23:39 GMT

By default, access is restricted to *all* endpoints, for *all* HTTP verbs
(methods), effectively locking down the whole API.

Fine-Tuning Global Security 
---------------------------
You might want a public read-only API where only authorized users can write,
edit and delete. You can achieve that by using the ``PUBLIC_METHODS`` and
``PUBLIC_ITEM_METHODS`` :ref:`global settings <global>`. Add the following to
your `settings.py`:

::

    PUBLIC_METHODS = ['GET'] 
    PUBLIC_ITEM_METHODS = ['GET']

And run your API. POST, PATCH and DELETE are still restricted while GET is
publicly available at all API endpoints. ``PUBLIC_METHODS`` refers to resource
endpoints, like ``/people/``, while ``PUBLIC_ITEM_METHODS`` refers to individual
items like ``/people/id/``.

Fine-Tuning Endpoint Security
-----------------------------
Suppose that you want to allow public read access to only certain resources.
You do that by declaring public methods at resource level, while declaring the
API :ref:`domain <domain>`:

::

    DOMAIN = {
        'people': {
            'public_methods': ['GET'],
            'public_item_methods': ['GET'],
            },
        }

Be aware that, when present, :ref:`resource settings <local>` override global
settings. You can use this at your advantage. Suppose that you want to grant
read access to all endpoints with the only exception of ``/invoices/``.  You
first open read access for all endpoints:

::

    PUBLIC_METHODS = ['GET'] 
    PUBLIC_ITEM_METHODS = ['GET']

Then you protect the private endpoint:

::

    DOMAIN = {
        'invoices': {
            'public_methods': [],
            'public_item_methods': [],
            }
        }

Effectively making `invoices` a restricted resource.

.. _basic:

Basic Authentication
--------------------
The ``eve.auth.BasicAuth`` class allows the implementation of Basic
Authentication (RFC2617). It should be subclassed in order to implement custom
authentication.

Basic Authentication with bcrypt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Encoding password with bcrypt_ is a great idea. It comes at the cost of
performance, but that's precisely the point, as slow encoding means very good
resistance to brute-force attacks. For a faster (and less safe) alternative see
the SHA1/MAC snippet further below. 

This script assumes that user accounts are stored in an `accounts` MongoDB
collection, and that passwords are stored as bcrypt hashes. All API
resources/methods will be secured unless they are made explicitly public.


.. admonition:: Please note

    You will need to install `py-bcript` for this to work.

::


    # -*- coding: utf-8 -*-

    """
        Auth-BCrypt
        ~~~~~~~~~~~

        Securing an Eve-powered API with Basic Authentication (RFC2617).

        You will need to install py-bcrypt: ``pip install py-bcrypt``

        This snippet by Nicola Iarocci can be used freely for anything you like.
        Consider it public domain.
    """

    import bcrypt
    from eve import Eve
    from eve.auth import BasicAuth


    class BCryptAuth(BasicAuth):
        def check_auth(self, username, password, allowed_roles):
            # use Eve's own db driver; no additional connections/resources are used
            accounts = app.data.driver.db['accounts']
            account = accounts.find_one({'username': username})
            return account and \
                bcrypt.hashpw(password, account['password']) == account['password']


    if __name__ == '__main__':
        app = Eve(auth=BCryptAuth)
        app.run()

Basic Authentication with SHA1/HMAC
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This script assumes that user accounts are stored in an `accounts` MongoDB
collection, and that passwords are stored as SHA1/HMAC hashes. All API
resources/methods will be secured unless they are made explicitly public.

::

    # -*- coding: utf-8 -*-

    """
        Auth-SHA1/HMAC
        ~~~~~~~~~~~~~~

        Securing an Eve-powered API with Basic Authentication (RFC2617).

        Since we are using werkzeug we don't need any extra import (werkzeug being
        one of Flask/Eve prerequisites).

        This snippet by Nicola Iarocci can be used freely for anything you like.
        Consider it public domain.
    """

    from eve import Eve
    from eve.auth import BasicAuth
    from werkzeug.security import check_password_hash


    class Sha1Auth(BasicAuth):
        def check_auth(self, username, password, allowed_roles):
            # use Eve's own db driver; no additional connections/resources are used
            accounts = app.data.driver.db['accounts']
            account = accounts.find_one({'username': username})
            return account and \
                check_password_hash(account['password'], password)


    if __name__ == '__main__':
        app = Eve(auth=Sha1Auth)
        app.run()

Token-Based Authentication
--------------------------
Token based authentication can be considered a specialized version of Basic
Authentication. The Authorization header tag will contain the auth token.

This script assumes that user accounts are stored in an `accounts` MongoDB
collection. All API resources/methods will be secured unless they are made
explicitly public (by fiddling with some settings you can open one or more
resources and/or methods to public access -see docs).

::

    # -*- coding: utf-8 -*-

    """
        Auth-Token
        ~~~~~~~~~~

        Securing an Eve-powered API with Token based Authentication.

        This snippet by Nicola Iarocci can be used freely for anything you like.
        Consider it public domain.
    """

    from eve import Eve
    from eve.auth import TokenAuth


    class TokenAuth(TokenAuth):
        def check_auth(self, token, allowed_roles):
            """For the purpose of this example the implementation is as simple as
            possible. A 'real' token should probably contain a hash of the
            username/password combo, which sould then validated against the account
            data stored on the DB.
            """
            # use Eve's own db driver; no additional connections/resources are used
            accounts = app.data.driver.db['accounts']
            return accounts.find_one({'token': token})


    if __name__ == '__main__':
        app = Eve(auth=TokenAuth)
        app.run()

HMAC Authentication
-------------------
The ``eve.auth.HMACAuth`` class allows for custom, Amazon S3-like, HMAC (Hash
Message Authentication Code) authentication, which is basically a very secure
custom authentication scheme built around the `Authorization` header.
  
How HMAC Authenticaton Works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The server provides the client with a user id and a secret key through some
out-of-band technique (e.g., the service sends the client an e-mail
containing the user id and secret key). The client will use the supplied
secret key to sign all requests.

When the client wants to send a request he builds the complete request and
then using the secret key computes a hash over the complete message body (and
optionally some of the message headers if required) 

Next the client add the computed hash and his userid to the message in the
Authorization header:

::

    Authorization: johndoe:uCMfSzkjue+HSDygYB5aEg==

and sends it to the service. The service retrieves the userid from the
message header and searches the private key for that user in its own
database. Next he computes the hash over the message body (and selected
headers) using the key to generate its hash. If the hash the client sends
matches the hash the server computes the server knows the message was send by
the real client and was not altered in any way.  

Really the only tricky part is sharing a secret key with the user and keeping
that secure. That is why some services allow for generation of shared keys
with a limited life time so you can give the key to a third party to
temporarily work on your behalf. This is also the reason why the secret key
is generally provided through out-of-band channels (often a webpage or, as
said above, an email or plain old paper).

The ``eve.auth.HMACAuth``  class also support access roles. 

HMAC Example
~~~~~~~~~~~~
The snippet below can also be found in the `examples/security` folder of the
Eve `repository`_.

::

    from eve import Eve
    from eve.auth import HMACAuth
    from hashlib import sha1
    import hmac


    class HMACAuth(HMACAuth):
        def check_auth(self, userid, hmac_hash, headers, data, allowed_roles):
            # use Eve's own db driver; no additional connections/resources are used
            accounts = app.data.driver.db['accounts']
            user = accounts.find_one({'userid': userid})
            if user:
                secret_key = user['secret_key']
            # in this implementation we only hash request data, ignoring the
            # headers.
            return user and \
                hmac.new(secret_key, data, sha1).hexdigest() == hmac_hash


    if __name__ == '__main__':
        app = Eve(auth=HMACAuth)
        app.run()

Role Based Access Control
-------------------------
The code snippets above deliberately ignore the ``allowed_roles`` parameter.
You can use this parameter to restrict access to authenticated users who also
have been assigned specific roles. 

First you would use the new ``ALLOWED_ROLES`` and ``ALLOWED_ITEM_ROLES`` :ref:`global
settings <global>` (or the corresponding ``allowed_roles`` and ``allowed_item_roles``
:ref:`resource settings <local>`).

::

    ALLOWED_ROLES = ['admin']

Then your subclass would implement the authorization logic by making good use
of the aforementioned ``allowed_roles`` parameter. 

The snippet below assumes that user accounts are stored in an `accounts`
MongoDB collection, that passwords are stored as SHA1/HMAC hashes and that user
roles are stored in a 'roles' array. All API resources/methods will be secured
unless they are made explicitly public.

::

    # -*- coding: utf-8 -*-

    """
        Auth-SHA1/HMAC-Roles
        ~~~~~~~~~~~~~~~~~~~~

        Securing an Eve-powered API with Basic Authentication (RFC2617) and user
        roles.

        Since we are using werkzeug we don't need any extra import (werkzeug being
        one of Flask/Eve prerequisites).

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
  
User-Restricted Resource Access
-------------------------------
When enabled, authorized users can only read/update/delete items created by
themselves. Can be switched on and off at global level via the
``AUTH_USERFIELD_NAME`` keyword, or at resource endpoints with the
``auth_userfield_name`` keyword (the latter will override the former). The
keyword contains the actual name of the field used to store the username of the
user who created the resource item. Defaults to ``''``, which disables the
feature.

.. admonition:: Please note

    The snippets in this page can also be found in the `examples/security`
    folder of the Eve `repository`_.

.. _`repository`: https://github.com/nicolaiarocci/eve
.. _bcrypt: http://en.wikipedia.org/wiki/Bcrypt
