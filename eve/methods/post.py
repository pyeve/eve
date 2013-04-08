# -*- coding: utf-8 -*-

"""
    eve.methods.post
    ~~~~~~~~~~~~~~~~

    This module imlements the POST method, supported by the resources
    endopints.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime
from flask import request
from flask import current_app as app
from common import parse, payload
from eve.utils import document_link, config
from eve.auth import requires_auth
from eve.validation import ValidationError


@requires_auth('resource')
def post(resource):
    """ Adds one or more documents to a resource. Each document is validated
    against the domain schema. If validation passes the document is inserted
    and ID_FIELD, LAST_UPDATED and DATE_CREATED along with a link to the
    document are returned. If validation fails, a list of validation issues
    is returned.

    :param resource: name of the resource involved.

    .. versionchanged:: 0.0.5
       Support for 'application/json' Content-Type .
       Support for 'user-restricted resource access'.

    .. versionchanged:: 0.0.4
       Added the ``reqiores_auth`` decorator.

    .. versionchanged:: 0.0.3
       JSON links. Superflous ``response`` container removed.
    """

    response = {}
    date_utc = datetime.utcnow()

    schema = app.config['DOMAIN'][resource]['schema']
    validator = app.validator(schema, resource)

    for key, value in payload().items():

        response_item = {}
        issues = []

        try:
            document = parse(value, resource)
            validation = validator.validate(document)
            if validation:
                document[config.LAST_UPDATED] = \
                    document[config.DATE_CREATED] = date_utc

                # if 'user-restricted resource access' is enabled and there's
                # an Auth request active, inject the username into the document
                username_field = \
                    app.config['DOMAIN'][resource]['auth_username_field']
                if username_field and request.authorization:
                    document[username_field] = request.authorization.username

                document[config.ID_FIELD] = app.data.insert(resource, document)

                response_item[config.ID_FIELD] = document[config.ID_FIELD]
                response_item[config.LAST_UPDATED] = \
                    document[config.LAST_UPDATED]
                response_item['_links'] = \
                    {'self': document_link(resource,
                                           response_item[config.ID_FIELD])}

            else:
                issues.extend(validator.errors)
        except ValidationError as e:
            raise e
        except Exception as e:
            issues.append(str(e))

        if len(issues):
            response_item['issues'] = issues
            response_item['status'] = config.STATUS_ERR
        else:
            response_item['status'] = config.STATUS_OK

        response[key] = response_item

    return response, None, None, 200
