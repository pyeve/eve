.. _auth:

Authentication and Authorization
================================
Introduction to Security
------------------------
Authentication is the mechanism whereby systems may securely identify their
users. Eve supports several authentication schemes: Basic Authentication, Token
Authentication, HMAC Authentication. `OAuth2 integration`_ is easily
accomplished.

Authorization is the mechanism by which a system determines what level of
access a particular (authenticated) user should have access to resources
controlled by the system. In Eve, you can restrict access to all API endpoints,
or only some of them. You can protect some HTTP verbs while leaving others
open. For example, you can allow public read-only access while leaving item
creation and edition restricted to authorized users only. You can also allow
``GET`` access for certain requests and ``POST`` access for others by checking
the method parameter. There is also support for role-based access control.

Security is one of those areas where customization is very important. This is
why you are provided with a handful of base authentication classes. They
implement the basic authentication mechanism and must be subclassed in order
to implement authorization logic. No matter which authentication scheme you
pick the only thing that you need to do in your subclass is override the
``check_auth()`` method.

Global Authentication
---------------------
To enable authentication for your API just pass the custom auth class on
app instantiation. In our example we're going to use the ``BasicAuth`` base
class, which implements the :ref:`basic` scheme:

.. code-block:: python

    from eve.auth import BasicAuth

    class MyBasicAuth(BasicAuth):
        def check_auth(self, username, password, allowed_roles, resource,
                       method):
            return username == 'admin' and password == 'secret'

    app = Eve(auth=MyBasicAuth)
    app.run()

All your API endpoints are now secured, which means that a client will need
to provide the correct credentials in order to consume the API:

.. code-block:: console

    $ curl -i http://example.com
    HTTP/1.1 401 UNAUTHORIZED
    Please provide proper credentials.

    $ curl -H "Authorization: Basic YWRtaW46c2VjcmV0" -i http://example.com
    HTTP/1.1 200 OK

By default access is restricted to all endpoints for all HTTP verbs
(methods), effectively locking down the whole API.

But what if your authorization logic is more complex, and you only want to
secure some endpoints or apply different logics depending on the
endpoint being consumed? You could get away with just adding logic to your
authentication class, maybe with something like this:

.. code-block:: python

    class MyBasicAuth(BasicAuth):
        def check_auth(self, username, password, allowed_roles, resource, method):
            if resource in ('zipcodes', 'countries'):
                # 'zipcodes' and 'countries' are public
                return True
            else:
                # all the other resources are secured
                return username == 'admin' and password == 'secret'

If needed, this approach also allows to take the request ``method`` into
consideration, for example to allow ``GET`` requests for everyone while forcing
validation on edits (``POST``, ``PUT``, ``PATCH``, ``DELETE``).

Endpoint-level Authentication
-----------------------------
The *one class to bind them all* approach seen above is probably good for most
use cases but as soon as authorization logic gets more complicated it could
easily lead to complex and unmanageable code, something you don't really want
to have when dealing with security.

Wouldn't it be nice if we could have specialized auth classes that we could
freely apply to selected endpoints? This way the global level auth class, the
one passed to the Eve constructor as seen above, would still be active on all
endpoints except those where different authorization logic is needed.
Alternatively, we could even choose to *not* provide a global auth class,
effectively making all endpoints public, except the ones we want protected.
With a system like this we could even choose to have some endpoints protected
with, say, Basic Authentication while others are secured with Token, or HMAC
Authentication!

Well, turns out this is actually possible by simply enabling the
resource-level ``authentication`` setting when we are defining the API
:ref:`domain <domain>`.

.. code-block:: python

    DOMAIN = {
        'people': {
            'authentication': MySuperCoolAuth,
            ...
            },
        'invoices': ...
        }

And that's it. The `people` endpoint will now be using the ``MySuperCoolAuth``
class for authentication, while the ``invoices`` endpoint  will be using the
general-purpose auth class if provided or else it will just be open to the
public.

There are other features and options that you can use to reduce complexity in
your auth classes, especially (but not only) when using the global level
authentication system. Lets review them.

Global Endpoint Security
------------------------
You might want a public read-only API where only authorized users can write,
edit and delete. You can achieve that by using the ``PUBLIC_METHODS`` and
``PUBLIC_ITEM_METHODS`` :ref:`global settings <global>`. Add the following to
your `settings.py`:

