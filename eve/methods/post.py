from eve import LAST_UPDATED, ID_FIELD, DATE_CREATED, STATUS_OK, STATUS_ERR
from eve.validation import ValidationError
from eve.utils import document_link
from common import parse
from datetime import datetime
from flask import request, abort
from flask import current_app as app


def post(resource):

    if len(request.form) == 0:
        abort(400)

    response = dict()
    date_utc = datetime.utcnow()

    schema = app.config['DOMAIN'][resource]['schema']
    validator = app.validator(schema, resource)

    for key, value in request.form.items():

        response_item = dict()
        issues = list()

        try:
            document = parse(value, resource)
            validation = validator.validate(document)
            if validation:
                document[LAST_UPDATED] = document[DATE_CREATED] = date_utc
                # TODO err.. we want to switch the two lines below!
                document[ID_FIELD] = key
                #document[ID_FIELD] = app.data.insert(resource, document)

                response_item[ID_FIELD] = document[ID_FIELD]
                response_item[LAST_UPDATED] = document[LAST_UPDATED]
                response_item['link'] = document_link(resource,
                                                      response_item[ID_FIELD])
            else:
                issues.append(validator.errors)
        except ValidationError as e:
            raise e
        except Exception as e:
            issues.append(str(e))

        if len(issues):
            response_item['issues'] = issues
            response_item['status'] = STATUS_ERR
        else:
            response_item['status'] = STATUS_OK

        response[key] = response_item

    return response, None, None, 200
