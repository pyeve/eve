# -*- coding: utf-8 -*-
import os

db_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           'test.db')
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s' % db_filename

# SQLALCHEMY_ECHO = True
# SQLALCHEMY_RECORD_QUERIES = True

SERVER_NAME = 'localhost:5000'

ID_FIELD = '_id'
ITEM_LOOKUP = True
ITEM_LOOKUP_FIELD = ID_FIELD

RESOURCE_METHODS = ['GET', 'POST', 'DELETE']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE', 'PUT']

people = {'item_title': 'person',
          'additional_lookup': {
              'url': 'regex("[\w]+")',
              'field': 'firstname'
          },
          'cache_control': 'max-age=10,must-revalidate',
          'cache_expires': 10,
          'resource_methods': ['GET', 'POST', 'DELETE']
          }

import copy
users = copy.deepcopy(people)
users['url'] = 'users'
users['datasource'] = {'source': 'People',
                       'filter': 'prog < 5'}
users['resource_methods'] = ['DELETE', 'POST', 'GET']
users['item_title'] = 'user'

users_overseas = copy.deepcopy(users)
users_overseas['url'] = 'users/overseas'
users_overseas['datasource'] = {'source': 'People'}

invoices = {}

user_invoices = copy.deepcopy(invoices)
user_invoices['url'] = 'users/<regex("[0-9]+"):people>/invoices'
user_invoices['datasource'] = {'source': 'Invoices'}

payments = {
    'resource_methods': ['GET'],
    'item_methods': ['GET'],
}

DOMAIN = {
    'people': people,
    'users': users,
    'users_overseas': users_overseas,
    'invoices': invoices,
    'userinvoices': user_invoices,
    'payments': payments
}
