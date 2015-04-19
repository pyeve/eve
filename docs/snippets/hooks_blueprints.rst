Using the Eve hooks from your blueprints
========================================
by Pau Freixes

The use of blueprints_ helps us to extend our Eve applications with new endpoints,
that do not fit as a typical Eve resource. Pulling these endpoints out of the Eve
scope allows us to write specific code in order to handle specific situations.

In this scenario we could think that almost all of the Eve features can not be used.
However, we can continue using a bunch of these features, such as the Eve `events hooks`_.

Next snippet displays how the `users` blueprint uses the `users_deleted` signal to notify
and run the specific code subscribed by the consumers.

.. code-block:: python

    from flask import Blueprint, current_app as app

    blueprint = Blueprint('prefix_uri', __name__)

    @blueprint.route('/users/<username>', methods=['DELETE'])
    def del_user(username):
        # some specific code goes here
        # call all Eve-hooks consumers for this  event
        getattr(app, "users_deleted")(username)

Next snippet displays how the blueprint is binded over our main Eve application and
how the specific `set_username_as_none` function is registered to be called each time that 
an user is deleted using the Eve events to update the properly Mongodb collection.

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
    app.register_blueprint(blueprint)
    app.users_deleted += set_username_as_none
    app.run()

.. _`blueprints`: http://flask.pocoo.org/docs/blueprints/
.. _`eve event-hooks`: http://python-eve.org/features.html#event-hooks
