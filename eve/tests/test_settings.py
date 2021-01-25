# -*- coding: utf-8 -*-
import copy


MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_USERNAME = MONGO1_USERNAME = "test_user"
MONGO_PASSWORD = MONGO1_PASSWORD = "test_pw"
MONGO_DBNAME, MONGO1_DBNAME = "eve_test", "eve_test1"
ID_FIELD = "_id"

RESOURCE_METHODS = ["GET", "POST", "DELETE"]
ITEM_METHODS = ["GET", "PATCH", "DELETE", "PUT"]
ITEM_CACHE_CONTROL = ""
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD


disabled_bulk = {
    "url": "somebulkurl",
    "item_title": "bulkdisabled",
    "bulk_enabled": False,
    "schema": {"string_field": {"type": "string"}},
}


contacts = {
    "url": "arbitraryurl",
    "cache_control": "max-age=20,must-revalidate",
    "cache_expires": 20,
    "item_title": "contact",
    "additional_lookup": {
        "url": r'regex("[\w]+")',  # to be unique field
        "field": "ref",
    },
    "datasource": {"filter": {"username": {"$exists": False}}},
    "schema": {
        "ref": {
            "type": "string",
            "minlength": 25,
            "maxlength": 25,
            "required": True,
            "unique": True,
        },
        "media": {"type": "media"},
        "prog": {"type": "integer"},
        "role": {"type": "list", "allowed": ["agent", "client", "vendor"]},
        "rows": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "sku": {"type": "string", "maxlength": 24},
                    "price": {"type": "integer"},
                },
            },
        },
        "alist": {"type": "list", "items": [{"type": "string"}, {"type": "integer"}]},
        "location": {
            "type": "dict",
            "schema": {
                "address": {"type": "string"},
                "city": {"type": "string", "required": True},
            },
        },
        "born": {"type": "datetime"},
        "tid": {"type": "objectid", "nullable": True},
        "title": {"type": "string", "default": "Mr."},
        "id_list": {"type": "list", "schema": {"type": "objectid"}},
        "id_list_of_dict": {
            "type": "list",
            "schema": {"type": "dict", "schema": {"id": {"type": "objectid"}}},
        },
        "id_list_fixed_len": {"type": "list", "items": [{"type": "objectid"}]},
        "dict_list_fixed_len": {
            "type": "list",
            "items": [
                {"type": "dict", "schema": {"key1": {"type": "string"}}},
                {"type": "dict", "schema": {"key2": {"type": "integer"}}},
            ],
        },
        "dependency_field1": {"type": "string", "default": "default"},
        "dependency_field2": {"type": "string", "dependencies": ["dependency_field1"]},
        "dependency_field3": {
            "type": "string",
            "dependencies": {"dependency_field1": "value"},
        },
        "dependency_field4": {"type": "string"},
        "dependency_field5": {"type": "string", "dependencies": ["dependency_field4"]},
        "dependency_field6": {
            "type": "string",
            "dependencies": {"dependency_field4": "value"},
        },
        "read_only_field": {"type": "string", "default": "default", "readonly": True},
        "dict_with_read_only": {
            "type": "dict",
            "schema": {
                "read_only_in_dict": {
                    "type": "string",
                    "default": "default",
                    "readonly": True,
                }
            },
        },
        "dict_with_nested_default": {
            "type": "dict",
            "schema": {
                "nested_field": {"type": "string"},
                "nested_field_with_default": {"type": "string", "default": "nested"},
            },
        },
        "key1": {"type": "string"},
        "keyschema_dict": {
            "type": "dict",
            "keyschema": {"type": "string", "regex": "[a-z]+"},
        },
        "valueschema_dict": {"type": "dict", "valueschema": {"type": "integer"}},
        "aninteger": {"type": "integer"},
        "afloat": {"type": "float"},
        "anumber": {"type": "number"},
        "dict_valueschema": {
            "type": "dict",
            "valueschema": {
                "type": "dict",
                "schema": {"challenge": {"type": "objectid"}},
            },
        },
        "unsetted_default_value_field": {"type": "string", "default": "value"},
    },
}

users = copy.deepcopy(contacts)
users["url"] = "users"
users["datasource"] = {
    "source": "contacts",
    "filter": {"username": {"$exists": True}},
    "projection": {"username": 1, "ref": 1},
}
users["schema"]["username"] = {"type": "string", "required": True}
users["resource_methods"] = ["DELETE", "POST", "GET"]
users["item_title"] = "user"
users["additional_lookup"]["field"] = "username"

