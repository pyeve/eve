Supporting both list-level and item-level CRUD operations
=========================================================
by John Chang

This is an example of how to implement a simple list of items that supports both list-level and item-level CRUD operations.

Specifically, it should be possible to use a single GET to get the entire list (including all items) but also a single POST to append an item (rather than PATCHing the list).

The solution was to database event hooks to inject the embedded child documents (``items``) into the parent list before it's returned to the client and also delete the child items when the parent list is deleted. This works, although it results in two DB queries.

main.py
-------
.. code-block:: python

    from eve import Eve
    from bson.objectid import ObjectId

    app = Eve()
    mongo = app.data.driver


    def after_fetching_lists(response):
        list_id = response['_id']
        f = {'list_id': ObjectId(list_id)}
        response['items'] = list(mongo.db.items.find(f))


    def after_deleting_lists(item):
        list_id = item['_id']
        f = {'list_id': ObjectId(list_id)}
        mongo.db.items.delete_many(f)

    app.on_fetched_item_lists += after_fetching_lists
    app.on_deleted_item_lists += after_deleting_lists

    app.run()

settings.py
-----------
.. code-block:: python

    import os

    DEBUG = True

    MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
    MONGO_PORT = os.environ.get('MONGO_PORT', 27017)
    MONGO_USERNAME = os.environ.get('MONGO_USERNAME', 'user')
    MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD', 'user')
    MONGO_DBNAME = os.environ.get('MONGO_DBNAME', 'listtest')

    RESOURCE_METHODS = ['GET', 'POST', 'DELETE']
    ITEM_METHODS = ['GET', 'PUT', 'PATCH', 'DELETE']

    DOMAIN = {
        'lists': {
            'schema': {
                'title': {
                    'type': 'string'
                }
            }
        },
        'items': {
            'url': 'lists/<regex("[a-f0-9]{24}"):list_id>/items',
            'schema': {
                'list_id': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'lists',
                        'field': '_id'
                    }
                },
                'name': {
                    'type': 'string',
                    'required': True
                }
            }
        }
    }

Usage
-----
.. code-block:: bash

    $ curl -i -X POST http://127.0.0.1:5000/lists -d title="My List"
    HTTP/1.0 201 CREATED

    {
        "_id": "58960f83a663e2e6746dfa6a",
        :
    }

    $ curl -i -X POST http://127.0.0.1:5000/lists/58960f83a663e2e6746dfa6a/items -d 'name=Alice'
    HTTP/1.0 201 CREATED

    $ curl -i -X POST http://127.0.0.1:5000/lists/58960f83a663e2e6746dfa6a/items -d 'name=Bob'
    HTTP/1.0 201 CREATED

    $ curl -i -X GET http://127.0.0.1:5000/lists/58960f83a663e2e6746dfa6a
    HTTP/1.0 200 OK

    {
        "_created": "Sat, 04 Feb 2017 17:29:39 GMT",
        "_etag": "01799f6be25a044ab95cfeb2dc0f834d11b796d8",
        "_id": "58960f83a663e2e6746dfa6a",
        "_updated": "Sat, 04 Feb 2017 17:29:39 GMT",
        "items": [
            {
                "_created": "Sat, 04 Feb 2017 17:30:06 GMT",
                "_etag": "72ad9248ad5bf45c7bfe3e03a1b9bc384d94572f",
                "_id": "58960f9ea663e2e6746dfa6b",
                "_updated": "Sat, 04 Feb 2017 17:30:06 GMT",
                "list_id": "58960f83a663e2e6746dfa6a",
                "name": "Alice",
                "quantity": 1
            },
            {
                "_created": "Sat, 04 Feb 2017 17:30:13 GMT",
                "_etag": "447f51b057fb5e0a70472e96ff883c64b5e2e308",
                "_id": "58960fa5a663e2e6746dfa6c",
                "_updated": "Sat, 04 Feb 2017 17:30:13 GMT",
                "list_id": "58960f83a663e2e6746dfa6a",
                "name": "Bob",
                "quantity": 1
            }
        ],
        "title": "My List"
    }

    $ curl -i -X DELETE http://127.0.0.1:5000/lists/58960f83a663e2e6746dfa6a/items/58960f9ea663e2e6746dfa6b -H "If-Match: 72ad9248ad5bf45c7bfe3e03a1b9bc384d94572f"
    HTTP/1.0 204 NO CONTENT

    $ curl -i -X GET http://127.0.0.1:5000/lists/58960f83a663e2e6746dfa6a
    HTTP/1.0 200 OK

    {
        "_created": "Sat, 04 Feb 2017 17:29:39 GMT",
        "_etag": "01799f6be25a044ab95cfeb2dc0f834d11b796d8",
        "_id": "58960f83a663e2e6746dfa6a",
        "_updated": "Sat, 04 Feb 2017 17:29:39 GMT",
        "items": [
            {
                "_created": "Sat, 04 Feb 2017 17:30:13 GMT",
                "_etag": "447f51b057fb5e0a70472e96ff883c64b5e2e308",
                "_id": "58960fa5a663e2e6746dfa6c",
                "_updated": "Sat, 04 Feb 2017 17:30:13 GMT",
                "list_id": "58960f83a663e2e6746dfa6a",
                "name": "Bob",
                "quantity": 1
            }
        ],
        "title": "My List"
    }