::

    PUBLIC_METHODS = ['GET']
    PUBLIC_ITEM_METHODS = ['GET']

And run your API. POST, PATCH and DELETE are still restricted, while GET is
publicly available at all API endpoints. ``PUBLIC_METHODS`` refers to resource
endpoints, like ``/people``, while ``PUBLIC_ITEM_METHODS`` refers to individual
items like ``/people/id``.

.. _endpointsec:

Custom Endpoint Security
------------------------
Suppose that you want to allow public read access to only certain resources.
You do that by declaring public methods at resource level, while declaring the
API :ref:`domain <domain>`:

.. code-block:: python

    DOMAIN = {
        'people': {
            'public_methods': ['GET'],
            'public_item_methods': ['GET'],
            },
        }

Be aware that, when present, :ref:`resource settings <local>` override global
settings. You can use this to your advantage. Suppose that you want to grant
read access to all endpoints with the only exception of ``/invoices``.  You
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
Encoding passwords with bcrypt_ is a great idea. It comes at the cost of
performance, but that's precisely the point, as slow encoding means very good
resistance to brute-force attacks. For a faster (and less safe) alternative, see
the SHA1/MAC snippet further below.

This script assumes that user accounts are stored in an `accounts` MongoDB
collection, and that passwords are stored as bcrypt hashes. All API
resources/methods will be secured unless they are made explicitly public.


.. admonition:: Please note

    You will need to install `py-bcrypt` for this to work.

.. code-block:: python


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
    from flask import current_app as app

    class BCryptAuth(BasicAuth):
        def check_auth(self, username, password, allowed_roles, resource, method):
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

.. code-block:: python

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
    from flask import current_app as app

    class Sha1Auth(BasicAuth):
        def check_auth(self, username, password, allowed_roles, resource, method):
            # use Eve's own db driver; no additional connections/resources are used
            accounts = app.data.driver.db['accounts']
            account = accounts.find_one({'username': username})
            return account and \
                check_password_hash(account['password'], password)


    if __name__ == '__main__':
        app = Eve(auth=Sha1Auth)
        app.run()

.. _token:

Token-Based Authentication
--------------------------
Token-based authentication can be considered a specialized version of Basic
Authentication. The Authorization header tag will contain the auth token as the
username, and no password.

This script assumes that user accounts are stored in an `accounts` MongoDB
collection. All API resources/methods will be secured unless they are made
explicitly public (by fiddling with some settings you can open one or more
resources and/or methods to public access -see docs).

.. code-block:: python

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
    from flask import current_app as app

    class TokenAuth(TokenAuth):
        def check_auth(self, token, allowed_roles, resource, method):
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

How HMAC Authentication Works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The server provides the client with a user id and a secret key through some
out-of-band technique (e.g., the service sends the client an e-mail
containing the user id and secret key). The client will use the supplied
secret key to sign all requests.

When the client wants to send a request, he builds the complete request and
then, using the secret key, computes a hash over the complete message body (and
optionally some of the message headers if required)

Next, the client adds the computed hash and his userid to the message in the
Authorization header:

::

    Authorization: johndoe:uCMfSzkjue+HSDygYB5aEg==

and sends it to the service. The service retrieves the userid from the
message header and searches the private key for that user in its own
database. Next it computes the hash over the message body (and selected
headers) using the key to generate its hash. If the hash the client sends
matches the hash the server computes, then the server knows the message was
sent by the real client and was not altered in any way.

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

.. code-block:: python

    from eve import Eve
    from eve.auth import HMACAuth
    from flask import current_app as app
    from hashlib import sha1
    import hmac


    class HMACAuth(HMACAuth):
        def check_auth(self, userid, hmac_hash, headers, data, allowed_roles,
                       resource, method):
            # use Eve's own db driver; no additional connections/resources are
            # used
            accounts = app.data.driver.db['accounts']
            user = accounts.find_one({'userid': userid})
            if user:
                secret_key = user['secret_key']
            # in this implementation we only hash request data, ignoring the
            # headers.
            return user and \
                hmac.new(str(secret_key), str(data), sha1).hexdigest() == \
                    hmac_hash


    if __name__ == '__main__':
        app = Eve(auth=HMACAuth)
        app.run()

