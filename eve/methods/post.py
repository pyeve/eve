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
from flask import request, abort
from flask import current_app as app
from common import parse
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

    .. versionchanged:: 0.0.4
       Added the ``reqiores_auth`` decorator.

    .. versionchanged:: 0.0.3
       JSON links. Superflous ``response`` container removed.
    """

    if len(request.form) == 0:
        abort(400)

    response = {}
    date_utc = datetime.utcnow()

    schema = app.config['DOMAIN'][resource]['schema']
    validator = app.validator(schema, resource)

    for key, value in request.form.items():

        response_item = {}
        issues = []

        try:
            document = parse(value, resource)
            validation = validator.validate(document)
            if validation:
                document[config.LAST_UPDATED] = \
                    document[config.DATE_CREATED] = date_utc

                resource_user_restricted = app.config['DOMAIN'][resource].get('user_restricted')
                if (app.config['AUTH_USERNAME_FIELD'] or resource_user_restricted)\
                        and resource_user_restricted is not False:
                    document.update(app.auth.username_field())

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