contacts_hide_born = copy.deepcopy(contacts)
contacts_hide_born["url"] = "contacts/hide_born"
contacts_hide_born["datasource"]["source"] = "contacts"
contacts_hide_born["datasource"]["projection"] = {"born": 0}

contacts_hide_media = copy.deepcopy(contacts)
contacts_hide_media["url"] = "contacts/hide_media"
contacts_hide_media["datasource"]["source"] = "contacts"
contacts_hide_media["datasource"]["projection"] = {"media": 0, "born": 0}

invoices = {
    "schema": {
        "inv_number": {"type": "string"},
        "person": {"type": "objectid", "data_relation": {"resource": "contacts"}},
        "invoicing_contacts": {
            "type": "list",
            "data_relation": {"resource": "contacts"},
        },
        "persondbref": {"type": "dbref", "data_relation": {"resource": "contacts"}},
        "decimal_number": {"type": "decimal"},
    }
}

# This resource is used to test app initialization when using resource
# level versioning
versioned_invoices = copy.deepcopy(invoices)
versioned_invoices["versioning"] = True

# This resource is used to test subresources that have a reference/objectid
# field that is set to be required.
required_invoices = copy.deepcopy(invoices)
required_invoices["schema"]["person"]["required"] = True

companies = {
    "item_title": "company",
    "schema": {
        "departments": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "title": {"type": "string"},
                    "members": {
                        "type": "list",
                        "schema": {
                            "type": "objectid",
                            "data_relation": {"resource": "contacts"},
                        },
                    },
                },
            },
        },
        "holding": {"type": "objectid", "data_relation": {"resource": "companies"}},
    },
}

users_overseas = copy.deepcopy(users)
users_overseas["url"] = "users/overseas"
users_overseas["datasource"] = {"source": "contacts"}

payments = {"resource_methods": ["GET"], "item_methods": ["GET"]}

empty = copy.deepcopy(invoices)

user_restricted_access = copy.deepcopy(contacts)
user_restricted_access["url"] = "restricted"
user_restricted_access["datasource"] = {"source": "contacts"}

users_invoices = copy.deepcopy(invoices)
users_invoices["url"] = 'users/<regex("[a-f0-9]{24}"):person>/invoices'
users_invoices["datasource"] = {"source": "invoices"}

users_required_invoices = copy.deepcopy(required_invoices)
users_required_invoices[
    "url"
] = 'users/<regex("[a-f0-9]{24}"):person>/required_invoices'
users_required_invoices["datasource"] = {"source": "required_invoices"}

users_searches = copy.deepcopy(invoices)
users_searches["datasource"] = {"source": "invoices"}
users_searches["url"] = 'users/<regex("[a-zA-Z0-9:\\-\\.]+"):person>/saved_searches'

internal_transactions = {
    "resource_methods": ["GET"],
    "item_methods": ["GET"],
    "internal_resource": True,
}

ids = {
    "query_objectid_as_string": True,
    "item_lookup_field": "id",
    "resource_methods": ["POST", "GET"],
    "schema": {"id": {"type": "string"}, "name": {"type": "string"}},
}

login = {
    "item_title": "login",
    "url": "login",
    "datasource": {"projection": {"password": 0}},
    "schema": {
        "email": {"type": "string", "required": True, "unique": True},
        "password": {"type": "string", "required": True},
    },
}

# This resource is used to test resource-specific id fields.
products = {
    "id_field": "sku",
    "item_lookup_field": "sku",
    "item_url": 'regex("[A-Z]+")',
    "schema": {
        "sku": {"type": "string", "maxlength": 16},
        "title": {"type": "string", "minlength": 4, "maxlength": 32},
        "parent_product": {"type": "string", "data_relation": {"resource": "products"}},
    },
}

test_patch = {
    "datasource": {"source": "test_patch"},
    "normalize_on_patch": False,
    "schema": {
        "name": {"type": "string", "required": True},
        "contact": {
            "type": "dict",
            "required": True,
            "schema": {
                "phone": {
                    "type": "string",
                    "required": False,
                    "default": "default_phone",
                },
                "email": {
                    "type": "string",
                    "required": False,
                    "default": "default_email",
                },
            },
        },
    },
}