.. _roleaccess:

Role Based Access Control
-------------------------
The code snippets above deliberately ignore the ``allowed_roles`` parameter.
You can use this parameter to restrict access to authenticated users who also
have been assigned specific roles.

First, you would use the new ``ALLOWED_ROLES`` and ``ALLOWED_ITEM_ROLES`` :ref:`global
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

.. code-block:: python

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
    from flask import current_app as app

    class RolesAuth(BasicAuth):
        def check_auth(self, username, password, allowed_roles, resource, method):
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

.. _user-restricted:

User-Restricted Resource Access
-------------------------------
When this feature is enabled, each stored document is associated with the
account that created it. This allows the API to transparently serve only
account-created documents on all kinds of requests: read, edit, delete and of
course create.  User authentication needs to be enabled for this to work
properly.

At the global level this feature is enabled by setting ``AUTH_FIELD`` and locally
(at the endpoint level) by setting ``auth_field``. These properties define the name
of the field used to store the id of the user who created the document.  So for
example by setting ``AUTH_FIELD`` to ``user_id``, you are effectively (and
transparently to the user) adding a ``user_id`` field to every stored
document. This will then be used to retrieve/edit/delete documents stored by
the user.

But how do you set the ``auth_field`` value? By invoking the
``set_request_auth_value()`` class method. Let us revise our
BCrypt-authentication example from above:

.. code-block:: python
   :emphasize-lines: 25-28

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
        def check_auth(self, username, password, allowed_roles, resource, method):
            # use Eve's own db driver; no additional connections/resources are used
            accounts = app.data.driver.db['accounts']
            account = accounts.find_one({'username': username})
            # set 'auth_field' value to the account's ObjectId
            # (instead of _id, you might want to use ID_FIELD)
            if account and '_id' in account:
                self.set_request_auth_value(account['_id'])
            return account and \
                bcrypt.hashpw(password, account['password']) == account['password']


    if __name__ == '__main__':
        app = Eve(auth=BCryptAuth)
        app.run()

.. _authdrivendb:

Auth-driven Database Access
---------------------------
Custom authentication classes can also set the database that should be used
when serving the active request.

Normally you either use a single database for the whole API or you configure
which database each endpoint consumes by setting ``mongo_prefix`` to the
desired value (see :ref:`local`).

However, you might opt to select the target database based on the active token,
user or client. This is handy if your use-case includes user-dedicated database
instances. All you have to do is set invoke the ``set_mongo_prefix()`` method
when authenticating the request.

A trivial example would be:

.. code-block:: python

    from eve.auth import BasicAuth

    class MyBasicAuth(BasicAuth):
        def check_auth(self, username, password, allowed_roles, resource, method):
            if username == 'user1':
                self.set_mongo_prefix('MONGO1')
            elif username == 'user2':
                self.set_mongo_prefix('MONGO2')
            else:
                # serve all other users from the default db.
                self.set_mongo_prefix(None)
            return username is not None and password == 'secret'

    app = Eve(auth=MyBasicAuth)
    app.run()

The above class will serve ``user1`` with data coming from the database which
configuration settings are prefixed by ``MONGO1`` in ``settings.py``. Same
happens with ``user2`` and ``MONGO2`` while all other users are served with
the default database.

Since values set by ``set_mongo_prefix()`` have precedence over both default
and endpoint-level ``mongo_prefix`` settings, what happens here is that the two
users will always be served from their reserved databases, no matter the
eventual database configuration for the endpoint.

OAuth2 Integration
------------------
Since you have total control over the Authorization process, integrating
OAuth2 with Eve is easy. Make yourself comfortable with the topics illustrated
in this page, then head over to `Eve-OAuth2`_, an example project which
leverages `Flask-Sentinel`_ to demonstrate how you can protect your API with
OAuth2.

.. admonition:: Please note

    The snippets in this page can also be found in the `examples/security`
    folder of the Eve `repository`_.

.. _`repository`: https://github.com/pyeve/eve
.. _bcrypt: http://en.wikipedia.org/wiki/Bcrypt
.. _`Eve-OAuth2`: https://github.com/pyeve/eve-oauth2
.. _`Flask-Sentinel`: https://github.com/pyeve/flask-sentinel
