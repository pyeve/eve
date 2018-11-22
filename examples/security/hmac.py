# -*- coding: utf-8 -*-

"""
    Auth-HMAC
    ~~~~~~~~~

    Securing an Eve-powered API with HMAC based Authentication.

    The ``eve.auth.HMACAuth`` class allows for custom Amazon S3-like
    authentication, which is basically a very secure custom authentication
    scheme built around the `Authorization` header.

    The server provides the client with a user id and a secret key through some
    out-of-band technique (e.g., the service sends the client an e-mail
    containing the user id and secret key). The client will use the supplied
    secret key to sign all requests.

    When the client wants to send a request he builds the complete request and
    then using the secret key computes a hash over the complete message body
    (and optionally some of the message headers if required)

    Next the client add the computed hash and his userid to the message in the
    Authorization header:

        Authorization: johndoe:uCMfSzkjue+HSDygYB5aEg==

    and sends it to the service. The service retrieves the userid from the
    message header and searches the private key for that user in its own
    database. Next he computes the hash over the message body (and selected
    headers) using the key to generate its hash. If the hash the client sends
    matches the hash the server computes the server knows the message was send
    by the real client and was not altered in any way.

    Really the only tricky part is sharing a secret key with the user and
    keeping that secure. That is why some services allow for generation of
    shared keys with a limited life time so you can give the key to a third
    party to temporarily work on your behalf. This is also the reason why the
    secret key is generally provided through out-of-band channels (often
    a webpage or, as said above, an email or plain old paper).

    The HMACAuth class also supports access roles.

    Checkout Eve at https://github.com/pyeve/eve

    This snippet by Nicola Iarocci can be used freely for anything you like.
    Consider it public domain.
"""
import hmac

from eve import Eve
from eve.auth import HMACAuth
from hashlib import sha1

from settings_security import SETTINGS


class HMACAuth(HMACAuth):
    def check_auth(
        self, userid, hmac_hash, headers, data, allowed_roles, resource, method
    ):
        # use Eve's own db driver; no additional connections/resources are used
        accounts = app.data.driver.db["accounts"]
        user = accounts.find_one({"userid": userid})
        if user:
            secret_key = user["secret_key"]
        # in this implementation we only hash request data, ignoring the
        # headers.
        return (
            user and hmac.new(str(secret_key), str(data), sha1).hexdigest() == hmac_hash
        )


if __name__ == "__main__":
    app = Eve(auth=HMACAuth, settings=SETTINGS)
    app.run()