tenant_a = {
    "datasource": {"source": "tenants", "filter": {"_tenant": "tenant_a"}},
    "schema": {
        "_tenant": {"type": "string", "readonly": True, "default": "tenant_a"},
        "name": {"type": "string", "required": True, "unique_within_resource": True},
    },
}

tenant_b = {
    "datasource": {"source": "tenants", "filter": {"_tenant": "tenant_b"}},
    "schema": {
        "_tenant": {"type": "string", "readonly": True, "default": "tenant_b"},
        "name": {"type": "string", "required": True, "unique_within_resource": True},
    },
}

test_unique = {
    "datasource": {"source": "test_unique"},
    "schema": {
        "unique_attribute": {"type": "string", "unique": True},
        "unique_in_dict_attribute": {
            "type": "dict",
            "schema": {"unique_attribute": {"type": "string", "unique": True}},
        },
        "unique_in_list_attribute": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {"unique_attribute": {"type": "string", "unique": True}},
            },
        },
        "unique_in_deep_dict_attribute": {
            "type": "dict",
            "schema": {
                "dict_attribute": {
                    "type": "dict",
                    "schema": {"unique_attribute": {"type": "string", "unique": True}},
                }
            },
        },
        "unique_in_deep_list_attribute": {
            "type": "dict",
            "schema": {
                "list_attribute": {
                    "type": "list",
                    "schema": {
                        "type": "dict",
                        "schema": {
                            "unique_attribute": {"type": "string", "unique": True}
                        },
                    },
                }
            },
        },
        "unique_within_resource_attribute": {
            "type": "string",
            "unique_within_resource": True,
        },
    },
}

test_unique_nested = {"datasource": {"source": "test_unique_nested"}, "schema": {}}

credit_rules = {
    "allow_unknown": True,
    "schema": {
        "name": {"type": "string"},
        "amount": {"type": "float", "default": 0.00, "min": 0.00, "required": True},
        "start": {"type": "string", "required": True},
        "duration": {
            "type": "string",
            "allowed": ["days", "weeks", "months", "years", "one-time"],
            "required": True,
        },
        "prepaid": {"type": "boolean", "default": False},
        "expiration_duration": {
            "type": "string",
            "allowed": ["days", "weeks", "months", "years"],
            "required": False,
        },
    },
}

brands = {
    "item_title": "brand",
    "schema": {"name": {"type": "string"}, "address": "string"},
}

components = {
    "item_title": "component",
    "schema": {
        "name": {"type": "string"},
        "price": "integer",
        "brand": {"type": "objectid", "data_relation": {"resource": "brands"}},
    },
}

computers = {
    "item_title": "computers",
    "schema": {
        "name": {"type": "string"},
        "components": {
            "type": "dict",
            "schema": {
                "cpu": {
                    "type": "objectid",
                    "data_relation": {"resource": "components"},
                },
                "motherboard": {
                    "type": "objectid",
                    "data_relation": {"resource": "components"},
                },
            },
        },
    },
}

child_products = copy.deepcopy(products)
child_products["url"] = 'products/<regex("[A-Z]+"):parent_product>/children'
child_products["datasource"] = {"source": "products"}

exclusion = copy.deepcopy(contacts)
exclusion["url"] = "exclusion"
exclusion["soft_delete"] = True
exclusion["datasource"]["source"] = "contacts"
exclusion["datasource"]["projection"] = {"int": 0}

DOMAIN = {
    "disabled_bulk": disabled_bulk,
    "contacts": contacts,
    "users": users,
    "users_overseas": users_overseas,
    "contacts_hide_born": contacts_hide_born,
    "contacts_hide_media": contacts_hide_media,
    "invoices": invoices,
    "versioned_invoices": versioned_invoices,
    "required_invoices": required_invoices,
    "payments": payments,
    "empty": empty,
    "restricted": user_restricted_access,
    "peopleinvoices": users_invoices,
    "peoplerequiredinvoices": users_required_invoices,
    "peoplesearches": users_searches,
    "companies": companies,
    "internal_transactions": internal_transactions,
    "ids": ids,
    "login": login,
    "products": products,
    "child_products": child_products,
    "exclusion": exclusion,
    "test_patch": test_patch,
    "tenant_a": tenant_a,
    "tenant_b": tenant_b,
    "test_unique": test_unique,
    "credit_rules": credit_rules,
    "brands": brands,
    "components": components,
    "computers": computers,
}
