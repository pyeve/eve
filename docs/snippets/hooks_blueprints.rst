Using Eve Event Hooks from your Blueprint
=========================================
by Pau Freixes

The use of Flask Blueprints_ helps us to extend our Eve applications with new
endpoints that do not fit as a typical Eve resource. Pulling these endpoints
out of the Eve scope allows us to write specific code in order to handle
specific situations.

In the context of a Blueprint we could expect Eve features not be available,
but often that is not the case. We can continue to use a bunch of features,
such as :ref:`eventhooks`.

Next snippet displays how the ``users`` module has a blueprint which performs
some custom actions and then uses the ``users_deleted`` signal to notify and
invoke all callback functions which are registered to the Eve application.

.. code-block:: python

    from flask import Blueprint, current_app as app

    blueprint = Blueprint('prefix_uri', __name__)

    @blueprint.route('/users/<username>', methods=['DELETE'])
    def del_user(username):
        # some specific code goes here
        # ...

        # call Eve-hooks consumers for this  event
        getattr(app, "users_deleted")(username)

Next snippet displays how the blueprint is binded over our main Eve application
and how the specific ``set_username_as_none`` function is registered to be
called each time an user is deleted using the Eve events, to update the
properly MongoDB collection.

.. code-block:: python

    from eve import Eve
    from users import blueprint
    from flask import current_app, request

    def set_username_as_none(username):
        resource = request.endpoint.split('|')[0]
        return  current_app.data.driver.db[resource].update(
            {"user" : username},
            {"$set": {"user": None}},
            multi=True
        )

    app = Eve()
    # register the blueprint to the main Eve application
    app.register_blueprint(blueprint)
    # bind the callback function so it is invoked at each user deletion
    app.users_deleted += set_username_as_none
    app.run()

.. _Blueprints: http://flask.pocoo.org/docs/blueprints/
.. _`eve event-hooks`: http://python-eve.org/features.html#event-hooks
