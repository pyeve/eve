# -*- coding: utf-8 -*-

SETTINGS = {
    "DEBUG": True,
    "MONGO_HOST": "localhost",
    "MONGO_PORT": 27017,
    "MONGO_DBNAME": "test_db",
    "DOMAIN": {
        "accounts": {
            "username": {"type": "string", "minlength": 5, "maxlength": 20},
            "password": {"type": "string", "minlength": 5, "maxlength": 20},
            "secret_key": {"type": "string", "minlength": 5, "maxlength": 20},
            "roles": {"type": "string", "minlength": 10, "maxlength": 50},
            "token": {"type": "string", "minlength": 10, "maxlength": 50},
        }
    },
}
